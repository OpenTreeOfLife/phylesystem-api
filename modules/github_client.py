#!/usr/bin/env python
import sys
import github
from github import Github, GithubException, BadCredentialsException, UnknownObjectException
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


def fetch_study(study_id, token):
    #headers = build_common_api_headers()
    try:
        gh = Github(token)
        gh_user = gh.get_user()
        gh_username = gh_user.login
    except BadCredentialsException, e:
        print('Bad credentials! Please proofread (or refresh) the auth token.')
        return
    except GithubException, e:
        print('Something else went wrong (too many login attempts?)')
        return
    except Exception, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return

    # find the 'treenexus' repo (confirm it exists and is available)
    repo_path = 'OpenTreeOfLife/treenexus'  # TODO: pull from config file?
    try:
        data_repo = gh.get_repo( repo_path )
    except UnknownObjectException, e:
        pprint('Data repo "%s" not found! (%s)' % (repo_path, e))
        return

    pprint( data_repo )
    # does the user have a WIP (work in progress) branch for this study?
    wip_branch_name = '%s_study_%s' % (gh_username, study_id,)  # eg, 'janet_study_123'
    public_branch_name = 'master'
    # try to fetch a WIP branch at this name
    study_branch = None
    try:
        study_branch = data_repo.get_branch( wip_branch_name )
    except GithubException, e:
        print('No WIP branch (%s)' % (e,))
        # try to fetch the master branch instead
        try:
            study_branch = data_repo.get_branch( public_branch_name )
        except GithubException, e:
            print('No master branch (%s)' % (e,))
    
    if study_branch is None:
        print('No study branches were found (this is very unexpected)')
        return

    study_ref = study_branch.commit.commit.sha
    print('Current study is on branch "%s", at commit %s' % (study_branch.name, study_ref))

    # TODO: confine this to the appropriate branch!?
    study_path = '/study/1001/1001.json'
    pprint('study_path: [%s]' % study_path)

    try:
        main_study_file = data_repo.get_file_contents( path=study_path, ref=study_ref )
    except Exception, e:
        print('No file found at this path (this is somewhat unexpected)')
        return

    # ...or should we use Repository.get_contents?
    study_nexson = main_study_file.content.decode( encoding=main_study_file.encoding )
    return study_nexson

    # TODO: Later we might want everything in the study directory
    ##print('get_dir_contents(study/1001)')
    ##pprint( data_repo.get_dir_contents( path = '/study/1001/') )


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
    test_study_id = 1001
    print('Test of fetch_study (id=%s)...' % test_study_id)
    print(fetch_study( test_study_id, token )[:800])
    print('...etc...')

__name__ == '__main__' and main(*sys.argv)
