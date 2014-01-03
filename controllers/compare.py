import os
import time
import json
import api_utils

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

        repo_path, repo_remote, git_ssh, pkey = api_utils.read_config(request)

        return _compare(repo_path,base,head, auth_token)

    def _compare(repo_path, base, head, token):
        """Compare two commits (by SHA or branch name) and return a list of changed files

        Example URL: http://localhost:8080/api/compare/v1/c3608e5/master

        which calls out to https://api.github.com/repos/OpenTreeOfLife/REPO/compare/c3608e5...master

        where REPO is the data repo which contains NEXSON files.

    """
        (gh,gh_user,gh_username) = api_utils.authenticate(auth_token=token)

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

    return locals()
