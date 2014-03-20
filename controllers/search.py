import os
import time
import json
import requests
from oti_search import OTISearch
from ConfigParser import SafeConfigParser
from gluon.tools import fetch
from api_utils import read_config

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
        api_base_url = "%s/ext/QueryServices/graphdb/" % (oti_base_url,)
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

def nudgeIndexOnUpdates():
    # just diagnostic stuff for now
    from pprint import pprint
    # nothing interesting in these...
    # pprint(request)
    # pprint(request.args)
    # pprint(request.body.read())
    payload = request.vars
    pprint(payload)

    # EXAMPLE of a working curl call to nudge index:
    # curl -X "POST" -d '{"urls": ["https://raw.github.com/OpenTreeOfLife/phylesystem/master/study/10/10.json", "https://raw.github.com/OpenTreeOfLife/phylesystem/master/study/9/9.json"]}' -H "Content-type: application/json" http://ec2-54-203-194-13.us-west-2.compute.amazonaws.com/oti/ext/IndexServices/graphdb/indexNexsons

    # curl http://ec2-54-203-194-13.us-west-2.compute.amazonaws.com/oti/ext/IndexServices/graphdb/indexNexsons -X POST -d '{"urls": ["https://raw.github.com/OpenTreeOfLife/phylesystem/master/study/9/9.json", "https://raw.github.com/OpenTreeOfLife/phylesystem/master/study/10/10.json"] }' -H "Content-type: application/json"

    repo_path, repo_remote, git_ssh, pkey, repo_nexml2json = read_config(request)
    # EXAMPLE VALUES: (
    #   '/Users/jima/projects/nescent/opentree/phylesystem', 
    #   'originssh',
    #   '/Users/jima/projects/nescent/opentree/api.opentreeoflife.org/bin/git.sh',
    #   '/Users/jima/.ssh/opentree/opentreeapi-gh.pem',
    #   '0.0.0'
    # )
    #
    # Hm, turns out none of this is useful! Here's what we need to know:
    #   repo's URL or name (munge this to grab raw NexSON)
    #   OTI_base_URL -- MAKE SURE we're pushing to the right OTI service(s)!
    # Both of these should probably "flow through" private/config from the server-config file.
    REPO_URL = "https://github.com/OpenTreeOfLife/phylesystem"  # TODO: fetch from private/config
    OTI_BASE_URL='http://ec2-54-203-194-13.us-west-2.compute.amazonaws.com/oti'  # TODO: fetch from private/config

    try:
        if payload['repository']['url'] != REPO_URL:
            raise HTTP(400,json.dumps({"error":1, "description":"wrong repo for this API instance"}))

        # how we nudge the index depends on which studies are new, changed, or deleted
        added_study_ids = [ ]
        modified_study_ids = [ ]
        removed_study_ids = [ ]
        # TODO: Should any of these lists override another? maybe use commit timestamps to "trump" based on later operations?
        for commit in payload['commits']:
            _harvest_study_ids_from_paths( commit['added'], added_study_ids )
            _harvest_study_ids_from_paths( commit['modified'], modified_study_ids )
            _harvest_study_ids_from_paths( commit['removed'], removed_study_ids )

        # "flatten" each list to remove duplicates
        added_study_ids = list(set(added_study_ids))
        modified_study_ids = list(set(modified_study_ids))
        removed_study_ids = list(set(removed_study_ids))

    except:
        # TODO: raise HTTP(400,json.dumps({"error":1, "description":"malformed GitHub payload"}))
        added_study_ids = ['9']
        modified_study_ids = ['9','10']
        removed_study_ids = ['10']

    nexson_url_template = REPO_URL.replace("github.com", "raw.github.com") + "/master/study/%s/%s.json"

    # for now, let's just add/update new and modified studies using indexNexsons
    study_ids = added_study_ids + modified_study_ids
    # NOTE that passing deleted_study_ids (any non-existent file paths) will fail on oti, with a FileNotFoundException!
    study_ids = list(set(study_ids))  # remove any duplicates

    nudge_url = "%s/ext/IndexServices/graphdb/indexNexsons" % (OTI_BASE_URL,)
    pprint("nudge_url:")
    pprint(nudge_url)

    nexson_urls = [ (nexson_url_template % (study_id, study_id)) for study_id in study_ids ]
    pprint("nexson_urls:")
    pprint(nexson_urls)

    nudge_index_response = fetch(
        nudge_url,
        data={
            "urls": nexson_urls
        },
        headers={
            "Content-type": "application/json"
        }
    )
    pprint(nudge_index_response)
    # TODO: check returned IDs against our original study_ids list... what if something fails?
    
    ##### TODO: Call removed studies here, once we have a solid method for nudging for removal!


def _harvest_study_ids_from_paths( path_list, target_array ):
    for path in path_list:
        path_parts = path.split('/')
        if path_parts[0] == "study":
            study_id = path_parts[1]
            target_array.append(study_id)


