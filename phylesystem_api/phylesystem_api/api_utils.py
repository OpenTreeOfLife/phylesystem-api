import json
import logging
import os
import tempfile
import threading
from configparser import ConfigParser
from datetime import datetime

import requests
from beaker.cache import cache_managers
from github import Github, BadCredentialsException
from peyotl.amendments import TaxonomicAmendmentStore
from peyotl.api import OTI
from peyotl.collections_store import TreeCollectionStore
from peyotl.nexson_syntax import write_as_json
from peyotl.phylesystem import Phylesystem
from peyotl.utility import read_config as read_peyotl_config
from peyotl.phylesystem.git_workflows import GitWorkflowError
from pyramid.httpexceptions import (
    HTTPOk,
    HTTPBadRequest,
    HTTPForbidden,
    HTTPInternalServerError,
    HTTPNotFound,
)

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.request import Request

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree


_LOG = logging.getLogger("phylesystem_api")
_LOG.debug("start api_utils")


# this will be updated by config below; start safe by default
READ_ONLY_MODE = True


def bool_arg(v):
    if isinstance(v, str):
        u = v.upper()
        if u in ["TRUE", "YES"]:
            return True
        if u in ["FALSE", "NO"]:
            return False
    return v


def raise_int_server_err(msg):
    body = {
        "error": 1,
        "description": msg,
    }
    raise HTTPInternalServerError(body=json.dumps(body))


def raise400(msg):
    raise HTTPBadRequest(body=json.dumps({"error": 1, "description": msg}))


def raise404(msg):
    raise HTTPNotFound(body=json.dumps({"error": 1, "description": msg}))


def get_owner_id(request, auth_info):
    owner_id = auth_info.get("login")
    if owner_id is None:
        raise400("no GitHub userid obtained from auth token")
    return owner_id


def get_commit_message(request):
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            return None
        return commit_msg
    except:
        return None


def get_parent_sha(request):
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    if parent_sha is None:
        msg = 'Expecting a "starting_commit_SHA" argument with the SHA of the parent'
        raise400(msg)
    return parent_sha


def commit_doc_and_trigger_push(
    request,
    commit_fn,
    doc,
    doc_id,
    doc_type_name,
    auth_info,
    parent_sha=None,
    merged_sha=None,
    commit_msg=None,
):
    """Tries to commit doc, raises HTTP errors as needed. Triggers push thread.

    `request` the Request obj,
    `commit_fn` a function that takes (doc, doc_id, auth_inf, commit_msg)
       and return the new_doc_id and a commit_return object.
    `doc` the document as an object
    `doc_id` or None if the docstore mints the ID.
    `doc_type_name` "amendment", "nexson", or "collection"
    `auth_info` dict
    `commit_msg` string
    """
    try:
        r = commit_fn(
            doc,
            doc_id,
            auth_info,
            parent_sha=parent_sha,
            merged_sha=merged_sha,
            commit_msg=commit_msg,
        )
        new_doc_id, commit_return = r
    except GitWorkflowError as err:
        raise400(err.msg)
    except Exception as x:
        raise400(str(x))
    if commit_return["error"] != 0:
        _LOG.debug("commit of {} failed with error code".format(doc_type_name))
        raise HTTPBadRequest(body=json.dumps(commit_return))
    # check for 'merge needed'
    mn = commit_return.get("merge_needed")
    if (mn is not None) and (not mn):
        _LOG.debug("commit of {} deferred_push_to_gh_call".format(doc_type_name))
        deferred_push_to_gh_call(
            request,
            new_doc_id,
            doc_type=doc_type_name,
            auth_token=auth_info["auth_token"],
        )
    return commit_return


