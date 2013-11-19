import os
import time
import json
from githubsearch import GithubSearch

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    def GET(search_term,jsoncallback=None,callback=None,_=None,**kwargs):
        "OpenTree API methods relating to searching"

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        gs = GithubSearch()
        return gs.search(search_term)

    return locals()
