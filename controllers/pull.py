import os
import time
import json
import gitdata
import api_utils
from gitdata import GitData
from locket import LockError

@request.restful()
def v1():
    """The OpenTree API v1: Pull Controller

    This controller can be used to update local branches from our remote, to keep the local and remote repo in sync.
    """
    response.view = 'generic.json'

    def POST(branch="master",jsoncallback=None,callback=None,_=None,**kwargs):
        """OpenTree API methods relating to updating branches

        This controller implements the updating of a branch (pulling it from our remote) via the API.

        For example, to update the branch leto_study_12 via curl:

        curl -X POST http://localhost:8000/api/pull/v1/leto_study_12?auth_token=$GITHUB_OAUTH_TOKEN

        The default branch is master, so to pull in changes from our remote master:

        curl -X POST http://localhost:8000/api/pull/v1?auth_token=$GITHUB_OAUTH_TOKEN

        If the request is successful, a JSON response similar to this will be returned:

        {
            "error": 0,
            "branch_name": "master",
            "description": "Updated branch",
            "sha":  "dcab222749c9185797645378d0bda08d598f81e7"
        }

        If there is an error, an HTTP 400 error will be returned with a JSON response similar
        to this:

        {
            "error": 1,
            "description": "Could not pull from remote origin! Details: ..."
        }
        """

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        (gh, author_name, author_email) = api_utils.authenticate(**kwargs)

        repo_path, repo_remote, git_ssh, pkey = api_utils.read_config(request)
        git_env     = {"GIT_SSH": git_ssh, "PKEY": pkey}

        gd = GitData(repo=repo_path)

        try:
            gd.acquire_lock()
        except LockError, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not acquire lock to pull branch %s" % branch
            }))

        try:
            # do the pull
            new_sha = gd.pull(repo_remote, env=git_env, branch=branch)
        except Exception, e:
            gd.release_lock()

            # Attempt to abort a merge, in case of conflicts
            try:
                git.merge("--abort")
            except:
                pass

            raise HTTP(409, json.dumps({
                "error": 1,
                "description": "Could not pull! Details: %s" % (e.message)
            }))
        finally:
            gd.release_lock()

        return {
            "error": 0,
            "branch_name": branch,
            "description": "Updated branch %s" % branch,
            "sha":  new_sha
        }

    return locals()