def fetch_doc(
    request,
    doc_id,
    doc_store,
    doc_type_name,
    doc_id_validator=None,
    add_version_history=True,
):
    if (doc_id_validator is not None) and (not doc_id_validator(doc_id)):
        msg = "invalid {n} ID ({i}) provided".format(n=doc_type_name, i=doc_id)
        raise400(msg)
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    try:
        r = doc_store.return_doc(doc_id, commit_sha=parent_sha, return_WIP_map=True)
    except:
        raise404("{n} '{i}' GET failure".format(n=doc_type_name, i=doc_id))
    document, head_sha, wip_map = r
    if not document:
        raise404("{n} '{i}' has no JSON data!".format(n=doc_type_name, i=doc_id))
    version_history = None
    if add_version_history:
        try:
            version_history = doc_store.get_version_history_for_doc_id(doc_id)
        except:
            m = "fetching version history failed"
            _LOG.exception(m)
            raise_int_server_err(m)
    try:
        external_url = doc_store.get_public_url(doc_id)
    except:
        external_url = "NOT FOUND"
    result = {
        "sha": head_sha,
        "data": document,
        "branch2sha": wip_map,
        "external_url": external_url,
    }
    if version_history:
        result["versionHistory"] = version_history
    return result


def get_private_dir(request):
    _LOG.debug("WHY PRIVATE DIR")
    return "~/private/"


def atomic_write_json_if_not_found(obj, dest, request):
    if os.path.exists(dest):
        return False
    pdir = get_private_dir(request)
    handle, tmpfn = tempfile.mkstemp(suffix=".json", dir=pdir, text=True)
    # mkstemp opens the file and returns a file descriptor,
    #   but we are using write_as_json to open with the right encoding
    os.close(handle)
    write_as_json(obj, tmpfn, indent=2, sort_keys=True)
    if os.path.exists(dest):
        return False
    os.rename(tmpfn, dest)
    return True


def compose_push_to_github_url(request, resource_id, doc_type):
    if resource_id is None:
        return request.route_url(
            "push_docstore_changes_bare", api_version="v3", doc_type=doc_type
        )
    return request.route_url(
        "push_docstore_changes", api_version="v3", doc_type=doc_type, doc_id=resource_id
    )


# this allows us to raise HTTP(...)
_PHYLESYSTEM = None


def get_phylesystem(request, conf_obj=None):
    global READ_ONLY_MODE
    global _PHYLESYSTEM
    # _LOG.debug('@@@ checking for _PHYLESYSTEM singleton...READ_ONLY_MODE? {}'.format(READ_ONLY_MODE))
    if _PHYLESYSTEM is not None:
        _LOG.debug("@@@ FOUND it, returning now")
        return _PHYLESYSTEM
    # _LOG.debug('@@@ NOT FOUND, creating now')
    from phylesystem_api.gitdata import GitData

    if conf_obj is None:
        conf_obj = get_conf_object(request)
    pc = read_phylesystem_config(request, conf_obj=conf_obj)
    READ_ONLY_MODE = pc.read_only
    peyotl_config, cfg_filename = read_peyotl_config()
    if "phylesystem" not in peyotl_config.sections():
        peyotl_config.add_section("phylesystem")
    peyotl_config.set(
        "phylesystem", "max_file_size", pc.max_filesize
    )  # overrides peyotl config with max phylesytem-api filesize
    push_mirror = os.path.join(pc.repo_parent, "mirror")
    pmi = {
        "parent_dir": push_mirror,
        "remote_map": {
            "GitHubRemote": pc.git_hub_remote,
        },
    }
    mirror_info = {"push": pmi}
    a = {}
    try:
        new_study_prefix = conf_obj.get("apis", "new_study_prefix")
        a["new_study_prefix"] = new_study_prefix
    except:
        pass
    _PHYLESYSTEM = Phylesystem(
        repos_par=pc.repo_parent,
        git_ssh=pc.git_ssh,
        pkey=pc.pkey,
        git_action_class=GitData,
        mirror_info=mirror_info,
        **a
    )
    # _LOG.debug('[[[[[[ repo_nexml2json = {}'.format(_PHYLESYSTEM.repo_nexml2json))
    if READ_ONLY_MODE:
        _LOG.warning("phylesytem-api running in READ_ONLY_MODE")
    else:
        _LOG.warning("phylesytem-api NOT running in READ_ONLY_MODE")
    return _PHYLESYSTEM


