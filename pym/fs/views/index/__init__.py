import logging
from pyramid.view import view_config, view_defaults
import pyramid.i18n
from pym.lib import json_serializer
from ...models import IFsNode
import pym.i18n
from pym.auth.models import Permissions
from pym.models import DbSession


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


@view_defaults(
    context=IFsNode,
    permission=Permissions.read.name
)
class FsView(object):

    def __init__(self, context, request):
        """
        View 'me' (personal pages).
        """
        self.context = context
        self.request = request
        self.sess = DbSession()
        self.lgg = logging.getLogger(__name__)

        self.urls = dict(
            index=request.resource_url(context),
        )

    @view_config(
        name='',
        renderer='index.mako',
        request_method='GET'
    )
    def index(self):
        rc = {
            'urls': self.urls
        }
        return {
            'rc': rc,
        }
