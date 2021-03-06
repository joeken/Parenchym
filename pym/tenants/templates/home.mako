<%!
    from pym.res.const import NODE_NAME_SYS
    from pym.auth.const import (NODE_NAME_SYS_AUTH_MGR, NODE_NAME_SYS_AUTH_USER_MGR,
        NODE_NAME_SYS_AUTH_GROUP_MGR, NODE_NAME_SYS_AUTH_GROUP_MEMBER_MGR,
        NODE_NAME_SYS_AUTH_PERMISSION_MGR)
%>
<%
    node_sys = request.root[NODE_NAME_SYS]
    node_auth = node_sys[NODE_NAME_SYS_AUTH_MGR]
    url_to = request.resource_url
%>
<%inherit file="pym:templates/_layouts/default.mako" />
<%block name="meta_title">Welcome</%block>
<%block name="styles">
${parent.styles()}
</%block>

<div class="row">

  <div class="col-md-4">
    <ul>
      <li><a href="${url_to(request.root)}">General</a>
        <ul>
          <li><a href="${url_to(request.root)}">Foo</a>
          </li>
        </ul>
      </li>
    </ul>
  </div>


  <div class="col-md-offset-4 col-md-4">
    <ul>
      <li><a href="${url_to(node_sys)}">System</a>
        <ul>
          <li><a href="${url_to(node_auth)}">Authentication Manager</a>
            <ul>
              <li><a href="${url_to(node_auth[NODE_NAME_SYS_AUTH_USER_MGR])}">Manage Users</a>
              </li>
              <li><a href="${url_to(node_auth[NODE_NAME_SYS_AUTH_GROUP_MGR])}">Manage Groups</a>
              </li>
              <li><a href="${url_to(node_auth[NODE_NAME_SYS_AUTH_GROUP_MEMBER_MGR])}">Manage Group Members</a>
              </li>
              <li><a href="${url_to(node_auth[NODE_NAME_SYS_AUTH_PERMISSION_MGR])}">Manage Permissions</a>
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
  </div>
</div>


<div class="outer-gutter">

  <p>M.A.I.N.</p>

</div>