_TREE_COLLECTION_STORE = None


def get_tree_collection_store(request):
    global _TREE_COLLECTION_STORE
    if _TREE_COLLECTION_STORE is not None:
        return _TREE_COLLECTION_STORE
    #    _LOG = get_logger(request, 'ot_api')
    from phylesystem_api.gitdata import GitData

    (
        repo_parent,
        repo_remote,
        git_ssh,
        pkey,
        git_hub_remote,
        max_filesize,
    ) = read_collections_config(request)
    push_mirror = os.path.join(repo_parent, "mirror")
    pmi = {
        "parent_dir": push_mirror,
        "remote_map": {
            "GitHubRemote": git_hub_remote,
        },
    }
    mirror_info = {"push": pmi}
    a = {}
    try:
        # any keyword args to pass along from config?
        # new_study_prefix = conf.get('apis', 'new_study_prefix')
        # a['new_study_prefix'] = new_study_prefix
        pass
    except:
        pass
    _TREE_COLLECTION_STORE = TreeCollectionStore(
        repos_par=repo_parent,
        git_ssh=git_ssh,
        pkey=pkey,
        git_action_class=GitData,  # TODO?
        mirror_info=mirror_info,
        **a
    )
    # _LOG.debug('assumed_doc_version = {}'.format(_TREE_COLLECTION_STORE.assumed_doc_version))
    return _TREE_COLLECTION_STORE


_TAXONOMIC_AMENDMENT_STORE = None


def get_taxonomic_amendment_store(request):
    global _TAXONOMIC_AMENDMENT_STORE
    if _TAXONOMIC_AMENDMENT_STORE is not None:
        return _TAXONOMIC_AMENDMENT_STORE
    #    _LOG = get_logger(request, 'ot_api')
    from phylesystem_api.gitdata import GitData

    (
        repo_parent,
        repo_remote,
        git_ssh,
        pkey,
        git_hub_remote,
        max_filesize,
    ) = read_amendments_config(request)
    push_mirror = os.path.join(repo_parent, "mirror")
    pmi = {
        "parent_dir": push_mirror,
        "remote_map": {
            "GitHubRemote": git_hub_remote,
        },
    }
    mirror_info = {"push": pmi}
    a = {}
    try:
        # any keyword args to pass along from config?
        # new_study_prefix = conf.get('apis', 'new_study_prefix')
        # a['new_study_prefix'] = new_study_prefix
        pass
    except:
        pass
    _TAXONOMIC_AMENDMENT_STORE = TaxonomicAmendmentStore(
        repos_par=repo_parent,
        git_ssh=git_ssh,
        pkey=pkey,
        git_action_class=GitData,  # TODO?
        mirror_info=mirror_info,
        **a
    )
    _LOG.debug(
        "assumed_doc_version = {}".format(
            _TAXONOMIC_AMENDMENT_STORE.assumed_doc_version
        )
    )
    return _TAXONOMIC_AMENDMENT_STORE


def get_failed_push_filepath(request, doc_type=None):
    filenames_by_content_type = {
        "nexson": "PUSH_FAILURE_nexson.json",
        "collection": "PUSH_FAILURE_collection.json",
        "amendment": "PUSH_FAILURE_amendment.json",
        "favorites": "PUSH_FAILURE_favorites.json",
    }
    content_type = doc_type or request.matchdict.get("doc_type", "nexson")
    failure_filename = filenames_by_content_type[content_type]
    return os.path.join(get_private_dir(request), failure_filename)


