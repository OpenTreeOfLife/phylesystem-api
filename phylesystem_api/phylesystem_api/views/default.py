import codecs
import datetime
import logging
import os
import sys
import traceback
import threading
from configparser import ConfigParser
from io import StringIO

import phylesystem_api.api_utils as api_utils
import requests
from peyotl import concatenate_collections, tree_is_in_collection
from peyotl.nexson_syntax import read_as_json
from peyotl.phylesystem.git_workflows import (
    GitWorkflowError,
    merge_from_master,
)
from phylesystem_api.api_utils import raise400, raise404
from pyramid.httpexceptions import (
    HTTPException,
    HTTPConflict,
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPGatewayTimeout,
)
from pyramid.response import Response
from pyramid.view import view_config
from phylesystem_api.api_utils import (
    raise_int_server_err,
    find_in_request,
    get_config_impl,
    get_docstore_from_type,
    get_update_coll_fn,
    commit_doc_and_trigger_push,
    normalize_synon_doc_types,
)

import json

_LOG = logging.getLogger("phylesystem_api")

try:
    from phylesystem_api.api_utils import call_http_json

    _LOG.debug("call_http_json imported")
except:
    call_http_json = None
    _LOG.debug("call_http_json was not imported from api_utils")

from beaker.cache import cache_region


@view_config(route_name="index", renderer="phylesystem_api:templates/home.jinja2")
def home_view(request):
    # a simple README web page for the curious
    return {"title": "phylesystem API"}


_DOC_DICT = {
    "description": "The Open Tree API",
    "documentation_url": "https://github.com/OpenTreeOfLife/phylesystem-api/tree/master/docs",
    "source_url": "https://github.com/OpenTreeOfLife/phylesystem-api",
}


@view_config(route_name="api_root", renderer="json", request_method="POST")
def base_API_view(request):
    return _DOC_DICT


def validate_api_version_number(arg):
    try:
        iarg = int(arg)
        assert 0 < iarg < 4
    except:
        raise404("Unrecognized API version v{}".format(arg))


@view_config(route_name="api_version_root", renderer="json")
@view_config(route_name="api_version_root_slash", renderer="json")
@view_config(route_name="studies_root", renderer="json")
@view_config(route_name="studies_root_slash", renderer="json")
@view_config(route_name="amendments_root", renderer="json")
@view_config(route_name="amendments_root_slash", renderer="json")
@view_config(route_name="collections_root", renderer="json")
@view_config(route_name="collections_root_slash", renderer="json")
def base_API_view(request):
    # a tiny JSON description of the API and where to find documentation
    validate_api_version_number(request.matchdict["api_version"])
    return _DOC_DICT


# Create a unique cache key with the URL and any vars (GET *and* POST) to its "query string"
# ALSO include the request method (HTTP verb) to respond to OPTIONS requests
def create_unique_cache_key(target_url, request):
    unique_key = "cached:{}:{}:{}".format(
        request.method, target_url, request.body.decode("utf-8")
    )
    # _LOG.warn(">> unique cache key: {}".format(unique_key))
    return unique_key


