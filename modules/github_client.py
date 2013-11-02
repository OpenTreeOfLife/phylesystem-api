#!/usr/bin/env python
import sys
from github import Github
# diagnostic helpers
from pprint import pprint


# can we import web2py API (current, etc)?
in_web2py = False
try:
    from gluon import *
    if current:
        in_web2py = True
except:
    pass


def build_common_api_headers(auth_info):
    if auth_info:
        oauth_token = auth_info['token'] or 'AUTH_NO_TOKEN'
    elif in_web2py:
        oauth_token = current.request.args['auth_token'] or 'ANONYMOUS_VISITOR'
    else:
        # mock a fake request with canned values?
        oauth_token = ''

    return {
        'User-Agent': 'Open Tree of Life - Study Curation App',
        'Authentication': ('token %s' % oauth_token),

        # TODO: more headers to use cached results if no change
        # http://developer.github.com/v3/#conditional-requests
        ##'If-None-Match': '',
        ##'If-Modified-Since': '',

        # TODO: if we need to support CORS
        # http://developer.github.com/v3/#cross-origin-resource-sharing

        # TODO: if we need to fetch JSON-P
        # http://developer.github.com/v3/#json-p-callbacks
    }

def fetch_study(study_id, auth_info):
    #headers = build_common_api_headers()
    gh = Github(auth_info.get('token', None))
    for repo in gh.get_user().get_repos():
        print repo.name
        #repo.edit(has_wiki=False)


# add testing or other behavior if run as standalone script
def main(*args):
    # args is a tuple of strings passed on the command line
    if len(args) < 2:
        print('Usage: github_client.py AUTH_TOKEN')
        return

    # expecting OAuth token as second argument
    token = args[1]

    if in_web2py:
        if current:
            pprint( 'We are in a web request, client IP is [%s]' % current.request.client )
        else:
            pprint( 'No web request found' )
    else:
        pprint( 'Not running in web2py!' );

    output = fetch_study(23, {'token': token})
    pprint( output )


__name__ == '__main__' and main(*sys.argv)