def get_conf_object(request=None, localconfig_filename=None):
    # There's apparently no easy way to retrieve the fully parsed
    # configuration from within the app. But we can access the variables
    # from the [app:main] setion, so we'll retrieve the full path to
    # our chosen INI file from there.
    if localconfig_filename is None:
        assert request is not None
        localconfig_filename = request.registry.settings["config_file_path"]
    _LOG.debug(
        'get_conf_object(localconfig_filename="{}")'.format(localconfig_filename)
    )
    if not os.path.isfile(localconfig_filename):
        raise RuntimeError(
            "localconfig_filename={} does not exist".format(localconfig_filename)
        )
    conf = ConfigParser(allow_no_value=True)
    conf.read(localconfig_filename)
    return conf


_phylesystem_config = None
_phylesystem_config_lock = threading.Lock()


def read_phylesystem_config(request, conf_obj=None):
    """Load settings for managing the main Nexson docstore"""
    global _phylesystem_config
    if _phylesystem_config is None:
        if conf_obj is None:
            conf_obj = get_conf_object(request)
        with _phylesystem_config_lock:
            if _phylesystem_config is None:
                _phylesystem_config = PhylesystemConfig(conf_obj)
    return _phylesystem_config


class PhylesystemConfig(object):
    def __init__(self, conf):
        self._repo_parent = conf.get("apis", "repo_parent")
        self._repo_remote = conf.get("apis", "repo_remote")
        try:
            self._git_ssh = conf.get("apis", "git_ssh")
        except:
            self._git_ssh = "ssh"
        try:
            self._pkey = conf.get("apis", "pkey")
        except:
            self._pkey = None
        try:
            self._git_hub_remote = conf.get("apis", "git_hub_remote")
        except:
            self._git_hub_remote = "git@github.com:OpenTreeOfLife"
        try:
            self._max_filesize = conf.get("filesize", "peyotl_max_file_size")
        except:
            self._max_filesize = "20000000"
        try:
            self._max_num_trees = conf.get("filesize", "validation_max_num_trees")
        except:
            self._max_num_trees = 65
        try:
            self._max_num_trees = int(self._max_num_trees)
        except ValueError:
            raise400("max number of trees per study in config is not an integer")
        try:
            self._read_only = conf.get("apis", "read_only") == "true"
        except:
            self._read_only = False

    @property
    def repo_parent(self):
        return self._repo_parent

    @property
    def repo_remote(self):
        return self._repo_remote

    @property
    def git_ssh(self):
        return self._git_ssh

    @property
    def pkey(self):
        return self._pkey

    @property
    def git_hub_remote(self):
        return self._git_hub_remote

    @property
    def max_filesize(self):
        return self._max_filesize

    @property
    def max_num_trees(self):
        return self._max_num_trees

    @property
    def read_only(self):
        return self._read_only


def read_collections_config(request):
    """Load settings for a minor repo with shared tree collections"""
    conf = get_conf_object(request)
    collections_repo_parent = conf.get("apis", "collections_repo_parent")
    collections_repo_remote = conf.get("apis", "collections_repo_remote")
    try:
        git_ssh = conf.get("apis", "git_ssh")
    except:
        git_ssh = "ssh"
    try:
        pkey = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = "git@github.com:OpenTreeOfLife"
    try:
        max_filesize = conf.get("filesize", "collections_max_file_size")
    except:
        max_filesize = "20000000"
    return (
        collections_repo_parent,
        collections_repo_remote,
        git_ssh,
        pkey,
        git_hub_remote,
        max_filesize,
    )


def read_amendments_config(request):
    """Load settings for a minor repo with shared taxonomic amendments"""
    conf = get_conf_object(request)
    amendments_repo_parent = conf.get("apis", "amendments_repo_parent")
    amendments_repo_remote = conf.get("apis", "amendments_repo_remote")
    try:
        git_ssh = conf.get("apis", "git_ssh")
    except:
        git_ssh = "ssh"
    try:
        pkey = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = "git@github.com:OpenTreeOfLife"
    try:
        max_filesize = conf.get("filesize", "amendments_max_file_size")
    except:
        max_filesize = "20000000"
    return (
        amendments_repo_parent,
        amendments_repo_remote,
        git_ssh,
        pkey,
        git_hub_remote,
        max_filesize,
    )


