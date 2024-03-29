import json
import logging
import sys

import requests
from peyotl.external import import_nexson_from_treebase
from peyotl.nexson_syntax import (
    get_empty_nexson,
    extract_supporting_file_messages,
    PhyloSchema,
    BY_ID_HONEY_BADGERFISH,
)
from peyotl.phylesystem.git_workflows import (
    GitWorkflowError,
    validate_and_convert_nexson,
)
from pyramid.encode import quote_plus, urlencode

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPNotFound,
    HTTPBadRequest,
)
from pyramid.renderers import render_to_response
from pyramid.view import view_config

import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import (
    find_in_request,
    raise400,
    raise404,
    fetch_doc,
    commit_doc_and_trigger_push,
    get_parent_sha,
    get_commit_message,
)

_LOG = logging.getLogger("phylesystem_api")


def __extract_nexson_from_http_call(request, **kwargs):
    """Returns the nexson blob from `kwargs` or the request.body"""
    try:
        # check for kwarg 'nexson', or load the full request body
        if "nexson" in kwargs:
            nexson = kwargs.get("nexson", {})
        else:
            nexson = request.json_body
        if not isinstance(nexson, dict):
            nexson = json.loads(nexson)
        if "nexson" in nexson:
            nexson = nexson["nexson"]
        return nexson
    except:
        raise400("NexSON must be valid JSON")


def __extract_and_validate_nexson(request, repo_nexml2json, kwargs):
    try:
        nexson = __extract_nexson_from_http_call(request, **kwargs)
        pc = api_utils.read_phylesystem_config(request)
        bundle = validate_and_convert_nexson(
            nexson,
            repo_nexml2json,
            allow_invalid=False,
            max_num_trees_per_study=pc.max_num_trees,
        )
        nexson, annotation, validation_log, nexson_adaptor = bundle
        return nexson, annotation, nexson_adaptor
    except GitWorkflowError as err:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('PUT failed in validation')
        raise400(err.msg or "No message found")


def __make_valid_DOI(candidate):
    # Try to convert the candidate string to a proper, minimal DOI. Return the DOI,
    # or None if conversion is not possible.
    #   WORKS: http://dx.doi.org/10.999...
    #   WORKS: 10.999...
    #   FAILS: 11.999...
    #   WORKS: doi:10.999...
    #   WORKS: DOI:10.999...
    #   FAILS: http://example.com/
    #   WORKS: http://example.com/10.blah
    #   FAILS: something-else
    doi_prefix = "10."
    # All existing DOIs use the directory indicator '10.', see
    #   http://www.doi.org/doi_handbook/2_Numbering.html#2.2.2

    # Remove all whitespace from the candidate string
    if not candidate:
        return None
    candidate = "".join(candidate.split())
    if doi_prefix in candidate:
        # Strip everything up to the first '10.'
        doi_parts = candidate.split(doi_prefix)
        doi_parts[0] = ""
        # Remove any preamble and return the minimal DOI
        return doi_prefix.join(doi_parts)
    else:
        return None


def __validate_output_nexml2json(
    repo_nexml2json, kwargs, resource, type_ext, content_id=None
):
    # sometimes we need to tweak the incoming kwargs, so let's
    # make a mutable MultiDict copy of Pyramid's immutable NestedMultiDict
    kwargs = kwargs.copy()
    msg = None
    if "output_nexml2json" not in kwargs:
        kwargs["output_nexml2json"] = "0.0.0"
    biv = kwargs.get("bracket_ingroup")
    if biv and isinstance(biv, str):
        if biv.lower() in ["f", "false", "0"]:
            kwargs["bracket_ingroup"] = False
        else:
            kwargs["bracket_ingroup"] = True
    try:
        schema = PhyloSchema(
            schema=kwargs.get("format"),
            type_ext=type_ext,
            content=resource,
            content_id=content_id,
            repo_nexml2json=repo_nexml2json,
            **kwargs
        )
        if not schema.can_convert_from(resource):
            msg = "Cannot convert from {s} to {d}".format(
                s=repo_nexml2json, d=schema.description
            )
    except ValueError as x:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        msg = str(x)
        # _LOG.exception('GET failing: {m}'.format(m=msg))
    if msg:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.debug('output sniffing err msg = ' + msg)
        raise400(msg)
    return schema


