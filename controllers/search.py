import os
import time
import json
import requests
from oti_search import OTISearch
from ConfigParser import SafeConfigParser

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    if os.path.isfile("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,)):
        conf.read("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,))
    else:
        conf.read("%s/applications/%s/private/config" % (os.path.abspath('.'), app_name,))

    if conf.has_option("apis", "oti_base_url"):
        oti_base_url = conf.get("apis", "oti_base_url")
        api_base_url = "%s/db/data/ext/QueryServices/graphdb/" % (oti_base_url,)
    else:
        # fall back to older convention [TODO: remove this]
        host = conf.get("apis","oti_host")
        port = conf.get("apis","oti_port")
        api_base_url = "http://%s:%s/db/data/ext/QueryServices/graphdb/" % (host, port)

    oti = OTISearch(api_base_url)

    def GET(kind, property_name, search_term,jsoncallback=None,callback=None,_=None,**kwargs):
        """"OpenTree API methods relating to searching
Example:

    http://localhost:8000/api/search/v1/tree/ot-ottTaxonName/Carex
    http://localhost:8000/api/search/v1/node/ot-ottId/1000455

When searching for a property name ot:foo, ot-foo must be used
because web2py does not recognize URLs that contain a colon
other than specifying a port, even if URL encoded.

"""

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # colons don't play nicely with GET requests
        property_name = property_name.replace("-",":")

        valid_kinds = ["study", "tree", "node"]
        if kind in valid_kinds:
            return oti.do_search(kind, property_name, search_term)
        else:
            raise HTTP(400,json.dumps({"error":1, "description":"not a valid property name"}))

    return locals()