def read_favorites_config(request):
    """Load settings for a minor repo with per-user 'favorites' information"""
    conf = get_conf_object(request)
    favorites_repo_parent = conf.get("apis", "favorites_repo_parent")
    favorites_repo_remote = conf.get("apis", "favorites_repo_remote")
    try:
        git_ssh = conf.get("apis", "git_ssh")
    except:
        git_ssh = "ssh"
    try:
        pkey = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = "git@github.com:OpenTreeOfLife"
    return favorites_repo_parent, favorites_repo_remote, git_ssh, pkey, git_hub_remote


def _raise_missing_auth_token():
    raise HTTPBadRequest(
        json.dumps(
            {
                "error": 1,
                "description": "You must provide an auth_token to authenticate to the OpenTree API",
            }
        )
    )


def authenticate(request):
    """Verify that we received a valid Github authentication token

    This method takes a dict of keyword arguments and optionally
    over-rides the author_name and author_email associated with the
    given token, if they are present.

    Returns a PyGithub object, author name and author email.

    This method will return HTTP 400 if the auth token is not present
    or if it is not valid, i.e. if PyGithub throws a BadCredentialsException.

    """
    # this is the GitHub API auth-token for a logged-in curator
    auth_token = find_in_request(request, "auth_token", "")

    if not auth_token:
        _raise_missing_auth_token()
    gh = Github(auth_token)
    gh_user = gh.get_user()
    auth_info = {}
    try:
        auth_info["login"] = gh_user.login
    except BadCredentialsException:
        raise400("You have provided an invalid or expired authentication token")
    # use the Github Oauth token to get a name/email if not specified
    # we don't provide these as default values above because they would
    # generate API calls regardless of author_name/author_email being specifed
    auth_info["name"] = find_in_request(request, "author_name", gh_user.name)
    auth_info["email"] = find_in_request(request, "author_email", gh_user.email)
    auth_info["auth_token"] = auth_token
    return auth_info


def auth_and_not_read_only(request):
    raise_if_read_only()
    return authenticate(request)


def log_time_diff(log_obj, operation="", prev_time=None):
    """If prev_time is not None, logs (at debug level) to
    log_obj the difference between now and the naive datetime
    object prev_time.
    `operation` is a string describing what events were timed.
    The current time is returned to allow for several
    calls with the form
       x = log_time_diff(_LOG, 'no op', x)
       foo()
       x = log_time_diff(_LOG, 'foo', x)
       bar()
       x = log_time_diff(_LOG, 'bar', x)
    """
    n = datetime.now()
    if prev_time is not None:
        td = n - prev_time
        t = td.total_seconds()
        log_obj.debug(
            'Timed operation "{o}" took {t:f} seconds'.format(o=operation, t=t)
        )
    return n


def get_oti_base_url(request):
    conf = get_conf_object(request)
    oti_base_url = conf.get("apis", "oti_base_url")
    if oti_base_url.startswith("//"):
        # Prepend scheme to a scheme-relative URL
        oti_base_url = "https:" + oti_base_url
    return oti_base_url


def get_oti_domain(request):
    oti_base = get_oti_base_url(request)
    s = oti_base.split("/")
    assert len(s) > 2
    return "/".join(s[:3])


def get_collections_api_base_url(request):
    conf = get_conf_object(request)
    base_url = conf.get("apis", "collections_api_base_url")
    if base_url.startswith("//"):
        # Prepend scheme to a scheme-relative URL
        base_url = "https:" + base_url
    return base_url