def __finish_write_verb(
    phylesystem,
    git_data,
    nexson,
    resource_id,
    auth_info,
    adaptor,
    annotation,
    parent_sha,
    commit_msg="",
    master_file_blob_included=None,
):
    """Called by PUT and POST handlers to avoid code repetition."""
    # TODO, need to make this spawn a thread to do the second commit rather than block
    a = phylesystem.annotate_and_write(
        git_data,
        nexson,
        resource_id,
        auth_info,
        adaptor,
        annotation,
        parent_sha,
        commit_msg,
        master_file_blob_included,
    )
    annotated_commit = a
    if annotated_commit["error"] != 0:
        raise HTTPBadRequest(body=json.dumps(annotated_commit))
    return annotated_commit


def _fetch_duplicate_study_ids(request, study_DOI=None, study_ID=None):
    # Use the oti (docstore index) service to see if there are other studies in
    # the collection with the same DOI; return the IDs of any duplicate studies
    # found, or an empty list if there are no dupes.
    if not study_DOI:
        return []
    oti = api_utils.get_oti_wrapper(request)
    duplicate_study_ids = oti.find_studies(
        {"ot:studyPublication": study_DOI}, verbose=False, exact=True
    )
    # strip the list to just include bare study IDs
    duplicate_study_ids = [x['ot:studyId'] for x in duplicate_study_ids]
    try:
        duplicate_study_ids.remove(study_ID)
    except ValueError:
        # ignore error, if oti is lagging and doesn't have this study yet
        pass
    return duplicate_study_ids


def _fetch_shard_name(phylesystem, study_id):
    try:
        return phylesystem.get_repo_and_path_fragment(study_id)[0]
    except:
        _LOG.debug("_fetch_shard_name failed for study {}".format(study_id))
        return None


@view_config(route_name="create_study", renderer="json", request_method="OPTIONS")
@view_config(route_name="study_CORS_preflight", renderer="json")
def study_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)


@view_config(route_name="fetch_study", renderer=None, request_method="GET")
@view_config(route_name="fetch_study_label", renderer=None, request_method="GET")
def fetch_study(request):
    study_id = request.matchdict["study_id"]
    _LOG.debug("study_id = {}".format(study_id))
    # does this look like a filename? if so, grab its extension
    request_extension = None
    fpps = study_id.split(".")
    if len(fpps) > 1:
        _LOG.debug("len(fpps) > 1")
        request_extension = fpps[-1]
        study_id = ".".join(fpps[:-1])
        _LOG.debug("Request extension is {}".format)
        if request_extension not in ("html", "json"):
            request_extension = ".{}".format(request_extension)
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    out_schema = __validate_output_nexml2json(
        repo_nexml2json,
        request.params,  # combined GET and POST
        "study",
        type_ext=request_extension,
        content_id=None,
    )
    result = fetch_doc(
        request,
        doc_id=study_id,
        doc_store=phylesystem,
        doc_type_name="study",
        add_version_history=out_schema.is_json(),
    )
    return add_study_specific_fields(
        request, study_id, out_schema, phylesystem, repo_nexml2json, result
    )


