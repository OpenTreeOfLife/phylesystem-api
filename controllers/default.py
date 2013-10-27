import os
import time
import json
import hashlib
from github import Github

def index():
    def GET():
        return locals()

@request.restful()
def api():
    response.view = 'generic.json'
    def GET(resource,resource_id):
        if not resource=='study': raise HTTP(400)
        # return the correct nexson of study_id
        return _get_nexson(resource_id)

    @auth.requires_login()
    def POST(resource,resource_id, **kwargs):
        if not resource=='study': raise HTTP(400, 'resource != study')

        if resource_id < 0 : raise HTTP(400, 'invalid resource_id: must be a postive integer')

        oauth_token  = auth.user.github_auth_token
        author_name  = auth.user.name
        author_email = auth.user.email

        if not oauth_token:
            raise HTTP(400,"You must authenticate to before updating via the OTOL API")

        # Connect to the Github v3 API via with this OAuth token
        gh = Github(oauth_token)

        try:
            nexson        = json.loads( kwargs.get('nexson','{}') )
        except:
            raise HTTP(400, 'NexSON must be valid JSON')

        # sort the keys of the POSTed NexSON and indent 4 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=4)

        _update_treenexus()

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_sha1        = hashlib.sha1( _get_nexson(resource_id) ).hexdigest()

        # the POSTed data is the same as what we have on disk, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { error: 0, description: "success" };
        else:
            # we have new data
            # TODO: Use http://jacquev6.github.io/PyGithub/github_objects/Repository.html#github.Repository.Repository.create_git_commit
            return dict()
    return locals()

def _update_treenexus():
    """Update the treenexus git submodule"""
    # submodule update must be run from the top-level dir of our repo
    rc = os.system("cd ..; git submodule update")
    if rc:
        raise HTTP(400,"Unable to update local treenexus.git")

def _study_id_to_filename(study_id):
    """Return the filename of a given study_id"""
    this_dir  = os.path.dirname(os.path.abspath(__file__))
    filename  = this_dir + "/../treenexus/study/" + study_id + "/" + study_id + ".json"
    return filename

def _get_nexson(study_id):
    """Return the NexSON of a given study_id"""
    try:
        filename    = _study_id_to_filename(study_id)
        nexson_file = open(filename,'r')
    except IOError:
        return { error: 1, description: "unknown study" }

    return nexson_file.readlines()
