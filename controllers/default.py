import os
import time
from pygit2 import Repository
from pygit2 import Signature

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
    def POST(resource,resource_id):
        if not resource=='study': raise HTTP(400)

        if resource_id < 0 : raise HTTP(400)

        if not isinstance(resource_id, int) : raise HTTP(400)

        # TODO: validate
        nexson       = request.post_vars['nexson']
        author_name  = request.post_vars['author_name']
        author_email = request.post_vars['author_email']

        # which branch in treenexus should we use?
        repo      = Repository('./treenexus/.git')
        branch    = repo.lookup_branch('master')

        # grab the latest commit SHA1 on master
        last_commit = branch.target.hex

        encoding    = 'utf-8'
        committer   = Signature('OTOL API', 'api@opentreeoflife.org', 12346, 0, encoding)
        author      = Signature( author_name, author_email, 12345, 0, encoding)
        message     = "New OTOL API commit\n"
        tree        = repo.TreeBuilder().write()
        parents     = [ last_commit.parents ]

        # actually create a new commit
        sha         = repo.create_commit(None, author, committer, message,
                                        tree, parents, encoding)
        new_commit  = repo[sha]

        # overwrite the nexson of study_id with the POSTed data
        # 1) verify that it is valid json
        # 2) Update local treenexus git submodule at ./treenexus
        # 3) See if the hash of the current value of the file matches the hash of the POSTed data. If so, do nothing and return successfully.
        # 4) If not, overwrite the correct nexson file on disk
        # 5) Make a git commit with the updated nexson (add as much automated metadata to the commit message as possible)
        # 6) return successfully

        return dict()
    return locals()

def _get_nexson(study_id):

    this_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        filename    = this_dir + "/../treenexus/study/" + study_id + "/" + study_id + ".json"
        nexson_file = open(filename,'r')
    except IOError:
        return '{}'

    return nexson_file.readlines()