def add_study_specific_fields(
    request, study_id, out_schema, phylesystem, repo_nexml2json, result
):
    head_sha = result["sha"]
    study_nexson = result["data"]
    blob_sha = phylesystem.get_blob_sha_for_study_id(study_id, head_sha)
    phylesystem.add_validation_annotation(study_nexson, blob_sha)

    try:
        comment_html = api_utils.markdown_to_html(
            study_nexson["nexml"]["^ot:comment"], open_links_in_new_window=True
        )
    except:
        comment_html = ""
    if out_schema.format_str == "nexson" and out_schema.version == repo_nexml2json:
        result_data = study_nexson
    else:
        try:
            serialize = not out_schema.is_json()
            src_schema = PhyloSchema("nexson", version=repo_nexml2json)
            result_data = out_schema.convert(
                study_nexson, serialize=serialize, src_schema=src_schema
            )
        except:
            m = "Exception while coercing NexSON to output schema."
            _LOG.exception(m)
            raise400(m)
    if out_schema.is_json():
        try:
            study_DOI = study_nexson["nexml"]["^ot:studyPublication"]["@href"]
        except KeyError:
            study_DOI = None
        try:
            duplicate_study_ids = _fetch_duplicate_study_ids(
                request, study_DOI, study_id
            )
        except:
            # _LOG.exception('call to OTI check for duplicate DOIs failed')
            duplicate_study_ids = None

        try:
            shard_name = _fetch_shard_name(phylesystem, study_id)
        except:
            # _LOG.exception('check for shard name failed')
            shard_name = None
        wip_map = result["branch2sha"]
        version_history = result.get("versionHistory")
        result = {
            "sha": head_sha,
            "data": result_data,
            "branch2sha": wip_map,
            "commentHTML": comment_html,
        }
        if duplicate_study_ids is not None:
            result["duplicateStudyIDs"] = duplicate_study_ids
        if shard_name:
            result["shardName"] = shard_name
        if version_history:
            result["versionHistory"] = version_history
        return render_to_response("json", result, request)
    else:
        # _LOG.debug(result_data)
        return render_to_response("string", result_data, request)


def _new_nexson_with_crossref_metadata(doi, ref_string, include_cc0=False):
    # look for matching studies via CrossRef.org API
    # N.B. The recommended API method is very different for DOI vs.
    # a reference string, but we can also use the filter option to get
    # consistent behavior and response.
    no_match_found = False
    meta_publication_reference = ""
    try:
        if doi:
            # use the supplied DOI to fetch study metadata
            lookup_response = requests.get(
                "https://api.crossref.org/works?%s"
                % urlencode({"rows": 1, "filter": "doi:" + doi})
            ).text  # always Unicode
        elif ref_string:
            # use the supplied reference text to fetch study metadata
            lookup_response = requests.get(
                "https://api.crossref.org/works?%s"
                % urlencode({"rows": 1, "query": ref_string})
            ).text  # always Unicode
        try:
            response_json = json.loads(lookup_response)
            response_status = response_json.get("status", "")
        except:
            response_status = "missing or malformed response text"
        if response_status == "ok":
            matching_records = response_json.get("message", {}).get("items", [])
            if len(matching_records) == 0:
                no_match_found = True
        else:
            # Something went wrong (TODO: Capture and log any error message?)
            no_match_found = True

    except requests.RequestException:
        # Both calls above should return a 200 status even if there's no match.
        # So apparently the CrossRef service is down for some reason.
        no_match_found = True

    if no_match_found:
        # Add a bogus reference string to signal the lack of results
        meta_publication_url = ""
        meta_year = ""
        if doi:
            meta_publication_reference = "No matching publication found for this DOI!"
        else:
            meta_publication_reference = (
                "No matching publication found for this reference string"
            )
    else:
        # We got a match! These are sorted by score, so we should assume the
        # first (possibly only) record is the best match.
        # See https://github.com/CrossRef/rest-api-doc#sort-order
        match = matching_records[0]
        meta_publication_url = match.get("URL", "")  # should be its DOI in URL form
        # Try to capture the publication year (print first, or online)
        meta_year = ""
        date_parts = match.get("published-print", {}).get("date-parts", [])
        if len(date_parts) == 0:
            # try again using online publication
            date_parts = match.get("published-online", {}).get("date-parts", [])
        if len(date_parts) > 0:
            # retrieve its inner parts list (not sure why this is nested)
            inner_date_parts = date_parts[0]
            if len(inner_date_parts) > 0:
                # first/only element here should be a year
                meta_year = inner_date_parts[0]

        # capture the raw DOI so we can try to retrieve a reference string below
        doi = match.get("DOI", "")

    # We need another API call to fetch a plain-text reference string.
    # NB - this is probabl APA style (based on conversation with CrossRef API team)
    if doi:
        try:
            # use the supplied (or recovered) DOI to fetch a plain-text reference string
            lookup_response = requests.get(
                "https://api.crossref.org/works/%s/transform/text/x-bibliography"
                % quote_plus(doi)
            ).content  # vs .text, which would decode to Unicode
            # make sure it's plain text (no markup)!
            meta_publication_reference = api_utils.remove_tags(lookup_response)

        except requests.RequestException as e:
            # Any response but 200 means no match found, or the CrossRef
            # service is down for some reason.
            _LOG.debug("URLError fetching ref-text!!")
            _LOG.debug(e)
            meta_publication_reference = "No matching publication found for this DOI!"

    # add any found values to a fresh NexSON template
    nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH, include_cc0=include_cc0)
    nexml_el = nexson["nexml"]
    nexml_el["^ot:studyPublicationReference"] = meta_publication_reference
    if meta_publication_url:
        nexml_el["^ot:studyPublication"] = {"@href": meta_publication_url}
    if meta_year:
        nexml_el["^ot:studyYear"] = meta_year
    return nexson


