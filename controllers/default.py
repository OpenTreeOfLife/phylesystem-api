import os
import time
import json
import hashlib
import github
from github import Github
import github_client
from githubwriter import GithubWriter
from pprint import pprint

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day

    def __validate(nexson):
        # stub function for hooking into NexSON validation
        pass

    def GET(resource,resource_id,subresource=None,subresource_id=None,jsoncallback=None,callback=None,_=None,*args,**kwargs):
        "OpenTree API methods relating to reading"
        valid_resources = ('study', 'search')
        valid_subresources = ('file',)  # TODO: support 'tree' in API?

        if not resource in valid_resources:
            raise HTTP(400, 'Resource requested not in list of valid resources: %s' % valid_resources)

        if subresource:
            if not subresource in valid_subresources:
                raise HTTP(400, 'Subresource requested not in list of valid subresources: %s' % valid_subresources)

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # fetch using the GitHub API auth-token for a logged-in curator
        auth_token = kwargs.get('auth_token', 'ANONYMOUS')
        if auth_token == 'ANONYMOUS':
            # non-web callers might be using an HTTP header ("Authorization: token abc123def456")
            auth_header = request.env.get('http_authorization', None) or request.wsgi.environ.get('HTTP_AUTHORIZATION', None)
            if auth_header:
                auth_token = auth_header.split()[1]

        if subresource:
            # TODO: return the specified file from this study
            # TODO: set content-disposition for download, and set filename?
            # We stash supporting files in the API server's filesystem (in a
            # shared folder, if multiple server instances). It should appear
            # in a subfolder named with the study's ID, e.g
            # "uploads/ot-351/Sequence data.xsl"
            pass
        else:
            # return the correct nexson of study_id, using the specified view
            try:
                # TODO: use readlines() in some way, to handle humongous files?
                return dict(FULL_RESPONSE=github_client.fetch_study(resource_id, auth_token))
            except Exception, e:
                return 'ERROR fetching study:\n%s' % e

    def POST(resource, resource_id=None, subresource=None, subresource_id=None, _method='POST', **kwargs):
        "OTOL API methods relating to creating (and importing) resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        # check for HTTP method override (passed on query string)
        if _method == 'PUT':
            return PUT(resource, resource_id, subresource, subresource_id, kwargs)
        elif _method == 'DELETE':
            return DELETE(resource, resource_id, subresource, subresource_id, kwargs)
        # elif _method == 'PATCH': ...

        if not resource=='study': raise HTTP(400, 'resource != study')

        # NOTE that we won't actually create or update files here. This should
        # be done with PUT (idempotent), since we know its URL and will be
        # posted the new/updated file in its entirety.

        # we're creating a new study (possibly with import instructions in the payload)
        cc0_agreement = kwargs.get('cc0_agreement', '')
        import_option = kwargs.get('import_option', '')
        treebase_id = kwargs.get('treebase_id', '')
        dryad_DOI = kwargs.get('dryad_DOI', '')
        import_option = kwargs.get('import_option', '')

        return kwargs
        # TODO: 
        # assign a new ID for this study, create its folder in repo(?)
        # forward ID and info to treemachine, expect to get study JSON back
        # IF treemachine returns JSON, save as {ID}.json and return URL as '201 Created'
        # or perhaps '303 See other' w/ redirect?
        # (should we do this on a WIP branch? save empty folder in 'master'?)
        # IF treemachine throws an error, return error info as '500 Internal Server Error'

    def PUT(resource, resource_id=None, subresource=None, subresource_id=None, **kwargs):
        "OTOL API methods relating to updating existing resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        if not resource=='study': raise HTTP(400, 'resource != study')
        if resource_id < 0 : raise HTTP(400, 'invalid resource_id: must be a postive integer')

        author_name  = kwargs.get('author_name','')
        author_email = kwargs.get('author_email','')
        # this is the GitHub API auth-token for a logged-in curator
        auth_token   = kwargs.get('auth_token','')

        if not auth_token:
            raise HTTP(400,"You must authenticate before updating via the OpenTree API")

        if subresource:
            # add or update a file in this study's folder
            if not subresource=='file': raise HTTP(400, 'subresource != file')
            if not subresource_id: raise HTTP(400, 'invalid subresource_id: should be a filename')

            # For now, we stash supporting files in the API server's filesystem (in
            # web2py's uploads/ directory, which should be a shared folder if
            # we have multiple server instances). It should appear in a
            # subfolder named with the study's ID, e.g "uploads/ot-351/Sequence data.xsl"
            try:
                # create study folder, if not found

                # delete any old file with this name? or rename w/ temporary name

                # save the new file with this name (uploaded data, or fetch URL and save)

                pass
            except:
                # TODO: restore old version of the file, if any?
                return {"error": 1, "description": "Unable to save this file: %s" % e }

            # What useful information should be returned on a successful write?
            return {
                "error": 0,
                # TODO: return filename? size?
            }

        # we're updating a study's Nexson
        try:
            nexson        = json.loads( kwargs.get('nexson','{}') )
        except:
            raise HTTP(400, 'NexSON must be valid JSON')

        # sort the keys of the POSTed NexSON and indent 0 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=0)

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_sha1        = hashlib.sha1( github_client.fetch_study(resource_id, auth_token) ).hexdigest()

        # the POSTed data is the same as what we currently have, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { "error": 0, "description": "success, nothing to update" };
        else:
            # validate the NexSON. If we find errors, prevent the update
            # if only warnings are found, make an additional commit containing the
            # warning annotation data
            __validate(nexson)

            # Connect to the Github v3 API via with this OAuth token
            # the org and repo should probably be in our config file
            gw = GithubWriter(oauth=auth_token, org="OpenTreeOfLife", repo="treenexus")

            # WARNING: Don't use a leading /, which will cause Github to create a corrupt tree!
            study_filename = "study/%s/%s.json" % (resource_id, resource_id)
            github_username= gw.gh.get_user().login
            branch_name    = "%s_study_%s" % (github_username, resource_id)

            try:
                new_sha = gw.create_or_update_file(
                    study_filename,
                    nexson,
                    "Update study #%s via OpenTree API" % resource_id,
                    branch_name
                )
            except github.GithubException, e:
                return {"error": 1, "description": "Got GithubException with status %d" % e.status }
            except:
                return {"error": 1, "description": "Got a non-GithubException: %s" % e }

            # What other useful information should be returned on a successful write?
            return {
                "error": 0,
                "branch_name": branch_name,
                "description": "Updated study #%s" % resource_id,
                "sha":  new_sha
            }

    def DELETE(resource, resource_id=None, subresource=None, subresource_id=None, **kwargs):
        "OTOL API methods relating to deleting existing resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        if not resource=='study': raise HTTP(400, 'resource != study')

        if subresource:
            if not subresource=='file': raise HTTP(400, 'subresource != file')


    def OPTIONS(args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200)

    return locals()
