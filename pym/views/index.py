from pyramid.security import (
    NO_PERMISSION_REQUIRED
)
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pym.lib import json_serializer
import pym.models
import pym.res.models
import pym.auth.models
from pym.tenants.const import DEFAULT_TENANT_NAME
import pym.tenants.manager
import pym.resp
import pym.menu


# noinspection PyUnusedLocal
@view_config(
    name='',
    context=pym.res.models.IRootNode,
    renderer='pym:templates/index.mako',
    permission=NO_PERMISSION_REQUIRED
)
def index(context, request):
    if request.user.is_auth():
        return HTTPFound(location=request.resource_url(request.root, 'main'))
    return dict()


# noinspection PyUnusedLocal
@view_config(
    name='imprint',
    context=pym.res.models.IRootNode,
    renderer='pym:templates/imprint.mako',
    permission=NO_PERMISSION_REQUIRED
)
def imprint(context, request):
    return dict()


# noinspection PyUnusedLocal
@view_config(
    name='main',
    context=pym.res.models.IRootNode,
    renderer='pym:templates/main.mako',
    permission='visit'
)
def main(context, request):
    # Enum tenants to which current user belongs.
    # If only one, redirect to tenant home page,
    # if several, let him choose.
    sess = pym.models.DbSession()
    tt = pym.tenants.manager.collect_my_tenants(sess, request.user.uid)
    if len(tt) == 1:
        url = request.resource_url(context[tt[0].name])
        return HTTPFound(location=url)
    else:
        return dict(tenants=tt)


@view_config(
    name='xhr_main_menu',
    context=pym.res.models.IRootNode,
    renderer='string',
    permission=NO_PERMISSION_REQUIRED
)
def xhr_main_menu(context, request):
    # TODO Build different menus for un/authenticated users
    resp = pym.resp.JsonResp()
    resp.data = pym.menu.main_menu(
        root_node=request.root,
        url_to=request.resource_url,
        tenant=DEFAULT_TENANT_NAME,
        translate=request.localizer.translate
    )
    return json_serializer(resp.resp)
