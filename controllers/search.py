import os
import time
import json
import requests
from oti_search import OTISearch
from ConfigParser import SafeConfigParser
import urllib2
import sys
import traceback
import api_utils

# logger for indexing failures
_LOG = api_utils.get_logger(request, 'ot_api.default.v1')

def check_not_read_only():
    if api_utils.READ_ONLY_MODE:
        raise HTTP(403, json.dumps({"error": 1, "description": "phylesystem-api running in read-only mode"}))
    return True

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    oti_base_url = api_utils.get_oti_base_url(request)  # WAS conf.get("apis", "oti_base_url")
    oti = OTISearch(oti_base_url)

    def GET(kind, property_name, search_term,jsoncallback=None,callback=None,_=None,**kwargs):
        """"OpenTree API methods relating to searching
Example:

    http://localhost:8000/api/search/v1/tree/ot-ottTaxonName/Carex
    http://localhost:8000/api/search/v1/node/ot-ottId/1000455

When searching for a property name ot:foo, ot-foo must be used
because web2py does not recognize URLs that contain a colon
other than specifying a port, even if URL encoded.

"""
        opentree_docstore_url = _read_from_local_config(request, "apis", "opentree_docstore_url")

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

def nudgeStudyIndexOnUpdates():
    """"Support method to update oti index in response to GitHub webhooks

This examines the JSON payload of a GitHub webhook to see which studies have
been added, modified, or removed. Then it calls oti's index service to
(re)index the NexSON for those studies, or to delete a study's information if
it was deleted from the docstore.

Finally, we clear the cached study list (response to find_studies with no args).

N.B. This depends on a GitHub webhook on the chosen docstore.
"""
    if not check_not_read_only():
        raise HTTP(500, "should raise from check_not_read_only")
    opentree_docstore_url = _read_from_local_config(request, "apis", "opentree_docstore_url")

    payload = request.vars

    # get list of study ids to be added / modified / removed
    try:
        # how we nudge the index depends on which studies are new, changed, or deleted
        added_study_ids = [ ]
        modified_study_ids = [ ]
        removed_study_ids = [ ]
        # TODO: Should any of these lists override another? maybe use commit timestamps to "trump" based on later operations?
        for commit in payload['commits']:
            _harvest_study_ids_from_paths( commit['added'], added_study_ids )
            _harvest_study_ids_from_paths( commit['modified'], modified_study_ids )
            _harvest_study_ids_from_paths( commit['removed'], removed_study_ids )

        # add and update treated the same, so merge
        # also "flatten" each list to remove duplicates
        add_or_update_ids = added_study_ids + modified_study_ids
        add_or_update_ids = list(set(add_or_update_ids))
        remove_ids = list(set(removed_study_ids))

    except:
        raise HTTP(400,json.dumps({"error":1, "description":"malformed GitHub payload"}))

    if payload['repository']['url'] != opentree_docstore_url:
        raise HTTP(400,json.dumps({"error":1, "description":"wrong repo for this API instance"}))

    # get index URLs from config
    otindex_base_url = api_utils.get_otindex_base_url(request)

    # nexson_url_template only needed for oti method, not otindex
    nexson_url_template = URL(r=request,
                              c="default",
                              f="v1",
                              args=["study", "%s"],
                              vars={'output_nexml2json': '0.0.0'},
                              scheme=True,
                              host=True,
                              url_encode=False)

    # call both the oti and otindex methods
    msg = ''
    if len(add_or_update_ids) > 0:
        # oti call
        _otindex_add_update_studies( add_or_update_ids, otindex_base_url )

    if len(remove_ids) > 0:
        # oti call
        # otindex call
        _otindex_remove_studies( remove_ids, otindex_base_url )

    # TODO: check returned IDs against our original list... what if something failed?

    # Clear any cached study lists (both verbose and non-verbose)
    api_utils.clear_matching_cache_keys(".*find_studies.*")

    github_webhook_url = "%s/settings/hooks" % opentree_docstore_url
    full_msg = """This URL should be called by a webhook set in the docstore repo:
    <br /><br />
    <a href="%s">%s</a><br />
    <pre>%s</pre>
    """ % (github_webhook_url, github_webhook_url, msg,)
    if msg == '':
        return full_msg
    else:
        raise HTTP(500, full_msg)

