#!/usr/bin/env python
import os
from ConfigParser import SafeConfigParser
import sys
import github
from github import Github, GithubException, BadCredentialsException, UnknownObjectException
# diagnostic helpers
from pprint import pprint
# NOTE: un-comment this to emit API chatter to stdout!
##github.enable_console_debug_logging()
import simplejson as json

# can we import web2py API (current, etc)?
in_web2py = False
app_name = 'api'  # default name, in case we're outside of web2py
try:
    from gluon import *
    if current:
        in_web2py = True
except:
    pass

def get_registered_app_secrets():
    # for anonymous visitors, fetch client ID and secret for this app (as registered with Github)
    Github_client_id = 'CLIENT_ID_NOT_FOUND'
    Github_client_secret = 'CLIENT_SECRET_NOT_FOUND'
    if in_web2py:
        app_name = current.request.application
    conf = SafeConfigParser(allow_no_value=True)
    try:
        # NOTE: This assumes that request.application EXACTLY matches the filesystem path
        print(">> LOOKING FOR %s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,))
        print(">>          OR %s/applications/%s/private/config" % (os.path.abspath('.'), app_name,))
        if os.path.isfile("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,)):
            conf.read("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,))
        else:
            conf.read("%s/applications/%s/private/config" % (os.path.abspath('.'), app_name,))
        Github_client_id = conf.get("apis", "github_client_id")
        Github_client_secret = conf.get("apis", "github_client_secret")
    except Exception, e:
        print('ERROR reading config file. Try running your script from the main web2py directory!')
        print('Exception details: %s' % (e,))

    return (Github_client_id, Github_client_secret)

def compare(repo_path, base, head, token):
    """Compare two commits (by SHA or branch name) and return a list of changed files

    Example URL: http://localhost:8080/api/compare/v1/c3608e5/master

    which calls out to https://api.github.com/repos/OpenTreeOfLife/treenexus/compare/c3608e5...master

"""
    (gh,gh_user,gh_username) = authenticate(token)

    repo = gh.get_repo(repo_path)

    comparison = repo.compare(base,head)

    excludes = [ ".to_download.json" ]

    files         = [ f for f in comparison.files if f.filename not in excludes ]
    changed_files = [ f.filename for f in files if f.status == "modified" ]
    added_files   = [ f.filename for f in files if f.status == "added"    ]
    removed_files = [ f.filename for f in files if f.status == "removed"  ]
    renamed_files = [ f.filename for f in files if f.status == "renamed"  ]

    return json.dumps(
        {
            "changed": changed_files,
            "added":   added_files,
            "removed": removed_files,
            "renamed": renamed_files,
        }
    )

def authenticate(token):
    try:
        if token == 'ANONYMOUS':
            (Github_client_id, Github_client_secret,) = get_registered_app_secrets()
            pprint('>>>>> Github_client_id: [%s]' % (Github_client_id,))
            pprint('>>>>> Github_client_secret: [%s]' % (Github_client_secret,))
            gh = Github(client_id=Github_client_id, client_secret=Github_client_secret)
            # there's no user to grab
            gh_user = None
            gh_username = 'ANONYMOUS_VISITOR'
        else:
            # grab info and name of logged-in user
            gh = Github(token)
            gh_user = gh.get_user()
            gh_username = gh_user.login

        return (gh,gh_user,gh_username)

    except BadCredentialsException, e:
        print('Bad credentials! Please proofread (or refresh) the auth token.')
        return 'Bad credentials! Please proofread (or refresh) the auth token.'
    except GithubException, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return 'Something else went wrong <%s>: %s' % (type(e), e,)
    except Exception, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return 'Something else went wrong <%s>: %s' % (type(e), e,)


def fetch_study(study_id, token):
    # Fetch study data using auth token, if provided, or using app secret for an
    # anonymous visitor (to take advantage of our high rate limit)
    pprint('>>>>> token: [%s]' % (token,))

    (gh,gh_user,gh_username) = authenticate(token)

    # find the 'treenexus' repo (confirm it exists and is available)
    repo_path = 'OpenTreeOfLife/treenexus'  # TODO: pull from config file?
    try:
        data_repo = gh.get_repo( repo_path )
    except UnknownObjectException, e:
        pprint('Data repo "%s" not found! (%s)' % (repo_path, e))
        return 'Data repo "%s" not found! (%s)' % (repo_path, e)

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
        return 'No study branches were found (this is very unexpected)'

    study_ref = study_branch.commit.commit.sha
    print('Current study is on branch "%s", at commit %s' % (study_branch.name, study_ref))

    # TODO: confine this to the appropriate branch!?
    study_path = '/study/%s/%s.json' % (study_id, study_id,)
    pprint('study_path: [%s]' % study_path)

    try:
        main_study_file = data_repo.get_file_contents( path=study_path, ref=study_ref )
    except Exception, e:
        print('No file found at this path (this is somewhat unexpected)')
        return 'No file found at this path (this is somewhat unexpected)'

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
        return 'Usage: github_client.py AUTH_TOKEN'

    # expecting OAuth token as second argument
    print('Quick test of API call and auth token...')
    token = args[1]
    try:
        gh = Github( token )
        gh_user = gh.get_user()
        TEST_login = gh_user.login   # needed to raise bad-credential exception
    except BadCredentialsException, e:
        print('Bad credentials! Please proofread (or refresh) the auth token.')
        return 'Bad credentials! Please proofread (or refresh) the auth token.'
    except GithubException, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return 'Something else went wrong <%s>: %s' % (type(e), e,)
    except Exception, e:
        print('Something else went wrong <%s>: %s' % (type(e), e,))
        return 'Something else went wrong <%s>: %s' % (type(e), e,)

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
