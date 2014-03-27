import os
import time
import json
import api_utils
import traceback
@request.restful()
def v1():
    """The OpenTree API v1: Merge Controller

    This controller can be used to merge changes from master into
    a WIP. After this succeeds, subsequent GETs and POSTs to the study
    should be able to merge to master.
    """
    response.view = 'generic.json'

    def PUT(resource_id=None, jsoncallback=None,callback=None,_=None,**kwargs):
        """OpenTree API methods relating to updating branches

        curl -X POST http://localhost:8000/api/push/v1?resource_id=9
        """

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'
        phylesystem = api_utils.get_phylesystem(request)
        try:
            phylesystem.push_study_to_remote('GitHubRemote', resource_id)
        except:
            m = traceback.format_exc()
            raise HTTP(409, json.dumps({
                "error": 1,
                "description": "Could not push! Details: {m}".format(m=m)
            }))
        return {'error': 0,
                'description': 'Push succeeded'}
    return locals()