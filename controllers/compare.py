import os
import time
import json
import github_client

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    def GET(base,head,jsoncallback=None,callback=None,_=None,**kwargs):
        "OpenTree API methods relating to comparing commits"

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # Get the GitHub API auth-token for a logged-in curator
        auth_token = kwargs.get('auth_token', 'ANONYMOUS')
        if auth_token == 'ANONYMOUS':
            # non-web callers might be using an HTTP header ("Authorization: token abc123def456")
            auth_header = request.env.get('http_authorization', None) or request.wsgi.environ.get('HTTP_AUTHORIZATION', None)
            if auth_header:
                auth_token = auth_header.split()[1]

        return github_client.compare("OpenTreeOfLife/treenexus",base,head, auth_token)

    return locals()