# NOTE that we don't offer CC-BY 4.0, which is problematic for data
_license2url = {
    "CC=0": ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    "CC-BY-2.0": ("CC-BY 2.0", "https://creativecommons.org/licenses/by/2.0/"),
    "CC-BY-2.5": ("CC-BY 2.5", "https://creativecommons.org/licenses/by/2.5/"),
    "CC-BY-3.0": ("CC-BY 3.0", "https://creativecommons.org/licenses/by/3.0/"),
    "CC-BY": ("CC-BY 3.0", "https://creativecommons.org/licenses/by/3.0/"),
}


def _add_license_info(cc0_agreement, nexml, request):
    # If submitter requested the CC0 waiver or other waiver/license, make sure it's here
    if cc0_agreement:
        existing_license = "CC-0"
    else:
        # Are they using an existing license or waiver (CC0, CC-BY, something else?)
        chosen_license = find_in_request(request, "chosen_license", "")
        if chosen_license != "study-data-has-existing-license":
            return
        existing_license = find_in_request(request, "alternate_license", "")
    lic_name_url = _license2url.get(existing_license)
    if lic_name_url is None:
        license_name = find_in_request(request, "alt_license_name", "")
        license_url = find_in_request(request, "alt_license_URL", "")
    else:
        license_name, license_url = lic_name_url
    nexml["^xhtml:license"] = {"@name": license_name, "@href": license_url}


