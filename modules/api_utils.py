from ConfigParser import SafeConfigParser
from github import Github, BadCredentialsException
import os
import json

# this allows us to raise HTTP(...)
from gluon import *

def read_config(request):
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    localconfig_filename = "%s/applications/%s/private/localconfig" % (request.env.web2py_path, app_name)

    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    else:
        filename = "%s/applications/%s/private/config" % (request.env.web2py_path, app_name)
        conf.readfp(open(filename))

    repo_path   = conf.get("apis","repo_path")
    repo_remote = conf.get("apis", "repo_remote")
    git_ssh     = conf.get("apis", "git_ssh")
    pkey        = conf.get("apis", "pkey")

    return repo_path, repo_remote, git_ssh, pkey

def authenticate(**kwargs):
    # this is the GitHub API auth-token for a logged-in curator
    auth_token   = kwargs.get('auth_token','')

    if not auth_token:
        raise HTTP(400,json.dumps({
            "error": 1,
            "description":"You must provide an auth_token to authenticate to the OpenTree API"
        }))
    gh           = Github(auth_token)
    gh_user      = gh.get_user()

    try:
        gh_user.login
    except BadCredentialsException:
        raise HTTP(400,json.dumps({
            "error": 1,
            "description":"You have provided an invalid or expired authentication token"
        }))

    author_name  = kwargs.get('author_name','')
    author_email = kwargs.get('author_email','')

    # use the Github Oauth token to get a name/email if not specified
    # we don't provide these as default values above because they would
    # generate API calls regardless of author_name/author_email being specifed

    if not author_name:
        author_name = gh_user.name
    if not author_email:
        author_email = gh_user.email

    return gh, author_name, author_email
