import babel
import logging
import pyramid.security
import pyramid.util
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, HSTORE, ARRAY, JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from pyramid.security import ALL_PERMISSIONS
import pyramid.i18n
import zope.interface

from pym.models import (
    DbBase, DefaultMixin, DbSession
)
from pym.models.types import CleanUnicode
import pym.lib
import pym.exc
from pym.i18n import _
from pym.cache import region_auth_long_term

from .events import UserAuthError
from .const import (NOBODY_UID, NOBODY_PRINCIPAL, NOBODY_EMAIL,
    NOBODY_DISPLAY_NAME, WHEEL_RID)


mlgg = logging.getLogger(__name__)
_dnr = pyramid.util.DottedNameResolver(None)


class IAuthMgrNode(zope.interface.Interface):
    pass


class IUserMgrNode(zope.interface.Interface):
    pass


class IGroupMgrNode(zope.interface.Interface):
    pass


class IGroupMemberMgrNode(zope.interface.Interface):
    pass


class IPermissionMgrNode(zope.interface.Interface):
    pass


class GroupMember(DbBase, DefaultMixin):
    """
    Group member.

    A group member is either a user or another group.
    """
    __tablename__ = "group_member"
    __table_args__ = (
        sa.UniqueConstraint('group_id', 'member_user_id',
            name='group_member_user_ux'),
        sa.UniqueConstraint('group_id', 'member_group_id',
            name='group_member_group_ux'),
        {'schema': 'pym'}
    )

    IDENTITY_COL = None

    group_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False)
    """This group is the container."""
    member_user_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.user.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """This user is the member."""
    member_group_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """This group is the member."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    group = relationship('Group', foreign_keys=[group_id])
    member_user = relationship('User', foreign_keys=[member_user_id])
    member_group = relationship('Group', foreign_keys=[member_group_id])


class GplusProfile:

    def __init__(self, user):
        self._user = user
        if 'gplus' not in user._profile:
            user._profile['gplus'] = {}

    @property
    def id(self):
        return self._user.gplus_id

    @id.setter
    def id(self, v):
        self._user.gplus_id = v

    @property
    def picture_url(self):
        return self._user._profile['gplus'].get('picture_url')

    @picture_url.setter
    def picture_url(self, v):
        self._user._profile['gplus']['picture_url'] = v

    @property
    def profile_url(self):
        return self._user._profile['gplus'].get('profile_url')

    @profile_url.setter
    def profile_url(self, v):
        self._user._profile['gplus']['profile_url'] = v


class GenderEnum(pym.lib.Enum):
    male = 'm'
    female = 'f'
    trans = 't'
    unknown = None


class UserProfile:

    def __init__(self, user, gplus_class=GplusProfile):
        if user._profile is None:
            user._profile = {}
        self._user = user
        self._gplus = gplus_class(user)

    def get_all(self):
        return self._user._profile

    @property
    def gplus(self):
        return self._gplus

    @property
    def locale_name(self):
        return self._user._profile.get('locale_name')

    @locale_name.setter
    def locale_name(self, v):
        self._user._profile['locale_name'] = v

    @property
    def gender(self):
        v = self._user._profile.get('gender')
        if v is None:
            return None
        for name, elem in GenderEnum.__members__.items():
            if v == elem.value:
                return elem
        raise ValueError("Invalid gender: '{}'".format(v))

    @gender.setter
    def gender(self, v):
        if isinstance(v, str):
            for name, elem in GenderEnum.__members__.items():
                if v == elem.value or v == name:
                    self._user._profile['gender'] = v
                    return
            raise ValueError("Invalid gender: '{}'".format(v))
        else:
            self._user._profile['gender'] = v.value


class UserRc:

    def __init__(self, user):
        self.user = user


class User(DbBase, DefaultMixin):
    """
    A user account.

    Attribute ``principal`` is the login name which must be unique. We store the
    string as-is, but treat it as lowercase: 'FOO' == 'foo' --> True.

    We treat ``email`` and ``display_name`` the same.

    Each user has a ``display_name`` by which she is identified in the UI.
    Therefore this also must be unique. Be creative, if the default,
    ``first_name`` and ``last_name`` is not sufficient.

    Users are global to the system, i.e. a person has only one user account,
    regardless how many tenants he belongs to.
    """
    __tablename__ = "user"
    # The unique indexes are created below.
    __table_args__ = (
        {'schema': 'pym'}
    )

    IDENTITY_COL = 'principal'

    is_enabled = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Enabled?")}})
    """Tells whether or not a (human) admin has en/disabled this account."""
    disable_reason = sa.Column(CleanUnicode(255),
        info={'colanderalchemy': {'title': _("Disable Reason")}})
    """Reason why admin disabled this account."""
    is_blocked = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Blocked?")}})
    """Tells whether or not some automated process has en/disabled this
    account."""
    blocked_since = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Blocked Since")}})
    """Timestamp when block was established."""
    blocked_until = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Blocked Until")}})
    """Timestamp when block will automatically be released. NULL=never."""
    block_reason = sa.Column(CleanUnicode(255),
        info={'colanderalchemy': {'title': _("Block Reason")}})
    """Reason why block was established."""

    principal = sa.Column(CleanUnicode(255), nullable=False,
        info={'colanderalchemy': {'title': _("Principal")}})
    """Principal or user name."""
    pwd = sa.Column(CleanUnicode(255),
        info={'colanderalchemy': {'title': _("Password")}})
    """Password. NULL means blocked for login, e.g. for system accounts."""
    pwd_expires = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Pwd expires")}})
    """Timestamp when current pwd expires. NULL==never."""
    identity_url = sa.Column(CleanUnicode(255), index=True, unique=True,
        info={'colanderalchemy': {'title': _("Identity URL")}})
    """Used for login by OpenID."""
    gplus_id = sa.Column(CleanUnicode(255), index=True, unique=True,
        info={'colanderalchemy': {'title': _("Google+ ID")}})
    """Used for login by Google+ (OpenID Connect)."""
    email = sa.Column(CleanUnicode(128), nullable=False,
        info={'colanderalchemy': {'title': _("Email")}})
    """Email address. Always lower cased."""
    first_name = sa.Column(CleanUnicode(64),
        info={'colanderalchemy': {'title': _("First Name")}})
    """User's first name."""
    last_name = sa.Column(CleanUnicode(64),
        info={'colanderalchemy': {'title': _("Last Name")}})
    """User's last name."""
    display_name = sa.Column(CleanUnicode(255), nullable=False,
        info={'colanderalchemy': {'title': _("Display Name")}})
    """User is displayed like this. Usually 'first_name last_name' or
    'principal'."""

    login_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Login Time")}})
    """Timestamp of current login."""
    login_ip = sa.Column(sa.String(255),
        info={'colanderalchemy': {'title': _("Login IP")}})
    """IP address of logged in client."""
    access_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Access Time")}})
    """Timestamp when site was last accessed. Used to expire session."""
    kick_session = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Kick?")}})
    """Tells whether user's session is automatically terminated on next
    access."""
    kick_reason = sa.Column(CleanUnicode(255),
        info={'colanderalchemy': {'title': _("Kick Reason")}})
    """Display this message to kicked user."""
    logout_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Logout Time")}})
    """Timestamp of logout."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True,
        info={'colanderalchemy': {'title': _("Description")}})
    )
    """Optional description."""
    _profile = sa.orm.deferred(
        sa.Column(
            'profile',
            MutableDict.as_mutable(JSON()),
            nullable=True,
            default=dict(),
            info={'colanderalchemy': {'title': _("Profile")}}
        )
    )
    """Profile data as JSON (aka detailed 'about me')"""
    _rc = sa.orm.deferred(
        sa.Column(
            'rc',
            MutableDict.as_mutable(JSON()),
            nullable=True,
            info={'colanderalchemy': {'title': _("Rc")}}
        )
    )
    """User's preferences"""
    sessionrc = sa.Column(
        MutableDict.as_mutable(JSON()),
        nullable=True,
        info={'colanderalchemy': {'title': _("SessionRc")}}
    )
    """User's session"""

    group_memberships = relationship('GroupMember',
        # cascade deletions
        cascade="all, delete-orphan",
        # Let the DB cascade deletions to children
        passive_deletes=True,
        foreign_keys='GroupMember.member_user_id')
    """List of our direct group memberships."""
    groups = association_proxy('group_memberships', 'group')
        #info={'colanderalchemy': {'title': _("Groups")}})
    """List of groups we are directly member of. Call :meth:`load_all_groups` to
    get all."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orm_init()

    @sa.orm.reconstructor
    def init_on_load(self):
        self._orm_init()

    def _orm_init(self):
        self.profile = UserProfile(self)
        self.rc = UserRc(self)

    def load_all_groups(self):
        def creator():
            # Load nested groups
            # Init with groups we are member of directly
            all_gg = {x.id: x for x in self.groups}
            # make copy, all_gg will be changed in loop
            gg = list(all_gg.values())

            def _fetch_next_level(g):
                for mg in g.member_groups:
                    if mg:
                        if mg.id not in all_gg:
                            all_gg[mg.id] = mg
                            _fetch_next_level(mg)

            # This is depth-first search
            for g in gg:
                _fetch_next_level(g)
            resp = [(x.id, x.name) for x in all_gg.values()]
            mlgg.debug('Groups for {}: {}'.format(self.principal, resp))
            return resp

        return region_auth_long_term.get_or_create(self.group_cache_key, creator)

    def clear_group_cache(self):
        region_auth_long_term.delete(self.group_cache_key)

    @property
    def group_cache_key(self):
        return 'auth:user:{}:groups'.format(self.principal)

    def __repr__(self):
        return "<{name}(id={id}, principal='{p}', email='{e}'>".format(
            id=self.id, p=self.principal, e=self.email, name=self.__class__.__name__)


sa.Index("user_principal_ux", sa.func.lower(User.__table__.c.principal),
    unique=True)
sa.Index("user_email_ux", sa.func.lower(User.__table__.c.email),
    unique=True)
sa.Index("user_display_name_ux", sa.func.lower(User.__table__.c.display_name),
    unique=True)


class Group(DbBase, DefaultMixin):
    """
    A group.

    A group groups users or other groups. Groups may be global to the system,
    or belong to a specific tenant. In the former case, group's ``name`` must
    be globally unique, in the latter case only within that tenant.

    A group may only belong to one tenant.
    """
    __tablename__ = "group"
    __table_args__ = (
        sa.UniqueConstraint('tenant_id', 'name', name='group_ux'),
        {'schema': 'pym'}
    )

    tenant_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.tenant.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True
    )
    """Optional reference to the tenant to which this group belongs."""
    name = sa.Column(CleanUnicode(255), nullable=False)
    """Name of the group. Must be unique within a tenant."""
    kind = sa.Column(CleanUnicode(255), nullable=True)
    """An optional classifier to bundle groups together."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    group_memberships = relationship('GroupMember',
        # cascade deletions
        cascade="all, delete-orphan",
        # Let the DB cascade deletions to children
        passive_deletes=True,
        foreign_keys='GroupMember.group_id')
    """List of memberships in which we are the container."""
    member_groups = association_proxy('group_memberships', 'member_group')
    """List of groups that are our members."""
    member_users = association_proxy('group_memberships', 'member_user')
    """List of users that are our members."""

    def __repr__(self):
        return "<{name}(id={id}, tenant_id={t}, name='{n}'>".format(
            id=self.id, t=self.tenant_id, n=self.name,
            name=self.__class__.__name__)


