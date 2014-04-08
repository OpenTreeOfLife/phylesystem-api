#!/usr/bin/env python

import json, requests, sys

# check args for repo-URL, Open Tree API URL, GitHub auth-key?
this_script = sys.argv[0]

if len(sys.argv) > 1:
	opentree_docstore_url = sys.argv[1]
else:
    print "Please specify the Open Tree doc-store URL as first argument: '%s <repo-URL> <public-API-URL> <GitHub-OAuth-token-file>'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 2:
	opentree_api_base_url = sys.argv[2].rstrip("/").rstrip("/api/v1")
else:
    print "Please specify the Open Tree API public URL as second argument: '%s <repo-URL> <public-API-URL> <GitHub-OAuth-token-file>'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong
 
if len(sys.argv) > 3:
	oauth_token_file = sys.argv[3]
else:
    print "Please specify an OAuth token file (for the 'opentreeapi' user on GitHub) as third argument: '%s <repo-URL> <public-API-URL>'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong
 
# For now, let's just instruct the user how to do this manually. Point to
# fetch current hooks on this docstore repo
print """
***************************************************************

Please ensure the required webhook is in place on GitHub. You can
manage webhooks for this repo at:
    
    %s/settings/hooks
    
Find (or add) a webhook with these properties:
    Payload URL: %s/api/search/nudgeIndexOnUpdates
    Payload version: application/vnd.github.v3+json
    Events: push
    Active: true

***************************************************************
    """ %  (opentree_docstore_url, opentree_api_base_url)

#sys.exit(0)
     
# To do this automatically via the GitHub API, we need an OAuth token for bot
# user 'opentreeapi' on GitHub, with scope 'public_repo' and permission to
# manage hooks. This is stored in yet another sensitive file.
auth_token = open(oauth_token_file).readline().strip()
print "auth_token:"
print auth_token
print "opentree_docstore_url:"
print opentree_docstore_url
docstore_repo_name = opentree_docstore_url.rstrip('/').split('/').pop()
print "docstore_repo_name:"
print docstore_repo_name


# OR, we can simply prompt the user for their GitHub username and password.

r = requests.get('https://api.github.com/repos/OpenTreeOfLife/%s/hooks' % docstore_repo_name)
print r.url
print r.text
#
# Parse with json and look for a hook with these properties:
#   hook['name'] == "web" 
#   hook['active'] == "true" 
#   "push" in hook['events']
#   hook['config']['url'] == "{THIS_API_SERVER}/api/search/nudgeIndexOnUpdates"
# If found, maybe update it with PATCH. If not found, add it now.