@view_config(route_name="create_study", renderer="json", request_method="POST")
def create_study(request):
    # this method requires authentication
    r_auth_info = api_utils.auth_and_not_read_only(request)
    phylesystem = api_utils.get_phylesystem(request)

    # we're creating a new study (possibly with import instructions in the payload)
    treebase_id = find_in_request(request, "treebase_id", "")
    publication_doi = find_in_request(request, "publication_DOI", "")
    # if a URL or something other than a valid DOI was entered, don't submit it to crossref API
    publication_doi_for_crossref = __make_valid_DOI(publication_doi) or None
    publication_ref = find_in_request(request, "publication_reference", "")
    # is the submitter explicity applying the CC0 waiver to a new study?
    cc0_agreement = (
        find_in_request(request, "chosen_license", "") == "apply-new-CC0-waiver"
        and find_in_request(request, "cc0_agreement", "") == "true"
    )
    # look for the chosen import method, e.g,
    # 'import-method-PUBLICATION_DOI' or 'import-method-MANUAL_ENTRY'
    import_method = find_in_request(request, "import_method", "")
    ##dryad_DOI = find_in_request(request, 'dryad_DOI', '')

    # Create initial study NexSON using the chosen import method.
    #
    # N.B. We're currently using a streamlined creation path with just
    # two methods (TreeBASE ID and publication DOI). But let's keep the
    # logic for others, just in case we revert based on user feedback.
    importing_from_treebase_id = (
        import_method == "import-method-TREEBASE_ID" and treebase_id != ""
    )
    importing_from_post_arg = import_method == "import-method-POST"
    importing_from_crossref_API = (
        import_method == "import-method-PUBLICATION_DOI"
        and publication_doi_for_crossref
    ) or (import_method == "import-method-PUBLICATION_REFERENCE" and publication_ref)

    # any of these methods should returna parsed NexSON dict (vs. string)
    if importing_from_treebase_id:
        # make sure the treebase ID is an integer
        treebase_id = "".join(treebase_id.split())  # remove all whitespace
        treebase_id = treebase_id.lstrip("S").lstrip(
            "s"
        )  # allow for possible leading 'S'?
        try:
            treebase_id = int(treebase_id)
        except ValueError as e:
            msg = "TreeBASE ID should be a simple integer, not '{}'! Details:\n{}"
            raise400(msg.format(treebase_id, str(e)))
        try:
            new_study_nexson = import_nexson_from_treebase(
                treebase_id, nexson_syntax_version=BY_ID_HONEY_BADGERFISH
            )
        except Exception:
            msg = "Unexpected error parsing the file obtained from TreeBASE. Please report this bug to the Open Tree of Life developers."
            api_utils.raise_int_server_err(msg)
    elif importing_from_crossref_API:
        new_study_nexson = _new_nexson_with_crossref_metadata(
            doi=publication_doi_for_crossref,
            ref_string=publication_ref,
            include_cc0=cc0_agreement,
        )
    elif importing_from_post_arg:
        repo_nexml2json = phylesystem.repo_nexml2json
        bundle = __extract_and_validate_nexson(
            request, repo_nexml2json, request.json_body
        )
        new_study_nexson = bundle[0]
    else:  # assumes 'import-method-MANUAL_ENTRY', or insufficient args above
        new_study_nexson = get_empty_nexson(
            BY_ID_HONEY_BADGERFISH, include_cc0=cc0_agreement
        )
        if publication_doi:
            # submitter entered an invalid DOI (or other URL); add it now
            new_study_nexson["nexml"]["^ot:studyPublication"] = {
                "@href": publication_doi
            }
    nexml = new_study_nexson["nexml"]
    if not importing_from_post_arg:
        _add_license_info(cc0_agreement, nexml, request)
    nexml["^ot:curatorName"] = r_auth_info.get("name", "")

    def study_commit_fn(doc, doc_id, auth_info, **kwargs):
        return phylesystem.ingest_new_study(
            doc, phylesystem.repo_nexml2json, auth_info, doc_id
        )

    return commit_doc_and_trigger_push(
        request,
        commit_fn=study_commit_fn,
        doc=new_study_nexson,
        doc_id=None,
        doc_type_name="nexson",
        auth_info=r_auth_info,
        commit_msg=None,
    )