def _otindex_add_update_studies(add_or_update_ids, otindex_base_url):
    if not check_not_read_only():
        raise HTTP(500, "should raise from check_not_read_only")
    nudge_url = "{o}/v3/studies/add_update".format(o=otindex_base_url)
    # can call otindex with list of either github urls or study ids
    payload = { "studies" : add_or_update_ids }
    headers={"Content-Type": "application/json"}
    resp = requests.post(nudge_url,
                        headers=headers,
                        data=json.dumps(payload),
                        allow_redirects=True)
    msg = ''
    try:
        response = resp.json()
        if len(response['failed_studies']) > 0:
            f = response['failed_studies']
            _LOG.warn("Could not update following studies: {s}".format(s=f))
    except Exception as e:
        msg = json.dumps({"description": "Unexpected error calling otindex: {}".format(e.message)})
    return msg


def _otindex_remove_studies(remove_ids, otindex_base_url):
    if not check_not_read_only():
        raise HTTP(500, "should raise from check_not_read_only")
    nudge_url = "{o}/v3/studies/remove".format(o=otindex_base_url)
    # can call otindex with list of either github urls or study ids
    payload = { "studies" : remove_ids }
    headers={"Content-Type": "application/json"}
    resp = requests.post(nudge_url,
                        headers=headers,
                        data=json.dumps(payload),
                        allow_redirects=True)
    msg = ''
    try:
        response = resp.json()
        if len(response['failed_studies']) > 0:
            f = response['failed_studies']
            _LOG.warn("Could not remove the following studies {s}".format(s=f))
    except Exception as e:
        msg = json.dumps({"description": "Unexpected error calling otindex: {}".format(e.message)})
    return msg


