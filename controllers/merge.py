import os
import time
import json
import gitdata
import api_utils
from gitdata import GitData
from locket import LockError

@request.restful()
def v1():
    "The OpenTree API v1: Merge Controller"
    response.view = 'generic.json'

    def POST(branch,base_branch="master",jsoncallback=None,callback=None,_=None,**kwargs):
        """OpenTree API methods relating to merging branches

        This controller implements the merging of branches via the API.

        For example, to merge the branch leto_study_12 to master via curl:

        curl -X POST http://localhost:8000/api/merge/v1/leto_study_12/master?auth_token=$GITHUB_OAUTH_TOKEN

        where the first branch is the branch to merge *in* and the second is
        the branch to merge *into*. The second branch defaults to "master", so
        this request is equivalent to the above:

        curl -X POST http://localhost:8000/api/merge/v1/leto_study_12?auth_token=$GITHUB_OAUTH_TOKEN

        If the request is successful, a JSON response similar to this will be returned:

        {
            "error": 0,
            "branch_name": "master",
            "description": "Merged branch leto_study_12",
            "sha":  "dcab222749c9185797645378d0bda08d598f81e7"
        }

        If there is an error, an HTTP 400 error will be returned with a JSON response similar
        to this:

        {
            "error": 1,
            "description": "Could not push foo branch"
        }
        """

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        (gh, author_name, author_email) = api_utils.authenticate(**kwargs)

        repo_path, repo_remote, git_ssh, pkey = api_utils.read_config(request)
        git_env     = {"GIT_SSH": git_ssh, "PKEY": pkey}

        gd = GitData(repo=repo_path)

        if branch == base_branch:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Cannot merge %s branch to itself" % branch
            }))

        for b in [ branch, base_branch ]:
            if not gd.branch_exists(b):
                raise HTTP(400, json.dumps({
                    "error": 1,
                    "description": "Cannot merge non-existent branch %s" % b
                }))

        try:
            gd.acquire_lock()
        except LockError, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not acquire lock to merge branch %s" % branch
            }))

        try:
            # do the merge
            new_sha = gd.merge(branch, base_branch)
        except Exception, e:
            gd.release_lock()

            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not merge! Details: %s" % (e.message)
            }))

        try:
            # actually push the changes to Github
            gd.push(repo_remote, env=git_env,branch=base_branch)
        except Exception, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not push %s branch! Details: \n%s" % (base_branch, e.message)
            }))

        try:
            # delete the WIP branch we just merged in on our remote
            gd.delete_remote_branch(repo_remote, env=git_env, branch=branch)
        except Exception, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not delete remote branch %s! Details:\n%s" % (branch, e.message)
            }))

        finally:
            gd.release_lock()

        return {
            "error": 0,
            "branch_name": base_branch,
            "description": "Merged branch %s" % branch,
            "sha":  new_sha
        }

    return locals()