@view_config(route_name="update_study", renderer="json")
def update_study(request):
    study_id = request.matchdict["study_id"]
    r_auth_info = api_utils.auth_and_not_read_only(request)
    _LOG.debug("STUDY: update_study")
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    bundle = __extract_and_validate_nexson(request, repo_nexml2json, request.json_body)
    nexson, annotation, nexson_adaptor = bundle
    try:
        gd = phylesystem.create_git_action(study_id)
    except KeyError:
        # _LOG.debug('PUT failed in create_git_action (probably a bad study ID)')
        raise400("invalid study ID, please check the URL")

    def update_study_fn(doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg):
        return doc_id, __finish_write_verb(
            phylesystem,
            gd,
            nexson=doc,
            resource_id=doc_id,
            auth_info=auth_info,
            adaptor=nexson_adaptor,
            annotation=annotation,
            parent_sha=parent_sha,
            commit_msg=commit_msg,
            master_file_blob_included=merged_sha,
        )

    r_parent_sha = get_parent_sha(request)
    r_commit_msg = get_commit_message(request)
    r_merged_sha = find_in_request(request, "merged_SHA")

    blob = commit_doc_and_trigger_push(
        request,
        commit_fn=update_study_fn,
        doc=nexson,
        doc_id=study_id,
        doc_type_name="nexson",
        auth_info=r_auth_info,
        parent_sha=r_parent_sha,
        merged_sha=r_merged_sha,
        commit_msg=r_commit_msg,
    )
    blob["versionHistory"] = phylesystem.get_version_history_for_study_id(study_id)
    return blob


@view_config(route_name="delete_study", renderer="json")
def delete_study(request):
    study_id = request.matchdict["study_id"]
    _LOG.debug("delete study_id={}".format(study_id))
    r_auth_info = api_utils.auth_and_not_read_only(request)
    r_commit_msg = get_commit_message(request)
    r_parent_sha = get_parent_sha(request)
    _LOG.debug("parent_sha={}".format(r_parent_sha))

    phylesystem = api_utils.get_phylesystem(request)

    def del_study_fn(doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg):
        return doc_id, phylesystem.delete_study(
            doc_id, auth_info, parent_sha, commit_msg=commit_msg
        )

    blob = commit_doc_and_trigger_push(
        request,
        commit_fn=del_study_fn,
        doc=None,
        doc_id=study_id,
        doc_type_name="nexson",
        auth_info=r_auth_info,
        parent_sha=r_parent_sha,
        merged_sha=None,
        commit_msg=r_commit_msg,
    )
    return blob


@view_config(route_name="get_study_file_list", renderer="json")
@view_config(route_name="get_study_single_file", renderer="json")
def get_study_file(request):
    api_utils.raise_on_CORS_preflight(request)
    study_id = request.matchdict["study_id"]
    file_id = request.matchdict.get("file_id", None)
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    __validate_output_nexml2json(
        repo_nexml2json,
        request.params,  # combined GET and POST
        "file",
        type_ext=None,
        content_id=study_id,
    )
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    try:
        r = phylesystem.return_study(
            study_id, commit_sha=parent_sha, return_WIP_map=True
        )
    except:
        raise404("Study #{} GET failure".format(study_id))
    study_nexson, head_sha, wip_map = r
    # TODO: return a description of the requested file, or a list of all files
    m_list = extract_supporting_file_messages(study_nexson)
    if file_id is None:
        r = []
        for m in m_list:
            files = m.get("data", {}).get("files", {}).get("file", [])
            for f in files:
                if "@url" in f:
                    r.append(
                        {
                            "id": m["@id"],
                            "filename": f.get("@filename", ""),
                            "url_fragment": f["@url"],
                        }
                    )
                    break
        return r
    else:
        try:
            matching = None
            for m in m_list:
                if m["@id"] == file_id:
                    matching = m
                    break
            if matching is None:
                msg = 'No file with id="{f}" found in study="{s}"'
                raise404(msg.format(f=file_id, s=study_id))
            u = None
            files = m.get("data", {}).get("files", {}).get("file", [])
            for f in files:
                if "@url" in f:
                    u = f["@url"]
                    break
            if u is None:
                msg = 'No @url found in the message with id="{f}" found in study="{s}"'
                raise404(msg.format(f=file_id, s=study_id))

            # TEMPORARY HACK TODO
            u = u.replace("uploadid=", "uploadId=")
            # TODO: should not hard-code this, I suppose... (but not doing so requires more config...)
            if u.startswith("/curator"):
                u = "https://tree.opentreeoflife.org" + u
            request.response.headers["Content-Type"] = "text/plain"
            fetched = requests.get(u)
            fetched.raise_for_status()
            return fetched.text
        except Exception as x:
            # _LOG.exception('file_get failed')
            raise404('Could not retrieve file. Exception: "{}"'.format(str(x)))