@view_config(route_name="pull_through_cache")
def pull_through_cache(request):
    """
    This emulates the "pull-through" RAM cache used in web2py. It should return
    a matching cached value if possible, else fetch fresh results from the
    original URL. If the original URL returns an error (non-200 status), return
    the error without caching the result.
    """
    #    _LOG = api_utils.get_logger(request, 'ot_api')
    api_utils.raise_on_CORS_preflight(request)

    # gather any request elements used to build a unique cache key
    target_url = request.matchdict.get("target_url")
    _LOG.warning(">> target_url: {}".format(target_url))

    # Some headers should not be used when adding to our RAM cache
    hop_by_hop_headers = [
        "Keep-Alive",
        "Transfer-Encoding",
        "TE",
        "Connection",
        "Trailer",
        "Upgrade",
        "Proxy-Authorization",
        "Proxy-Authenticate",
    ]

    @cache_region("short_term", create_unique_cache_key(target_url, request))
    def fetch_and_cache(url):
        # let's restrict this to URLs on this api server, to avoid shenanigans
        # import pdb; pdb.set_trace()
        root_relative_url = "/{}".format(url)
        _LOG.warning(">> root_relative_url: {}".format(root_relative_url))
        conf = api_utils.get_conf_object(request)
        base_url = conf.get("apis", "default_apis_base_url")
        fetch_url = base_url + root_relative_url
        _LOG.warning("NOT CACHED, FETCHING THIS URL: {}".format(fetch_url))
        _LOG.warning("  request.method = {}".format(request.method))
        # modify or discard "hop-by-hop" headers
        for bad_header in hop_by_hop_headers:
            request.headers.pop(bad_header, None)
        # _LOG.warning("  MODIFIED request.headers:")
        # _LOG.warning( dict(request.headers) )

        try:
            if request.method == "POST":
                # assume a typical API request with JSON payload
                # (pass this along unchanged)
                _LOG.warning("  treating as POST")
                _LOG.warning("  headers: {}".format(request.headers))
                fetched = requests.post(
                    url=fetch_url, data=request.body, headers=request.headers
                )
            elif request.method == "OPTIONS":
                _LOG.warning("  treating as OPTIONS")
                _LOG.warning("  headers: {}".format(request.headers))
                fetched = requests.options(
                    url=fetch_url, data=request.body, headers=request.headers
                )
            else:
                _LOG.warning("  treating as GET")
                fetched = requests.get(fetch_url)
            # TODO: For more flexibility, we might examine and mimic the original request (headers, etc)
            msg = "... and now we're back with fetched, which is a {}"
            msg = msg.format(type(fetched))
            _LOG.warning(msg)
            fetched.raise_for_status()
            fetched.encoding = "utf-8"  # Optional: requests infers this internally

            # modify or discard "hop-by-hop" headers
            for bad_header in hop_by_hop_headers:
                fetched.headers.pop(bad_header, None)
            try:
                fetched.json()  # missing JSON payload will raise an error
                ct = "application/json"
            except requests.exceptions.JSONDecodeError:
                ct = "text/plain"
            return Response(
                headers=fetched.headers,
                body=fetched.text,  # missing JSON payload will raise an error
                status="200 OK",
                charset="UTF-8",
                content_type=ct,
            )
        except requests.RequestException as e:
            # throw an exception (hopefully copying its status code and message) so we don't poison the cache!
            # NB - We don't want to cache this response, but we DO want to return its payload
            _LOG.warning("  request exception: {}".format(str(e)))
            raise HTTPException(body=str(e))
        except Exception as e:
            _LOG.warning("  UNKNOWN request exception: {}".format(str(e)))
            raise HTTPBadRequest(body="Unknown exception in cached call!")

    _LOG.warning("...trying to fetch-and-cache...")
    return fetch_and_cache(target_url)


@view_config(route_name="clear_cache_keys", renderer="json")
def clear_cache_keys(request):
    """
    This clears any cached items (from the "pull-through" cache above) that
    match the encoded regular expression. It should return a summary of the
    items removed, something like:

    {
      "key_pattern": "^example:*",
      "number_removed": 3,
      "matching_items": [
        "example:foo",
        "example:BAR",
        "example:BAZ123"
        ]
    }
    """
    api_utils.raise_on_CORS_preflight(request)
    key_pattern = request.matchdict.get("key_pattern")
    _LOG.warning(">> key_pattern: {}".format(key_pattern))

    """
    # TODO: decode this from URL-encoding??
    response_dict = {
      'key_pattern': key_pattern,
      'number_removed': 0,
      "matching_items": [ ]
    }

    # TODO: search and destroy any cached item with a matching key
    region_invalidate(fetch_and_cache, 'short_term', 'pull-through', key_pattern)
    # NB - Beaker has no build-in support for key-matching with regular expressions!

    return response_dict
    """
    # Fow now, use the brute-force interpr
    api_utils.clear_matching_cache_keys(key_pattern)
    return "OK"  # dumb JSON response


@view_config(route_name="render_markdown")
def render_markdown(request):
    # Convert POSTed Markdown to HTML (e.g., for previews in web UI)
    if "src" in request.params:
        src = request.params.get("src", "")
    else:
        src = request.body
    html = api_utils.markdown_to_html(src, open_links_in_new_window=True)
    return Response(body=html, content_type="text/html")


