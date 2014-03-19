import os
import time
import json
import gitdata
import api_utils
from gitdata import GitData
from locket import LockError
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             merge_from_master

@request.restful()
def v1():
    """The OpenTree API v1: Pull Controller

    This controller can be used to update local branches from our remote, to keep the local and remote repo in sync.
    """
    response.view = 'generic.json'

    def POST(resource_id, starting_commit_SHA, jsoncallback=None,callback=None,_=None,**kwargs):
        """OpenTree API methods relating to updating branches

        curl -X POST http://localhost:8000/api/pull/v1?starting_commit_SHA=152316261261342&auth_token=$GITHUB_OAUTH_TOKEN

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
        auth_info = api_utils.authenticate(**kwargs)
        repo_path = api_utils.read_config(request)[0]
        gd = GitData(repo=repo_path)
        try:
            return merge_from_master(gd, resource_id, auth_info, starting_commit_SHA)
        except GitWorkflowError, err:
            raise HTTP(400, json.dumps({"error": 1, "description": err.msg}))
        except Exception, e:
            raise HTTP(409, json.dumps({
                "error": 1,
                "description": "Could not pull! Details: %s" % (e.message)
            }))
