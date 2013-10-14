import os
import time
import json
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


        # overwrite the nexson of study_id with the POSTed data
        # 1) verify that it is valid json
        # 2) Update local treenexus git submodule at ./treenexus
        _update_treenexus()
        # 3) See if the hash of the current value of the file matches the hash of the POSTed data. If so, do nothing and return successfully.
        # 4) If not, overwrite the correct nexson file on disk
        # 5) Make a git commit with the updated nexson (add as much automated metadata to the commit message as possible)
        # 6) return successfully

        return dict()
    return locals()

def _update_treenexus():
    """Update the treenexus git submodule"""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    # submodule update must be run from the top-level dir of our repo
    os.system("cd ..; git submodule update")


def _get_nexson(study_id):
    """Return the NexSON of a given study_id"""
    this_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        filename    = this_dir + "/../treenexus/study/" + study_id + "/" + study_id + ".json"
        nexson_file = open(filename,'r')
    except IOError:
        return '{}'

    return nexson_file.readlines()
