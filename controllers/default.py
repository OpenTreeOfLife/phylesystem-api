import os
import time
import json
import hashlib
import github
from github import Github
import github_client
import GithubWriter
from pprint import pprint

@request.restful()
def v1():
    "The OTOL API v1"
    response.view = 'generic.json'

    def GET(resource,resource_id,jsoncallback=None,callback=None,_=None,**kwargs):
        "OTOL API methods relating to reading"
        if not resource=='study': raise HTTP(400, 'resource != study [GET]')

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

        # return the correct nexson of study_id, using the specified view
        try:
            # TODO: use readlines() in some way, to handle humongous files?
            return dict(FULL_RESPONSE=github_client.fetch_study(resource_id, auth_token))
        except Exception, e:
            return 'ERROR fetching study:\n%s' % e

    def POST(resource, resource_id=None, **kwargs):
        "OTOL API methods relating to writing"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        if not resource=='study': raise HTTP(400, 'resource != study')

        # TODO: use presence or absence of resource_id as a cue to creation vs.
        # updates? Or better yet, support method overrides (on POST requests)
        # for PUT, PATCH, DELETE and redirect as needed:
        # http://www.vinaysahni.com/best-practices-for-a-pragmatic-restful-api#method-override
        #
        if False:
            if resource_id:
                # this is an update(?) of an existing study, use code below
                pass
            else:
                # we're creating a new study (possibly with import instructions in the payload)
                cc0_agreement = kwargs.get('cc0_agreement', '')
                import_option = kwargs.get('import_option', '')
                treebase_id = kwargs.get('treebase_id', '')
                dryad_DOI = kwargs.get('dryad_DOI', '')
                import_option = kwargs.get('import_option', '')

                return kwargs
                # TODO: assign a new ID for this study, create its folder in repo(?)
                # forward ID and info to treemachine, expect to get study JSON back
                # IF treemachine returns JSON, save as {ID}.json and return URL as '201 Created'
                # or perhaps '303 See other' w/ redirect?
                # (should we do this on a WIP branch? save empty folder in 'master'?)
                # IF treemachine throws an error, return error info as '500 Internal Server Error'

        if resource_id < 0 : raise HTTP(400, 'invalid resource_id: must be a postive integer')

        author_name  = kwargs.get('author_name','')
        author_email = kwargs.get('author_email','')
        # this is the GitHub API auth-token for a logged-in curator
        auth_token   = kwargs.get('auth_token','')

        if not auth_token:
            raise HTTP(400,"You must authenticate before updating via the OTOL API")

        try:
            nexson        = json.loads( kwargs.get('nexson','{}') )
        except:
            raise HTTP(400, 'NexSON must be valid JSON')

        # sort the keys of the POSTed NexSON and indent 4 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=4)

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_sha1        = hashlib.sha1( github_client.fetch_study(resource_id, auth_token) ).hexdigest()

        # the POSTed data is the same as what we have on disk, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { "error": 0, "description": "success, nothing to update" };
        else:
            # Connect to the Github v3 API via with this OAuth token
            # the org and repo should probably be in our config file
            gw = GithubWriter(oauth=auth_token, org="OpenTreeOfLife", repo="treenexus")

            study_filename = "/study/%s/%s.json" % (resource_id, resource_id)
            branch_name    = "%s_study_%s" % (gw.gh.get_user(), resource_id)

            try:
                gw.create_or_update_file(
                    study_filename,
                    nexson,
                    "Update study #%s via OTOL API" % resource_id,
                    branch_name
                )
            except github.GithubException, e:
                return {"error": 1, "description": "Got GithubException with status %d" % e.status }
            except:
                return {"error": 1, "description": "Got a non-GithubException: %s" % e }

            # What other useful information should be returned on a successful write?
            return {"error": 0, "branch_name": branch_name, "description": "Updated study #%s" % resource_id }

    return locals()