class Permissions(pym.lib.Enum):
    all = '*'
    visit = 'visit'
    read = 'read'
    write = 'write'
    delete = 'delete'
    admin = 'admin'
    admin_auth = 'admin_auth'
    admin_res = 'admin_res'


class Permission(DbBase, DefaultMixin):
    """
    Permission.

    A permission has a ``name``, a string that is used in code e.g. as::

        @view_defaults(permission='manage_auth')

    Permissions may be hierarchical.

    If you grant a permission, automatically all of its parents are also
    granted. E.g. if ``read`` is a parent of ``write`` and you grant ``write``,
    ``read`` is also granted.

    If you deny a permission, automatically all of its children are also denied.
    E.g. if with above settings you deny ``read``, ``write`` is also denied.
    """
    __tablename__ = "permission_tree"
    __table_args__ = (
        sa.UniqueConstraint('name', name='permission_tree_ux'),
        {'schema': 'pym'}
    )
    # Topmost permission has parent_id NULL
    parent_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            'pym.permission_tree.id',
            onupdate='CASCADE',
            ondelete='CASCADE',
            name='permission_parent_fk'
        ),
        nullable=True
    )
    name = sa.Column(CleanUnicode(64), nullable=False)
    """The name of the permission as used in code."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    children = relationship("Permission",
        order_by=[name],
        # cascade deletions
        cascade="all, delete-orphan",
        # Let the DB cascade deletions to children
        passive_deletes=True,
        lazy='select',
        ##lazy='joined',
        ##join_depth=1,

        # many to one + adjacency list - remote_side
        # is required to reference the 'remote'
        # column in the join condition.
        backref=sa.orm.backref("parent", remote_side="Permission.id"),

        # children will be represented as a dictionary
        # on the "name" attribute.
        collection_class=attribute_mapped_collection('name'),
    )
    """Children of this permission."""

    def add_child(self, perm):
        """
        Adds a permission to my children.

        :param perm: Instance of a permission
        """
        perm.parent = self

    @region_auth_long_term.cache_on_arguments(namespace='permission')
    def load_all(sess):
        """
        Returns detailed info about permissions.

        Returned is a dict which keys are the permission names as well as their
        IDs. Each element is another dict with keys ``id``, ``name``,
        ``parents``, and ``children``.

        ``parents`` and ``children`` are lists of 2-tuples with [0] := ID and
        [1] := name.

        The list of parents comprises only parents in the direct path to the
        topmost permission, where-as the list of children comprises the whole
        tree of child permissions. Given this tree::

            visit
             |
             +-- read
             |    +-- write
             +-- delete
             |
             +-- admin
                  +-- admin_auth
                  +-- admin_res

        Element 'admin_auth' has as parents ['admin', 'visit'] and None children.

        Element 'visit' has None parents and all other permissions as children
        ['read', 'delete', 'admin', 'write', 'admin_auth', 'admin_res'].

        E.g.::
            {
                8: {
                    'children': None,
                    'id': 8,
                    'name': 'admin_res',
                    'parents': [(2, 'visit'), (4, 'admin')]
                },
                'read': {
                    'children': [(6, 'write')],
                    'id': 3,
                    'name': 'read',
                    'parents': [(2, 'visit')]
                },
            }
        """
        tree = {}
        # This query returns all permissions with their parents.
        # Some permissions may have no parents.
        q = sa.text("SELECT id, name, parents "
            "FROM pym.vw_permission_tree") \
            .columns(
                id=sa.Integer(), name=sa.Unicode(),
                parents=ARRAY(sa.Unicode, dimensions=2)
            )
        rs = sess.execute(q)
        for r in rs:
            pp = None
            if r.parents:
                pp = []
                for p in r.parents:
                    pp.append((int(p[0]), p[1]))
            tree[r.name] = {
                'id': r.id,
                'name': r.name,
                'parents': pp,
                'children': None
            }
        # This query returns all permissions with their children.
        # CAVEAT: Permissions without children are not listed!
        q = sa.text("SELECT id, name, children "
            "FROM pym.vw_permissions_with_children") \
            .columns(
                id=sa.Integer(), name=sa.Unicode(),
                children=ARRAY(sa.Unicode, dimensions=2)
            )
        rs = sess.execute(q)
        # A single permission may have multiple rows with lists of children.
        # Append them all.
        for r in rs:
            if tree[r.name]['children']:
                tree[r.name]['children'] += [(int(x[0]), x[1])
                    for x in r.children]
            else:
                tree[r.name]['children'] = [(int(x[0]), x[1])
                    for x in r.children]
        # Now remove duplicate children.
        for name, v in tree.items():
            if not v['children']:
                continue
            v['children'] = list(set(v['children']))
        # Also index by ID
        by_id = {}
        for name, v in tree.items():
            by_id[v['id']] = v
        tree.update(by_id)
        return tree

    def __repr__(self):
        return "<{name}(id={id}, name='{n}', parent_id='{p}'>".format(
            id=self.id, n=self.name, p=self.parent_id, name=self.__class__.__name__)


class Ace(DbBase, DefaultMixin):
    """
    Access Control Entry.

    We define access control by granting or denying a group or a user a
    named permission on a resource.
    """
    __tablename__ = "resource_acl"
    __table_args__ = (
        sa.UniqueConstraint('resource_id', 'group_id', 'user_id',
            'permission_id', name='resource_acl_ux'),
        {'schema': 'pym'}
    )

    resource_id = sa.Column(
        sa.Integer(),
        sa.ForeignKey(
            "pym.resource_tree.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_resource_fk'
        ),
        nullable=False
    )
    """Reference to a resource node."""
    group_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_group_fk'
        ),
        nullable=True
    )
    """Reference to a group. Mandatory if user is not set."""
    user_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.user.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_user_fk'
        ),
        nullable=True
    )
    """Reference to a user. Mandatory if group is not set."""
    sortix = sa.Column(sa.Integer(), nullable=True, server_default='5000')
    """Sort index; if equal, sort by ID.

    .. note::

        Pyramid's authorization policy lets the first match win, so it is
        important to setup ``sortix`` properly!
    """
    permission_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            "pym.permission_tree.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_permission_fk'
        ),
        nullable=False
    )
    """Reference to a permission."""
    allow = sa.Column(
        sa.Boolean(),
        nullable=False
    )
    """Allow if TRUE, deny if FALSE."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def to_pyramid_ace(self, perms):
        if self.user_id:
            princ = 'u:' + str(self.user_id)
        else:
            princ = 'g:' + str(self.group_id)
        p = perms[self.permission_id]
        if p['name'] == '*':
            perm = pyramid.security.ALL_PERMISSIONS
        else:
            perm = p['name']
        allow_deny = pyramid.security.Allow if self.allow \
            else pyramid.security.Deny
        return allow_deny, princ, perm

    def __repr__(self):
        return "<{name}(id={id}, resource_id={r}, group_id={g}," \
               " user_id={u}, sortix={ix}, permission_id={p}, allow={allow}>".format(
                   id=self.id, r=self.resource_id, p=self.permission_id,
                   g=self.group_id, u=self.user_id, allow=self.allow,
                   ix=self.sortix, name=self.__class__.__name__
               )


