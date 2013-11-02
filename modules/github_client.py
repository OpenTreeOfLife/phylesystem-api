#!/usr/bin/env python
import sys
import github
from github import Github, GithubException, BadCredentialsException
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


def fetch_study(study_id, auth_info):
    #headers = build_common_api_headers()
    gh = Github(auth_info.get('token', None))
    # TODO: use the proper sequence of API calls
    #   find the 'treenexus' repo (confirm it exists and is available)
    #   does this user have an existing study (WIP) branch?
    #   IF SO, fetch latest from this branch
    #   IF NOT, fetch the 'master' version


# if this is run as standalone script, run some initial tests and demos
# EXAMPLE:   $ github_client.py AUTH_TOKEN    <== unquoted OAuth token
def main(*args):
    # test to see if we're running inside web2py or standalone
    if in_web2py:
        if current:
            print( 'We are in web2py and in a web request, client IP is [%s]' % current.request.client )
        else:
            print( 'We are in web2py, but no web request found' )
    else:
        print( 'Not running in web2py!' );

    # args should be a tuple (strings passed on the command line)
    if len(args) < 2:
        print('Usage: github_client.py AUTH_TOKEN')
        return

    # expecting OAuth token as second argument
    print('Quick test of API call and auth token...')
    token = args[1]
    try:
        gh = Github( token )
        gh_user = gh.get_user()
        TEST_login = gh_user.login   # needed to raise bad-credential exception
    except BadCredentialsException, e:
        print('Bad credentials! Please proofread (or refresh) the auth token.')
        return
    except GithubException, e:
        print('Something else went wrong (too many login attempts?)')
        return
    except Exception, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return

    print('Current Github API status: %s' % (gh.get_api_status().status,))
    print('This token is for user [%s] "%s <%s>"' % (gh_user.login, gh_user.name, gh_user.email,))
    print('Repos for this user:')
    for repo in gh_user.get_repos():
        print '  %s' % repo.name
    print('Rate limiting: %s' % (gh.rate_limiting,) );
    print('Rate limiting reset time: %s' % (gh.rate_limiting_resettime,) );


__name__ == '__main__' and main(*sys.argv)