def nudgeTaxonIndexOnUpdates():
    """"Support method to update taxon index (taxomachine) in response to GitHub webhooks

This examines the JSON payload of a GitHub webhook to see which taxa have
been added, modified, or removed. Then it calls the appropriate index service to
(re)index these taxa, or to delete a taxon's information if it was deleted in
an amendment.

TODO: Clear any cached taxon list.

N.B. This depends on a GitHub webhook on the taxonomic-amendments docstore!
"""
    if not check_not_read_only():
        raise HTTP(500, "should raise from check_not_read_only")
    amendments_repo_url = _read_from_local_config(request, "apis", "amendments_repo_url")
    payload = request.vars
    if payload['repository']['url'] != amendments_repo_url:
        raise HTTP(400,json.dumps({"error":1, "description":"wrong repo for this API instance"}))

    msg = ''
    try:
        # how we nudge the index depends on which taxa are new, changed, or deleted
        added_ott_ids = [ ]
        modified_ott_ids = [ ]
        removed_ott_ids = [ ]
        # TODO: Should any of these lists override another? maybe use commit timestamps to "trump" based on later operations?
        for commit in payload['commits']:
            _harvest_ott_ids_from_paths( commit['added'], added_ott_ids )
            _harvest_ott_ids_from_paths( commit['modified'], modified_ott_ids )
            _harvest_ott_ids_from_paths( commit['removed'], removed_ott_ids )
        # "flatten" each list to remove duplicates
        added_ott_ids = list(set(added_ott_ids))
        modified_ott_ids = list(set(modified_ott_ids))
        removed_ott_ids = list(set(removed_ott_ids))
    except:
        raise HTTP(400,json.dumps({"error":1, "description":"malformed GitHub payload"}))

    # build a working URL, gather amendment body, and nudge the index!
    amendments_api_base_url = api_utils.get_amendments_api_base_url(request)

    if len(added_ott_ids) > 0:
        nudge_url = "{b}v3/taxonomy/process_additions".format(b=amendments_api_base_url)

        for ott_id in added_ott_ids:
            # fetch the JSON body of each new amendment and submit it for indexing
            fetch_url = "{b}v3/amendment/{i}".format(b=amendments_api_base_url, i=ott_id)
            fetch_response = None
            req = urllib2.Request(
                url=fetch_url
            )
            try:
                fetch_response = urllib2.urlopen(req).read()
                # strip away metadata (version history, etc.)
                amendment_blob = json.loads( fetch_response ).get('data')
            except Exception, e:
                # bail and report the error in webhook response
                exc_type, exc_value, exc_traceback = sys.exc_info()
                msg += """fetch of amendment failed!'
    fetch_url: %s
    fetch_response: %s
    ott_id: %s
    %s""" % (fetch_url, fetch_response, ott_id, traceback.format_exception(exc_type, exc_value, exc_traceback),)
                break

            # Extra weirdness required here, as neo4j needs an encoded *string*
            # of the amendment JSON, within a second JSON wrapper :-/
            POST_blob = {"addition_document": json.dumps(amendment_blob) }
            POST_string = json.dumps(POST_blob)
            nudge_response = None
            req = urllib2.Request(
                url=nudge_url,
                data=POST_string,
                headers={"Content-Type": "application/json"}
            )
            try:
                # N.B. we don't expect anything interesting here, probably just an empty dict
                nudge_response = urllib2.urlopen(req).read()
            except Exception, e:
                # report the error in webhook response
                exc_type, exc_value, exc_traceback = sys.exc_info()
                msg += """index amendments failed!'
    nudge_url: %s
    POST_data: %s
    fetch_response: %s
    nudge_response: %s
    added_ott_ids: %s
    %s""" % (nudge_url, POST_data, fetch_response, nudge_response, added_ott_ids, traceback.format_exception(exc_type, exc_value, exc_traceback),)

    # LATER: add handlers for modified and removed taxa?
    if len(modified_ott_ids) > 0:
        raise HTTP(400,json.dumps({
            "error":1,
            "description":"We don't currently re-index modified taxa!"}))
    if len(removed_ott_ids) > 0:
        raise HTTP(400,json.dumps({
            "error":1,
            "description":"We don't currently re-index removed taxa!"}))

    # N.B. If we had any cached amendment results, we'd clear them now
    #api_utils.clear_matching_cache_keys(...)

    github_webhook_url = "%s/settings/hooks" % amendments_repo_url
    full_msg = """This URL should be called by a webhook set in the amendments repo:
<br /><br />
<a href="%s">%s</a><br />
<pre>%s</pre>
""" % (github_webhook_url, github_webhook_url, msg,)
    if msg == '':
        return full_msg
    else:
        raise HTTP(500, full_msg)

def _read_from_local_config(request, section_name, key_name):
    app_name = request.application
    conf = SafeConfigParser(allow_no_value=True)
    if os.path.isfile("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,)):
        conf.read("%s/applications/%s/private/localconfig" % (os.path.abspath('.'), app_name,))
    else:
        conf.read("%s/applications/%s/private/config" % (os.path.abspath('.'), app_name,))
    return conf.get(section_name, key_name)

def _harvest_study_ids_from_paths( path_list, target_array ):
    for path in path_list:
        path_parts = path.split('/')
        if path_parts[0] == "study":
            # skip any intermediate directories in docstore repo
            study_id = path_parts[ len(path_parts) - 2 ]
            target_array.append(study_id)

def _harvest_ott_ids_from_paths( path_list, target_array ):
    for path in path_list:
        path_parts = path.split('/')
        # ignore changes to counter file, other directories, etc.
        if path_parts[0] == "amendments":
            # skip intermediate directories in docstore repo
            amendment_file_name = path_parts.pop()
            ott_id = amendment_file_name[:-5]
            target_array.append(ott_id)