class ActivityLog(DbBase):
    __tablename__ = "activity_log"
    __table_args__ = (
        {'schema': 'pym'}
    )

    id = sa.Column(sa.Integer, primary_key=True)
    """Primary key of table."""
    ctime = sa.Column(sa.DateTime,
        server_default=sa.func.current_timestamp())
    """Timestamp, creation time."""
    principal = sa.Column(CleanUnicode(255))
    method = sa.Column(CleanUnicode(255))
    url = sa.Column(CleanUnicode(2048))
    client_addr = sa.Column(INET)
    remote_addr = sa.Column(INET)
    remote_user = sa.Column(CleanUnicode(255))
    header_authorization = sa.Column(CleanUnicode(255))
    headers = sa.Column(HSTORE)


def get_vw_user_browse():
    return sa.Table('vw_user_browse', User.metadata, autoload=True,
        schema='pym')


def get_vw_group_browse():
    return sa.Table('vw_group_browse', Group.metadata, autoload=True,
        schema='pym')


def get_vw_group_member_browse():
    return sa.Table('vw_group_member_browse', GroupMember.metadata, autoload=True,
        schema='pym')


class CurrentUser(object):

    SESSION_KEY = 'auth:current_user'

    def __init__(self, sess, request, user_class):
        """
        This class describes the current user.

        This class gets bolted onto ``request`` and is used to handle the
        current user. Even if no-one is logged in, we have a current user:
        "nobody".

        Use this class to process login/logout, and handle attributes of the
        current user in the current session.

        This class does not handle storage of user records itself, but relies
        on an injected ``auth_provider``.

        :param sess: Current DB session
        :param request: Current request
        :param user_class: Class that represents a stored user, needed for
            ``auth_provider``.
        """
        self._request = request
        self._metadata = {}
        self._groups = []
        self.uid = None
        self.principal = None
        self.sess = sess
        rc = request.registry['rc']
        cls = rc.g('auth.class.provider')
        self.auth_provider = cls(self.sess, user_class)
        self.init_nobody()

    def load_by_principal(self, principal):
        u = self.auth_provider.load_by_principal(principal)
        self.init_from_user(u)

    def init_nobody(self):
        u = self.auth_provider.load_by_principal(NOBODY_PRINCIPAL)
        self.init_from_user(u)

    def init_from_user(self, u):
        """
        Initialises authenticated user.
        """
        self.uid = u.id
        self.principal = u.principal
        self.groups = u.load_all_groups()
        self._metadata['email'] = u.email
        self._metadata['first_name'] = u.first_name
        self._metadata['last_name'] = u.last_name
        self._metadata['display_name'] = u.display_name
        self._metadata['preferred_locale'] = u.profile.locale_name

    def is_auth(self):
        """Tells whether user is authenticated, i.e. is not nobody
        """
        return self.uid != NOBODY_UID

    def is_wheel(self):
        if not self._groups:
            return False
        for g in self._groups:
            if g.id == WHEEL_RID:
                return True
        return False

    def login(self, login, pwd, remote_addr):
        """
        Login by principal/email and password.

        Returns True on success, else False.
        """
        # Login methods throw AuthError exception. Caller should handle them.
        try:
            if '@' in login:
                p = self.auth_provider.login_by_email(
                    request=self._request,
                    email=login, pwd=pwd, remote_addr=remote_addr
                )
            else:
                p = self.auth_provider.login_by_principal(
                    request=self._request,
                    principal=login, pwd=pwd, remote_addr=remote_addr
                )
        except pym.exc.AuthError as exc:
            self._request.registry.notify(
                UserAuthError(self._request, login, pwd,
                    remote_addr, exc)
            )
            raise
        self.init_from_user(p)
        self._request.session.new_csrf_token()
        return True

    def impersonate(self, principal):
        """
        Loads a different user into current session.

        Keep in mind that all session data apart from the user data will not
        change.

        :param principal: Principal or instance of new user
        :return: Instance of new user
        """
        if isinstance(principal, str):
            u = self.auth_provider.load_by_principal(principal)
        else:
            u = principal
        self._request.session[self.__class__.SESSION_KEY + '/prev_user'] = \
            self.principal
        self.init_from_user(u)
        self._request.session.new_csrf_token()
        return u

    def repersonate(self):
        """
        Loads previous user back into session.

        :return: Instance of new user (which is the previous one) or None if
            no previous user was set
        """
        try:
            principal = self._request.session[
                self.__class__.SESSION_KEY + '/prev_user']
            del self._request.session[self.__class__.SESSION_KEY + '/prev_user']
        except KeyError:
            return False
        u = self.auth_provider.load_by_principal(principal)
        self.init_from_user(u)
        self._request.session.new_csrf_token()
        return u

    def is_impersonated(self):
        return self.__class__.SESSION_KEY + '/prev_user' in self._request.session

    def logout(self):
        """
        Logout, resets metadata back to nobody.
        """
        self.auth_provider.logout(self._request, self.uid)
        # Remove all session data
        self._request.session.invalidate()
        self.init_nobody()
        self._request.session.new_csrf_token()

    def __getattr__(self, name):
        try:
            return self._metadata[name]
        except KeyError:
            raise AttributeError("Attribute '{0}' not found".format(name))

    @property
    def groups(self):
        return self._groups

    @groups.setter
    def groups(self, v):
        # mlgg.debug("Setting groups: {}".format([str(x) for x in groups]))
        # for x in traceback.extract_stack(limit=7):
        #     mlgg.debug("{}".format(x))
        self._groups = v

    @property
    def preferred_locale(self):
        loc = self._metadata.get('preferred_locale', None)
        if loc:
            return babel.Locale(loc)
        else:
            return None

    def __repr__(self):
        return "<{name}(id={id}, principal='{pr}', email='{email}')>".format(
            id=self.uid, pr=self.principal, email=self.email,
            name=self.__class__.__name__
        )


def get_current_user(request):
    """
    This method is used as a request method to reify a user object
    to the request object as property ``user``.
    """
    #mlgg.debug("get user: {}".format(request.path))
    userid = request.unauthenticated_userid
    sess = DbSession()
    rc = request.registry['rc']
    user_class = rc.g('auth.class.user')
    cusr = CurrentUser(sess, request, user_class)
    if userid is not None:
        cusr.load_by_principal(userid)
    return cusr
