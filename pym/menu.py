import functools
import pyramid.i18n
import pyramid.location

import pym.i18n
from pym.tenants.const import DEFAULT_TENANT_NAME
from pym.sys.const import NODE_NAME_SYS, NODE_NAME_SYS_CACHE_MGMT
from pym.auth.const import (NODE_NAME_SYS_AUTH_MGR, NODE_NAME_SYS_AUTH_USER_MGR,
                            NODE_NAME_SYS_AUTH_GROUP_MGR,
                            NODE_NAME_SYS_AUTH_GROUP_MEMBER_MGR,
                            NODE_NAME_SYS_AUTH_PERMISSION_MGR)

_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


# TODO Build menus from table pym.resource_tree


# def foo_menu(root_node, url_to, tenant=DEFAULT_TENANT_NAME,
#         translate=lambda s: s):
#     home_node = root_node[tenant]
#     # Foo
#     node0 = home_node[NODE_NAME_FOO]
#     id_ = resource_path(node0)
#     menu = {
#         'id': id_,
#         'text': translate(_("Foo")),
#         'href': url_to(node0),
#         'children': []
#     }
#     # Foo / Bar
#     node = node0[NODE_NAME_FOO_BAR]
#     id_ = resource_path(node)
#     menu['children'].append({
#         'id': id_,
#         'text': translate(_("Bar")),
#         'href': url_to(node)
#     })
#     return menu


def sys_menu(root_node, url_to, tenant=DEFAULT_TENANT_NAME,
        translate=lambda s: s):
    # Sys
    node_sys = root_node[NODE_NAME_SYS]
    id_ = resource_path(node_sys)
    menu_sys = {
        'id': id_,
        'text': translate(_("System")),
        'href': url_to(node_sys),
        'children': []
    }
    # Sys / AuthMgr
    node_auth_mgr = node_sys[NODE_NAME_SYS_AUTH_MGR]
    id_ = resource_path(node_auth_mgr)
    menu_sys['children'].append({
        'id': id_,
        'text': translate(_("AuthMgmt")),
        'href': url_to(node_auth_mgr),
        'children': []
    })
    # Sys / AuthMgr / Users
    node = node_auth_mgr[NODE_NAME_SYS_AUTH_USER_MGR]
    id_ = resource_path(node)
    menu_sys['children'][-1]['children'].append({
        'id': id_,
        'text': translate(_("Users")),
        'href': url_to(node)
    })
    # Sys / AuthMgr / Groups
    node = node_auth_mgr[NODE_NAME_SYS_AUTH_GROUP_MGR]
    id_ = resource_path(node)
    menu_sys['children'][-1]['children'].append({
        'id': id_,
        'text': translate(_("Groups")),
        'href': url_to(node)
    })
    # Sys / AuthMgr / GroupMembers
    node = node_auth_mgr[NODE_NAME_SYS_AUTH_GROUP_MEMBER_MGR]
    id_ = resource_path(node)
    menu_sys['children'][-1]['children'].append({
        'id': id_,
        'text': translate(_("Group Members")),
        'href': url_to(node)
    })
    # Sys / AuthMgr / Perms
    node = node_auth_mgr[NODE_NAME_SYS_AUTH_PERMISSION_MGR]
    id_ = resource_path(node)
    menu_sys['children'][-1]['children'].append({
        'id': id_,
        'text': translate(_("Permissions")),
        'href': url_to(node)
    })
    # Sys / CacheMgmt
    node = node_sys[NODE_NAME_SYS_CACHE_MGMT]
    id_ = resource_path(node)
    menu_sys['children'].append({
        'id': id_,
        'text': translate(_("Cache Management")),
        'href': url_to(node)
    })
    return menu_sys


def main_menu(root_node, url_to, tenant=DEFAULT_TENANT_NAME,
        translate=lambda s: s):
    menu = [
        sys_menu(root_node, url_to, tenant, translate),
    ]
    return menu


def resource_path(resource, *elements):
    """
    Works as ``pyramid.traversal.resource_path()`` except does not quote
    or escape elements.
    """
    # joining strings is a bit expensive so we delegate to a function
    # which caches the joined result for us.
    # Borrowed from pyramid.traversal.
    return _join_tuple(resource_path_tuple(resource, *elements))


def resource_path_tuple(resource, *elements):
    """
    Borrowed from ``pyramid.traversal.resource_path_tuple()``.
    """
    return tuple(_resource_path_list(resource, *elements))


def _resource_path_list(resource, *elements):
    """ Implementation detail shared by resource_path and resource_path_tuple"""
    path = [loc.__name__ or '' for loc in pyramid.location.lineage(resource)]
    path.reverse()
    path.extend(elements)
    return path


@functools.lru_cache(maxsize=128)
def _join_tuple(some_tuple):
    return some_tuple and '/'.join([x for x in some_tuple]) or '/'
