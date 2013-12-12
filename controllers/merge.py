import os
import time
import json
import gitdata
import api_utils
from locket import LockError

@request.restful()
def v1():
    "The OpenTree API v1: Merge Controller"
    response.view = 'generic.json'

    def POST(branch,base_branch="master",jsoncallback=None,callback=None,_=None,**kwargs):
        "OpenTree API methods relating to merging branching"

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # TODO: authenticate

        repo_path, repo_remote, git_ssh, pkey = api_utils.read_config(request)
        git_env     = {"GIT_SSH": git_ssh, "PKEY": pkey}

        gd = GitData(repo=repo_path)

        # Check if both branches exist

        try:
            gd.acquire_lock()
        except LockError, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not acquire lock to write to study #%s" % resource_id
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

        # TODO: push correct branch


    return locals()