@view_config(route_name="raw_study_list", renderer="json")
def study_list(request):
    phylesystem = api_utils.get_phylesystem(request)
    studies = phylesystem.get_study_ids()
    return studies


@view_config(route_name="conventional_study_list", renderer="json")
def conventional_study_list(request):
    validate_api_version_number(request.matchdict["api_version"])
    return study_list(request)


@view_config(route_name="doc_list", renderer="json")
def doc_list(request):
    validate_api_version_number(request.matchdict["api_version"])
    docstore = get_docstore_from_type(request.matchdict["doc_type_name"], request)
    return docstore.get_doc_ids()


@view_config(route_name="docstore_push_failure", renderer="json")
def docstore_push_failure(request):
    # this should find a type-specific PUSH_FAILURE file
    api_utils.raise_on_CORS_preflight(request)
    doc_type = request.matchdict["doc_type_name"]
    fail_file = api_utils.get_failed_push_filepath(request, doc_type)
    if os.path.exists(fail_file):
        try:
            blob = read_as_json(fail_file)
        except:
            blob = {"message": "could not read push fail file"}
        blob["pushes_succeeding"] = False
    else:
        blob = {"pushes_succeeding": True}
    blob["doc_type"] = normalize_synon_doc_types(doc_type)
    return blob


@view_config(route_name="get_docstore_config", renderer="json")
def get_docstore_config(request):
    return get_config_impl(request, request.matchdict["doc_type_name"])


@view_config(route_name="phylesystem_config_no_vers", renderer="json")
@view_config(route_name="phylesystem_config_no_vers_slash", renderer="json")
def phylesystem_config_no_vers(request):
    return get_config_impl(request, "studies")


@view_config(route_name="phylesystem_config", renderer="json")
def phylesystem_config(request):
    validate_api_version_number(request.matchdict["api_version"])
    return get_config_impl(request, "studies")


@view_config(route_name="trees_in_synth", renderer="json")
def trees_in_synth(request):
    """Return an "artificial" collection that contains all trees (and
    contributors) from all of the tree collections that contribute to
    synthesis.
    """
    coll_id_list = _get_synth_input_collection_ids()
    coll_list = []
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            el = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            raise404("GET of collection {} failed".format(coll_id))
        coll_list.append(el)
    try:
        return concatenate_collections(coll_list)
    except:
        # _LOG.exception('concatenation of collections failed')
        e = sys.exc_info()[0]
        raise HTTPBadRequest(body=e)


@view_config(route_name="include_tree_in_synth", renderer="json")
def include_tree_in_synth(request):
    study_id = request.params.get("study_id", "").strip()
    tree_id = request.params.get("tree_id", "").strip()
    # check for empty/missing ids
    if (study_id == "") or (tree_id == ""):
        raise400("Expecting study_id and tree_id arguments")
    # examine this study and tree, to confirm it exists *and* to capture its name
    auth_info = api_utils.auth_and_not_read_only(request)
    owner_id = auth_info.get("login", None)
    sds = api_utils.get_phylesystem(request)
    try:
        found_study = sds.return_doc(study_id, commit_sha=None, return_WIP_map=False)[0]
    except:
        raise404("Study {} not found".format(study_id))
    found_tree = None
    try:
        tree_collections_by_id = found_study.get("nexml", {}).get("treesById", {})
        for trees_id, trees_collection in list(tree_collections_by_id.items()):
            trees_by_id = trees_collection.get("treeById", {})
            if tree_id in list(trees_by_id.keys()):
                found_tree = trees_by_id.get(tree_id)
    except Exception as x:
        raise_int_server_err(str(x))
    if found_tree is None:
        msg = "Specified tree '{t}' in study '{s}' not found! Save this study and try again?"
        msg = msg.format(s=study_id, t=tree_id)
        raise404(msg)
    try:
        found_tree_name = found_tree.get("@label") or tree_id
    except Exception as x:
        raise_int_server_err(str(x))
    # Look ahead to see if it's already in an included collection; if so, skip
    # adding it again.
    coll_id_list = _get_synth_input_collection_ids()
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            coll = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            raise404("GET of collection {} failed".format(coll_id))
        if tree_is_in_collection(coll, study_id, tree_id):
            return trees_in_synth(request)

    # find the default synth-input collection and parse its JSON
    default_collection_id = coll_id_list[-1]
    # N.B. For now, we assume that the last listed synth-input collection
    # is the sensible default, so we already have it in coll
    decision_list = coll.get("decisions", [])
    # construct and add a sensible decision entry for this tree
    decision_list.append(
        {
            "name": found_tree_name or "",
            "treeID": tree_id,
            "studyID": study_id,
            "SHA": "",
            "decision": "INCLUDED",
            "comments": "Added via API (include_tree_in_synth) from {p}".format(
                p=found_study.get("nexml")["^ot:studyPublicationReference"]
            ),
        }
    )
    # update (or add) the decision list for this collection
    coll["decisions"] = decision_list
    commit_fn = get_update_coll_fn(cds, owner_id)
    commit_doc_and_trigger_push(
        request,
        commit_fn=commit_fn,
        doc=coll,
        doc_id=default_collection_id,
        doc_type_name="collection",
        auth_info=auth_info,
        parent_sha=request.params.get("starting_commit_SHA", None),
        merged_sha=None,  # TODO: request.params.get('???', None)
        commit_msg="Updated via API (include_tree_from_synth)",
    )
    # fetch and return the updated list of synth-input trees
    return trees_in_synth(request)


