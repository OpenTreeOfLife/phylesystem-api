import os
import time
import json
import api_utils
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             merge_from_master

@request.restful()
def v1():
    """The OpenTree API v1: Merge Controller

    This controller can be used to merge changes from master into
    a WIP. After this succeeds, subsequent GETs and POSTs to the study
    should be able to merge to master.
    """
    response.view = 'generic.json'

    def PUT(resource_id, starting_commit_SHA, jsoncallback=None,callback=None,_=None,**kwargs):
        """OpenTree API methods relating to updating branches

        curl -X POST http://localhost:8000/api/merge/v1?resource_id=9&starting_commit_SHA=152316261261342&auth_token=$GITHUB_OAUTH_TOKEN

        If the request is successful, a JSON response similar to this will be returned:

        {
            "error": 0,
            "branch_name": "my_user_9_2",
            "description": "Updated branch",
            "sha": "dcab222749c9185797645378d0bda08d598f81e7",
            "merged_SHA": "16463623459987070600ab2757540c06ddepa608",
        }

        'merged_SHA' must be included in the next PUT for this study (unless you are
            happy with your work languishing on a WIP branch instead of master).

        If there is an error, an HTTP 400 error will be returned with a JSON response similar
        to this:

        {
            "error": 1,
            "description": "Could not merge master into WIP! Details: ..."
        }
        """

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'
        auth_info = api_utils.authenticate(**kwargs)
        phylesystem = api_utils.get_phylesystem(request)
        gd = phylesystem.create_git_action(resource_id)
        try:
            return merge_from_master(gd, resource_id, auth_info, starting_commit_SHA)
        except GitWorkflowError, err:
            raise HTTP(400, json.dumps({"error": 1, "description": err.msg}))
        except Exception, e:
            raise HTTP(409, json.dumps({
                "error": 1,
                "description": "Could not pull! Details: %s" % (e.message)
            }))

    return locals()