@view_config(route_name="get_study_external_url", renderer="json")
def get_study_external_url(request):
    api_utils.raise_on_CORS_preflight(request)
    study_id = request.matchdict["study_id"]
    phylesystem = api_utils.get_phylesystem(request)
    try:
        u = phylesystem.get_public_url(study_id)
        return json.dumps({"url": u, "study_id": study_id})
    except:
        raise404("study not found")


@view_config(route_name="get_study_tree", renderer=None)
@view_config(route_name="get_study_tree_label", renderer=None)
def get_study_tree(request):
    tree_id_with_extension = request.matchdict["tree_id_with_extension"]
    tree_name_parts = tree_id_with_extension.split(".")
    tree_id = tree_name_parts[0]
    if len(tree_name_parts) > 1:
        file_ext = ".{}".format(tree_name_parts[1])
    else:
        file_ext = None
    return _fine_grained_get(request, "tree", content_id=tree_id, file_ext=file_ext)


@view_config(route_name="get_study_otus", renderer=None)
@view_config(route_name="get_study_otus_slash", renderer=None)
def get_study_otus(request):
    return _fine_grained_get(request, "otus")


@view_config(route_name="get_study_otu", renderer=None)
@view_config(route_name="get_study_otu_slash", renderer=None)
def get_study_otu(request):
    return _fine_grained_get(request, "otu")


@view_config(route_name="get_study_otu_by_id", renderer=None)
@view_config(route_name="get_study_otu_by_id_slash", renderer=None)
def get_study_otu(request):
    otu_id = request.matchdict["otu_id"]
    return _fine_grained_get(request, "otu", content_id=otu_id)


@view_config(route_name="get_study_otumap", renderer=None)
@view_config(route_name="get_study_otumap_slash", renderer=None)
def get_study_otumap(request):
    return _fine_grained_get(request, "otumap")


@view_config(route_name="get_study_meta", renderer=None)
@view_config(route_name="get_study_meta_slash", renderer=None)
def get_study_ometa(request):
    return _fine_grained_get(request, "meta")


def _fine_grained_get(request, subresource, content_id=None, file_ext=None):
    api_utils.raise_on_CORS_preflight(request)
    study_id = request.matchdict["study_id"]
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    out_schema = __validate_output_nexml2json(
        repo_nexml2json,
        request.params,  # combined GET and POST
        subresource,
        type_ext=file_ext,
        content_id=content_id,
    )
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    try:
        r = phylesystem.return_study(
            study_id, commit_sha=parent_sha, return_WIP_map=True
        )
    except:
        raise404("Study #{} GET failure".format(study_id))
    try:
        study_nexson, head_sha, wip_map = r
        blob_sha = phylesystem.get_blob_sha_for_study_id(study_id, head_sha)
        phylesystem.add_validation_annotation(study_nexson, blob_sha)
    except:
        _LOG.exception("GET failed")
        e = sys.exc_info()[0]
        raise HTTPBadRequest(e)

    try:
        serialize = not out_schema.is_json()
        src_schema = PhyloSchema("nexson", version=repo_nexml2json)
        result_data = out_schema.convert(
            study_nexson, serialize=serialize, src_schema=src_schema
        )
    except:
        msg = "Exception in coercing to the required NexSON version for validation. "
        # _LOG.exception(msg)
        raise HTTPBadRequest(msg)

    if result_data is None:
        m = 'subresource "{b}/{t}" not found in study "{s}"'
        m = m.format(b=subresource, t=content_id, s=study_id)
        raise HTTPNotFound(body=m)
    if out_schema.is_json():
        return render_to_response("json", result_data, request)
    return render_to_response("string", result_data, request)
