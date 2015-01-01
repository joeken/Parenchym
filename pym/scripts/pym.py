#!/usr/bin/env python
from collections import OrderedDict
import getpass
import textwrap

import transaction
import time
import argparse
import logging
import sys
import os
import datetime
import redis
import sqlalchemy as sa
import sqlalchemy.sql.expression
import sqlalchemy.orm.exc
import alembic.command
import alembic.config
from zope.sqlalchemy import mark_changed
from pym.auth.const import SYSTEM_UID
import pym.cli
import pym.exc
import pym.auth.models as pam
import pym.auth.manager as authmgr
import pym.res.models as prm
import pym.tenants.models as ptm
from pprint import pprint
from pym.models import todata, todict


def _list_to_tree(data, id_field='id', parent_field='parent_id', name_field='name'):
    out = OrderedDict([
        ('root', {id_field: 0, parent_field: 0, name_field: "Root node", 'children': []})
    ])
    for p in data:
        pid = p[parent_field] or 'root'
        out.setdefault(pid, {'children': []})
        out.setdefault(p[id_field], {'children': []})
        out[p[id_field]].update(p)
        out[pid]['children'].append(out[p[id_field]])
    return out['root']['children']


class Runner(pym.cli.Cli):

    ENTITIES = {
        'user': pam.User,
        'group': pam.Group,
        'group-member': pam.GroupMember,
        'permission': pam.Permission,
        'resource': prm.ResourceNode,
        'tenant': ptm.Tenant
    }

    def __init__(self):
        super().__init__()
        self.cache = None
        self._actor = None

    def init_app(self, args, lgg=None, rc=None, rc_key=None, setup_logging=True):
        super().init_app(args=args, lgg=lgg, rc=rc, rc_key=rc_key,
            setup_logging=setup_logging)
        self.cache = redis.StrictRedis.from_url(
            **self.rc.get_these('cache.redis'))
        self._actor = self.args.actor or getpass.getuser()
        self.lgg.debug('Actor: {}'.format(self._actor))

        try:
            self.args.id = int(self.args.id)
        except AttributeError:
            pass
        try:
            self._actor = int(self._actor)
        except ValueError:
            pass

    def run(self):
        self.lgg.error("You need to specify a command")

    def cmd_ls(self):
        if self.args.entity == 'user':
            self._cmd_ls_users()
        elif self.args.entity == 'group':
            self._cmd_ls_groups()
        elif self.args.entity == 'group-member':
            self._cmd_ls_group_members()
        elif self.args.entity == 'tenant':
            self._cmd_ls_tenants()
        elif self.args.entity == 'permission':
            self._cmd_ls_permissions()
        elif self.args.entity == 'resource':
            self._cmd_ls_resources()

    def _cmd_ls_users(self):
        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(e)
        qry = self._build_query(qry, e)
        data = todata(qry, excludes=['rc', 'profile'])
        self._print(data)

    def _cmd_ls_groups(self):
        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(
            e,
            ptm.Tenant
        ).outerjoin(
            ptm.Tenant, pam.Group.tenant_id == ptm.Tenant.id
        )
        qry = self._build_query(qry, e)
        data = []
        for r in qry:
            e, ten = r
            de = todict(e)
            d = OrderedDict()
            for k, v in de.items():
                d[k] = v
                if k == 'tenant_id':
                    d['tenant'] = ten.name if ten else None
            data.append(d)
        self._print(data)

    def _cmd_ls_group_members(self):
        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(e)
        qry = self._build_query(qry, e)
        data = todata(qry)
        self._print(data)

    def _cmd_ls_tenants(self):

        def _my_group(it):
            gr = it.load_my_group()
            return "{} ({})".format(gr.name, gr.id)

        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(e)
        qry = self._build_query(qry, e)
        fmap = {
            'assoc_group': _my_group
        }
        data = todata(qry, fmap=fmap)
        self._print(data)

    def _cmd_ls_permissions(self):
        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(e)
        qry = self._build_query(qry, e)
        data = todata(qry)
        self._print(data)

    def _cmd_ls_resources(self):
        e = self.__class__.ENTITIES[self.args.entity]
        qry = self.sess.query(e)
        qry = self._build_query(qry, e)
        data = todata(qry)
        self._print(data)

    def cmd_create(self):
        ent = self.args.entity
        data = self._parse(self.args.data)
        if 'owner_id' in data:
            del data['owner_id']
        data['owner'] = self._actor
        with transaction.manager:
            if ent == 'user':
                self._cmd_create_user()
            elif ent == 'group':
                e = authmgr.create_group(sess=self.sess, **data)
            elif ent == 'group-member':
                self._cmd_create_group_members()
            elif ent == 'tenant':
                self._cmd_create_tenant()
            elif ent == 'permission':
                self._cmd_create_permission()
            elif ent == 'resource':
                self._cmd_create_resource()
            else:
                raise ValueError("Unknown entity: '{}'".format(ent))
            self.lgg.info("{} created with ID {}".format(ent, e.id))

    def _cmd_create_user(self):
        raise NotImplementedError('TODO')

    def _cmd_create_group(self):
        raise NotImplementedError('TODO')

    def _cmd_create_group_members(self):
        raise NotImplementedError('TODO')

    def _cmd_create_tenant(self):
        raise NotImplementedError('TODO')

    def _cmd_create_permission(self):
        raise NotImplementedError('TODO')

    def _cmd_create_resource(self):
        raise NotImplementedError('TODO')

    def cmd_update(self):
        ent = self.args.entity
        id_ = self.args.id
        data = self._parse(self.args.data)
        if 'editor_id' in data:
            del data['editor_id']
        data['editor'] = self._actor
        with transaction.manager:
            if ent == 'user':
                self._cmd_update_user()
            elif ent == 'group':
                self._cmd_update_group()
            elif ent == 'group-member':
                self._cmd_update_group_members()
            elif ent == 'tenant':
                self._cmd_update_tenant()
            elif ent == 'permission':
                self._cmd_update_permission()
            elif ent == 'resource':
                self._cmd_update_resource()
            elif ent == 'ace':
                self._cmd_update_ace()
            else:
                raise ValueError("Unknown entity: '{}'".format(ent))
            self.lgg.info('{} {} updated'.format(ent, id_))

    def _cmd_update_user(self):
        raise NotImplementedError('TODO')

    def _cmd_update_group(self):
        raise NotImplementedError('TODO')

    def _cmd_update_group_members(self):
        raise NotImplementedError('TODO')

    def _cmd_update_tenant(self):
        raise NotImplementedError('TODO')

    def _cmd_update_permission(self):
        raise NotImplementedError('TODO')

    def _cmd_update_resource(self):
        raise NotImplementedError('TODO')

    def _cmd_update_ace(self):
        raise NotImplementedError('TODO')

    def cmd_delete(self):
        ent = self.args.entity
        id_ = self.args.id
        answer = 'y' if self.args.yes else input(
            "Are you sure to delete {} {} (y/n)? ".format(ent, id_)).lower()
        if answer == 'y':
            with transaction.manager:
                if ent == 'user':
                    self._cmd_delete_user()
                elif ent == 'group':
                    authmgr.delete_group(
                        sess=self.sess,
                        group=id_,
                        deleter=self._actor,
                        delete_from_db=self.args.delete_from_db
                    )
                elif ent == 'group-member':
                    self._cmd_delete_group_members()
                elif ent == 'tenant':
                    self._cmd_delete_tenant()
                elif ent == 'permission':
                    self._cmd_delete_permission()
                elif ent == 'resource':
                    self._cmd_delete_resource()
                elif ent == 'ace':
                    authmgr.delete_ace(
                        sess=self.sess,
                        ace_id=id_,
                        deleter=self._actor,
                        delete_from_db=self.args.delete_from_db
                    )
                else:
                    raise ValueError("Unknown entity: '{}'".format(ent))
                self.lgg.info('{} {} deleted'.format(ent, id_))

    def _cmd_delete_user(self):
        raise NotImplementedError('TODO')

    def _cmd_delete_group_members(self):
        raise NotImplementedError('TODO')

    def _cmd_delete_tenant(self):
        raise NotImplementedError('TODO')

    def _cmd_delete_permission(self):
        raise NotImplementedError('TODO')

    def _cmd_delete_resource(self):
        raise NotImplementedError('TODO')

    def cmd_allow(self):
        resource_id = int(self.args.resource_id)
        w = {}
        which = self.args.who[:2]
        who = self.args.who[2:]
        try:
            who = int(who)
        except ValueError:
            pass
        if which == 'u:':
            w['user'] = who
        elif which == 'g:':
            w['group'] = who
        else:
            raise ValueError("Invalid prefix: '{}'".format(which))
        try:
            perm = int(self.args.permission)
        except ValueError:
            perm = self.args.permission
        with transaction.manager:
            n = self.sess.query(prm.ResourceNode).get(resource_id)
            if not n:
                raise sa.orm.exc.NoResultFound("Failed to find resource with ID {}".format(resource_id))
            ace = n.allow(self.sess, self._actor, perm, **w)
        self.lgg.info('ACE created with ID {}'.format(ace.id))

    def _build_query(self, qry, entity):
        if not self.args.with_deleted:
            qry = qry.filter(entity.dtime == None)
        qry = qry.order_by(
            entity.id
        )
        return qry

    def cmd_permission_tree(self):

        def prn(dd, lvl):
            for d in dd:
                print('  ' * lvl, "{} ({})".format(d['name'], d['id']))
                if d['children']:
                    prn(d['children'], lvl + 1)

        rs = self.sess.query(pam.Permission).filter(
            pam.Permission.dtime == None
        ).order_by(pam.Permission.name)
        pp = _list_to_tree(todata(rs))
        prn(pp, 0)

    def cmd_resource_tree(self):
        sess = self.sess
        out = []

        def fetch_acl(resource_id):
            rs = sess.query(
                pam.Ace,
                pam.User,
                pam.Group,
                pam.Permission
            ).outerjoin(
                pam.User, pam.Ace.user_id == pam.User.id
            ).outerjoin(
                pam.Group, pam.Ace.group_id == pam.Group.id
            ).outerjoin(
                pam.Permission, pam.Ace.permission_id == pam.Permission.id
            ).filter(
                pam.Ace.resource_id == resource_id,
                pam.Ace.dtime == None
            ).order_by(
                pam.User.principal,
                pam.Group.name,
                pam.Ace.allow
            )
            data = []
            for r in rs:
                ace, usr, grp, perm = r
                p = 'u:' + usr.principal if usr else 'g:' + grp.name
                ad = 'ALLOW' if ace.allow else 'DENY'
                data.append("{} {} {} ({})".format(p, ad, perm.name, ace.id))
            return data

        def prn(dd, lvl):
            ind = '  ' * lvl
            for d in dd:
                if self.args.verbose:
                    od = OrderedDict()
                    od['Resource'] = "{ind}{} ({})".format(d['name'], d['id'], ind=ind)
                    if self.args.with_acl:
                        acl = fetch_acl(d['id'])
                        od['ACL'] = "\n".join(acl) if acl else ''
                    od['Interface'] = d['iface']
                    od['Kind'] = d['kind']
                    od['Title'] = d['title']
                    od['Short Title'] = d['short_title']
                    od['Slug'] = d['slug']
                    out.append(od)
                else:
                    print("{ind}{} ({})".format(d['name'], d['id'], ind=ind))
                    if self.args.with_acl:
                        acl = fetch_acl(d['id'])
                        for ace in acl:
                            print("{ind}  ! {}".format(ace, ind=ind))
                if d['children']:
                    prn(d['children'], lvl + 1)

        # Do not load deleted records
        rs = self.sess.query(prm.ResourceNode).filter(
            prm.ResourceNode.dtime == None
        ).order_by(
            sa.sql.expression.nullsfirst(prm.ResourceNode.parent_id),
            prm.ResourceNode.sortix,
            prm.ResourceNode.name
        )
        pp = _list_to_tree(todata(rs))
        prn(pp, 0)
        if out:
            self._print_txt(out)