def clear_matching_cache_keys(key_pattern):
    # emulate our regex-powered cache clearing, as used in web2py
    """
    # brute force method, will clear all Beaker caches
    for _cache in cache_managers.values():
        _cache.clear()
    """
    assert len(cache_managers) == 1
    # NB - code below may change if we use multiple caches/regions!
    active_cache = list(cache_managers.values())[0]
    ns_mgr = active_cache.namespace
    namespaces = ns_mgr.namespaces.dict
    """
    This yields specific namespaces in the active cache, and keys/values for each cached item, e.g. 
    {
      '/Users/jima/projects/opentree/phylesystem-api/phylesystem_api/phylesystem_api/views/default.py|fetch_and_cache': {
        b'pull-through v3/amendments/list_all': (1648487894.102585, 600, <Response at 0x10f75fc10 200 OK>),
        b'another key': (1648487894.102585, 600, <Response at 0x10f75fc10 200 OK>)
      },
      'another namespace': {
        b'first key': (...),
        b'second key': (...)
      }
    }
    """
    assert len(namespaces) == 1
    active_namespace = list(namespaces.values())[0]
    # NB - again, code may change if we use multiple namespaces here
    # _LOG.debug("> clearing cached items matching [%s]" % key_pattern)
    # item_count_before = len(list(active_namespace.items()))
    # print("=== %d RAM cache keys BEFORE clearing: ===" % item_count_before)
    # for k, v in active_namespace.items():
    #     print('{k} ===> {v}'.format(k=k,v=v))
    # print("===")

    matching_keys = []
    for k, v in active_namespace.items():
        if re.match(key_pattern, str(k)):
            matching_keys.append(k)
    for matching_key in matching_keys:
        del active_namespace[matching_key]

    # item_count_after = len(list(active_namespace.items()))
    # print("=== %d RAM cache keys AFTER clearing: ===" % item_count_after)
    # for k, v in active_namespace.items():
    #     print('{k} ===> {v}'.format(k,v))
    # print("===")
    # print("  %d items removed" % (item_count_before - item_count_after,))


def raise_on_CORS_preflight(request):
    "A simple method for approving CORS preflight request"
    if request.method == "OPTIONS":
        # NB - This is VERY welcoming, which is our current API posture!
        requested_methods = request.headers.get("Access-Control-Allow-Methods", None)
        requested_headers = request.headers.get("Access-Control-Allow-Headers", None)
        if requested_methods:
            request.response.headers["Access-Control-Allow-Methods"] = requested_methods
        if requested_headers:
            request.response.headers["Access-Control-Allow-Headers"] = requested_headers
        raise HTTPOk("CORS preflight!", headers=request.response.headers)


def raise_if_read_only():
    "Add this to any web view that is disabled in a read-only setup"
    if READ_ONLY_MODE:
        raise HTTPForbidden(
            json.dumps(
                {"error": 1, "description": "phylesystem-api running in read-only mode"}
            )
        )
    return True


def call_http_json(url, verb="GET", data=None, headers=None):
    _LOG.debug("call_http_json data={}".format(str(data)))
    if headers is None:
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
    if data:
        # _LOG.debug("running http json call with DATA")
        # _LOG.debug("url: {}".format(url))
        # _LOG.debug("headers: {}".format(headers))
        # _LOG.debug("data: {}".format(json.dumps(data)))
        resp = requests.request(
            verb, url, headers=headers, data=json.dumps(data), allow_redirects=True
        )

    else:
        # _LOG.debug("running http json call NO DATA")
        resp = requests.request(verb, url, headers=headers, allow_redirects=True)
    resp.raise_for_status()
    return resp.status_code, resp.json()


def deferred_push_to_gh_call(request, resource_id, doc_type="nexson", auth_token=None):
    ##TODO Thius needs to create a bare URL for collections, and pass in the resource id etc as data
    # _LOG.debug("deferred_push_to_gh_call")
    raise_if_read_only()
    # Pass the resource_id in data, so that two-part collection IDs will be recognized
    # (else the second part will trigger an unwanted JSONP response from the push)
    if doc_type == "collection" or doc_type == "amendment":
        data = {"resource_id": resource_id, "doc_type": doc_type}
        resource_id = None  # to make bare url
    else:
        data = {}
    url = compose_push_to_github_url(request, resource_id, doc_type)
    if not auth_token:
        _raise_missing_auth_token()
    data["auth_token"] = auth_token
    # call_http_json(url=url, verb='PUT', data=data)
    threading.Thread(
        target=call_http_json,
        args=(
            url,
            "PUT",
            data,
        ),
    ).start()