@view_config(route_name="exclude_tree_from_synth", renderer="json")
def exclude_tree_from_synth(request):
    study_id = request.params.get("study_id", "").strip()
    tree_id = request.params.get("tree_id", "").strip()
    # check for empty/missing ids
    if (study_id == "") or (tree_id == ""):
        raise400("Expecting study_id and tree_id arguments")
    # find this tree in ANY synth-input collection; if found, remove it and update the collection
    coll_id_list = _get_synth_input_collection_ids()
    cds = api_utils.get_tree_collection_store(request)
    auth_info = api_utils.auth_and_not_read_only(request)
    owner_id = auth_info.get("login", None)
    commit_fn = get_update_coll_fn(cds, owner_id)
    for coll_id in coll_id_list:
        try:
            coll = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            raise404("GET of collection {} failed".format(coll_id))
        if tree_is_in_collection(coll, study_id, tree_id):
            # remove it and update the collection
            decision_list = coll.get("decisions", [])
            coll["decisions"] = [
                d
                for d in decision_list
                if not ((d["studyID"] == study_id) and (d["treeID"] == tree_id))
            ]
            # N.B. that _both_ ids (for study and tree) must match to remove a decision!
            # update the collection (forces re-indexing)
            parent_sha = request.params.get("starting_commit_SHA", None)
            merged_sha = None  # TODO: request.params.get('???', None)
            commit_doc_and_trigger_push(
                request,
                commit_fn=commit_fn,
                doc=coll,
                doc_id=coll_id,
                doc_type_name="collection",
                auth_info=auth_info,
                parent_sha=parent_sha,
                merged_sha=merged_sha,
                commit_msg="Updated via API (exclude_tree_from_synth)",
            )
    # fetch and return the updated list of synth-input trees
    return trees_in_synth(request)


def _get_synth_input_collection_ids():
    """Return a list of all collection ids for the collections that contribute
    to synthesis (based on the current propinquity configuration).
    """
    # URL could be configurable, but I'm not sure we've ever changed this...
    url_of_synth_config = "https://raw.githubusercontent.com/mtholder/propinquity/master/config.opentree.synth"
    try:
        resp = requests.get(url_of_synth_config)
        conf_fo = StringIO(resp.content.decode("utf-8"))
    except:
        raise HTTPGatewayTimeout(
            body="Could not fetch synthesis list from {}".format(url_of_synth_config)
        )
    cfg = ConfigParser()
    try:
        cfg.read_file(conf_fo)
    except:
        raise HTTPInternalServerError(
            body="Could not parse file from {}".format(url_of_synth_config)
        )
    try:
        coll_id_list = cfg.get("synthesis", "collections").split()
    except:
        raise HTTPInternalServerError(
            body="Could not find a collection list in file from {}".format(
                url_of_synth_config
            )
        )
    return coll_id_list