def parse_args(app):
    # Main parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Parenchym command-line interface.""",
        epilog=textwrap.dedent('''\
        Samples:

        pym -c production.ini --format tsv ls group-member > /tmp/a.txt && gnumeric /tmp/a.txt

        pym -c development.ini --format yaml create group '{name: fs_writer, descr: Can write files via FS, tenant_id: 1}'
        '''))
    parser.add_argument(
        '--yes',
        help="Answer all prompts with YES, useful for scripting",
        action='store_true'
    )
    parser.add_argument(
        '--actor',
        help="Principal or ID of user who performs this command. Will be OWNER"
             "on creates, EDITOR on updates and, DELETER on deletes. If omitted,"
             "we use the login name of the console user.",
    )
    app.add_parser_args(parser, (('config', True),
        ('locale', False), ('alembic-config', False), ('format', False)))
    subparsers = parser.add_subparsers(title="Commands", dest="subparser_name",
        help="""Type 'pym COMMAND --help'""")

    # Parser cmd ls
    p_ls = subparsers.add_parser('ls',
        help="List all records of an entity")
    p_ls.set_defaults(func=app.cmd_ls)
    p_ls.add_argument(
        'entity',
        help='Entity',
        choices=list(sorted(Runner.ENTITIES.keys()))
    )
    p_ls.add_argument(
        '--with-deleted',
        help='Show also deleted records',
        action='store_true'
    )

    # Parser cmd permission-tree
    p_permission_tree = subparsers.add_parser('permission-tree',
        help="Show permission tree")
    p_permission_tree.set_defaults(func=app.cmd_permission_tree)

    # Parser cmd resource-tree
    p_resource_tree = subparsers.add_parser('resource-tree',
        help="Show resource tree")
    p_resource_tree.set_defaults(func=app.cmd_resource_tree)
    p_resource_tree.add_argument(
        '-v', '--verbose',
        action='count',
        help="""Show detailed info about each node"""
    )
    p_resource_tree.add_argument(
        '--with-acl',
        action='store_true',
        help="""Show ACL of each node"""
    )

    # Parser cmd create
    p_create = subparsers.add_parser('create',
        help="Create an entity")
    p_create.set_defaults(func=app.cmd_create)
    p_create.add_argument(
        'entity',
        help='Entity',
        choices=list(sorted(Runner.ENTITIES.keys()))
    )
    p_create.add_argument(
        'data',
        help='Data as YAML or JSON, as set with --format'
    )

    # Parser cmd update
    p_update = subparsers.add_parser('update',
        help="Update an entity")
    p_update.set_defaults(func=app.cmd_update)
    p_update.add_argument(
        '--id',
        help='ID of the entity to update',
        required=True
    )
    p_update.add_argument(
        'entity',
        help='Entity',
        choices=list(sorted(Runner.ENTITIES.keys()))
    )
    p_update.add_argument(
        'data',
        help='Data as YAML or JSON, as set with --format'
    )

    # Parser cmd delete
    p_delete = subparsers.add_parser('delete',
        help="Delete an entity")
    p_delete.set_defaults(func=app.cmd_delete)
    p_delete.add_argument(
        '--delete-from-db',
        action='store_true',
        default=False,
        help='If given, entities are deleted from database, else only marked as'
             ' deleted'
    )
    ee = sorted(list(Runner.ENTITIES.keys()) + ['ace'])
    p_delete.add_argument(
        'entity',
        help='Entity',
        choices=ee
    )
    p_delete.add_argument(
        'id',
        help='ID of the entity to delete'
    )

    # Parser cmd allow
    p_allow = subparsers.add_parser('allow',
        help="Allow a permission")
    p_allow.set_defaults(func=app.cmd_allow)
    p_allow.add_argument(
        'resource_id',
        help='Allow permission on this resource (ID)'
    )
    p_allow.add_argument(
        'permission',
        help='Allow this permission (name or ID)'
    )
    p_allow.add_argument(
        'who',
        help='Allow to this group (name or ID) or user (principal or ID). Prefix'
             'group with "g:" and user with "u:"'
    )

    return parser.parse_args()


def main(argv=None):
    start_time = time.time()
    if not argv:
        argv = sys.argv

    app_name = os.path.basename(argv[0])
    lgg = logging.getLogger('cli.' + app_name)

    # noinspection PyBroadException
    try:
        runner = Runner()
        args = parse_args(runner)
        runner.init_app(args, lgg=lgg, setup_logging=True)
        if hasattr(args, 'func'):
            args.func()
        else:
            runner.run()
    except Exception as exc:
        lgg.exception(exc)
        lgg.fatal('Program aborted!')
    else:
        # Clear redis cache
        runner.cache.flushall()
        lgg.info('Finished.')
    finally:
        lgg.info('Time taken: {}'.format(
            datetime.timedelta(seconds=time.time() - start_time))
        )


if __name__ == '__main__':
    main(sys.argv)