def find_in_request(
    request, property_name, default_value=None, return_all_values=False
):
    """Search JSON body (if any), then try GET/POST keys"""
    if not isinstance(request, Request):
        msg = "request not provided in call to api_utils.find_in_request!"
        raise_int_server_err(msg)
    try:
        # recommended practice is all vars in the JSON body
        found_value = request.json_body.get(property_name)
        if found_value is not None:
            return found_value
    except:
        pass  # happens if we have no json_body
    # sometimes we allow vars from the query-string or form values
    if return_all_values:
        # NB - request.params combines GET and POST into a shared MultiDict
        found_value = request.params.getall(property_name)
        if found_value is None:
            return default_value
        return found_value
    # NB this returns None if default not specified!
    return request.params.get(property_name, default_value)


# Define a consistent cleaner to sanitize user input. We need a few
# tags and attributes that are common in our markdown but missing from the
# default Bleach whitelist.
import markdown
import re
import bleach
from bleach.sanitizer import Cleaner

# N.B. HTML comments are stripped by default. Non-allowed tags will appear
# "naked" in output, so we can identify any bad actors.
allowed_curation_comment_tags = [
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "pre",
    "code",
]  # any others?
ot_markdown_tags = list(set(bleach.sanitizer.ALLOWED_TAGS)) + list(
    set(allowed_curation_comment_tags)
)
# allow hyperlinks with target="_blank"
ot_markdown_attributes = {}
ot_markdown_attributes.update(bleach.sanitizer.ALLOWED_ATTRIBUTES)
ot_markdown_attributes["a"].append("target")
ot_cleaner = Cleaner(tags=ot_markdown_tags, attributes=ot_markdown_attributes)


def markdown_to_html(markdown_src="", open_links_in_new_window=False):
    extensions = [
        "mdx_linkify",
    ]
    try:  # coerce byte-string to Unicode
        markdown_src = markdown_src.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        pass
    html = markdown.markdown(
        markdown_src,
        extensions=extensions,
    )
    # NB - This is clumsy, but seems impossible to do with a second extension
    # like `markdown-link-attr-modifier`
    if open_links_in_new_window:
        html = re.sub(r" href=", r' target="_blank" href=', html)
    # scrub HTML output with bleach
    html = ot_cleaner.clean(html)
    try:  # coerce byte-string to Unicode
        html = html.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        pass
    return html


# another simple clean function to strip ALL tags (and entities from HTML
def remove_tags(markup):
    try:  # coerce Unicode to byte-string (required by ElementTree)
        markup = markup.encode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        pass
    try:
        markup = "".join(ElementTree.fromstring(markup).itertext())
    except ElementTree.ParseError:
        # if it won't parse (badly-formed XML/HTML, or plaintext), return unchanged
        pass
    # return value should be Unicode, not bytes
    markup = markup.decode("utf-8")
    return markup


def extract_json_from_http_call(request, data_field_name="data", request_params=None):
    """Returns the json blob (as a deserialized object) from `request_params` or the request.body.

    request_params can be the Pyramids request.params multidict or just a dict.
    """
    try:
        # check for kwarg data_field_name, or load the full request body
        if data_field_name in request_params:
            json_obj = request_params.get(data_field_name, {})
        else:
            json_obj = request.json_body

        if not isinstance(json_obj, dict):
            json_obj = json.loads(json_obj)
        if data_field_name in json_obj:
            json_obj = json_obj[data_field_name]
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('Exception getting JSON content in extract_json_from_http_call')
        raise400("no collection JSON found in request")
    return json_obj


def get_oti_wrapper(request):
    return OTI(oti=get_oti_domain(request))