@view_config(route_name="merge_docstore_changes", renderer="json")
def merge_docstore_changes(request):
    """Undocumented method to merge changes FROM master, i.e.
    any work merged by others since these edits began.

        curl -X PUT https://devapi.opentreeoflife.org/v3/merge_docstore_changes/ot_9999/152316261261342&auth_token=$GITHUB_OAUTH_TOKEN

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
    resource_id = request.matchdict["doc_id"]
    starting_commit_SHA = request.matchdict["starting_commit_SHA"]
    auth_info = api_utils.auth_and_not_read_only(request)
    phylesystem = api_utils.get_phylesystem(request)
    gd = phylesystem.create_git_action(resource_id)
    try:
        return merge_from_master(gd, resource_id, auth_info, starting_commit_SHA)
    except GitWorkflowError as err:
        raise400(err.msg)
    except:
        m = traceback.format_exc()
        raise_conflict("Could not merge! Details: {}".format(m))


@view_config(route_name="push_docstore_changes", renderer="json")
@view_config(route_name="push_docstore_changes_bare", renderer="json")
def push_docstore_changes(request):
    """OpenTree API method to update branch on master

    curl -X POST https://devapi.opentreeoflife.org/v3/push_docstore_changes/nexson/ot_999
    """
    _LOG.debug("push_docstore_changes")
    doc_type = request.matchdict["doc_type"].lower()
    resource_id = request.matchdict.get("doc_id")
    if resource_id is None:
        resource_id = find_in_request(request, "doc_id", None)
    api_utils.auth_and_not_read_only(request)
    fail_file = api_utils.get_failed_push_filepath(request, doc_type=doc_type)
    # TODO
    docstore = get_docstore_from_type(doc_type, request)
    doc_key_dict = {
        "nexson": "study",
        "study": "study",
        "studies": "study",
        "collection": "collection",
        "collections": "collection",
        "amendment": "amendment",
        "amendments": "amendment",
    }
    doc_key = doc_key_dict[doc_type]
    try:
        docstore.push_doc_to_remote("GitHubRemote", resource_id)
    except:
        m = traceback.format_exc()
        msg = "Push of {k} {s} failed. Details: {m}".format(
            k=doc_key, s=resource_id, m=m
        )
        _LOG.warning(msg)
        if os.path.exists(fail_file):
            msg = '"{f}" already exists. This event not logged'.format(f=fail_file)
            _LOG.warning(msg)
        else:
            timestamp = datetime.datetime.utcnow().isoformat()
            try:
                ga = docstore.create_git_action(resource_id)
            except:
                msg = 'Could not create an adaptor for git actions on ID "{}".  If you are confident that this is a valid ID, please report this as a bug.'
                raise400(msg.format(resource_id))
            master_sha = ga.get_master_sha()
            obj = {
                "date": timestamp,
                doc_key: resource_id,
                "commit": master_sha,
                "stacktrace": m,
            }
            api_utils.atomic_write_json_if_not_found(obj, fail_file, request)
            _LOG.warning('push failure file "{f}" created.'.format(f=fail_file))
        raise_conflict("Could not push! Details: {m}".format(m=m))

    if os.path.exists(fail_file):
        remove_fail_file(fail_file)
    return {"error": 0, "description": "Push succeeded"}


def raise_conflict(msg):
    bd = {
        "error": 1,
        "description": msg,
    }
    raise HTTPConflict(body=json.dumps(bd))


fail_file_lock = threading.Lock()


def remove_fail_file(fail_file):
    with fail_file_lock:

        # log any old fail_file, and remove it because the pushes are working
        if not os.path.exists(fail_file):
            return

        with codecs.open(fail_file, "rU", encoding="utf-8") as inpf:
            prev_fail = json.load(inpf)
        os.unlink(fail_file)
        fail_log_file = codecs.open(fail_file + ".log", mode="a", encoding="utf-8")
        json.dump(prev_fail, fail_log_file, indent=2, encoding="utf-8")
        fail_log_file.close()
