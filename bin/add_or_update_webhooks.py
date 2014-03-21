#!/usr/bin/env python

import json, requests, sys

# check args for repo-URL, Open Tree API URL, GitHub auth-key?
this_script = sys.argv[0]

if len(sys.argv) > 1:
	opentree_docstore_url = sys.argv[1]
else:
    print "Please specify the Open Tree doc-store URL as first argument: '%s <repo-URL> <public-API-URL>'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 2:
	opentree_api_base_url = sys.argv[2].rstrip("/").rstrip("/api/v1")
else:
    print "Please specify the Open Tree API public URL as second argument: '%s <repo-URL> <public-API-URL>'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong
 
# For now, let's just instruct the user how to do this manually. Point to
# fetch current hooks on this docstore repo
print """Please ensure the required webhook is in place on GitHub. You can
manage webhooks for this repo at:
    
    %s/settings/hooks
    
Find (or add) a webhook with these properties:
    Payload URL: %s/api/search/nudgeIndexOnUpdates
    Payload version: application/vnd.github.v3+json
    Events: push
    Active: true
    """ %  (opentree_docstore_url, opentree_api_base_url)

ignore_me = raw_input("Press RETURN to continue")
sys.exit(0)
     
# TODO: To do this automatically via the GitHub API, we'll need an OAuth token
# with scope 'public_repo' to add/edit webhooks on GitHub. This would probably
# use the 'opentreeapi' bot user on GitHub, probably with its userid:password
# read from (yet another) sensitive file.
# OR, we can simply prompt the user for their GitHub username and password.
#
## r = requests.get('https://api.github.com/repos/OpenTreeOfLife/phylesystem/hooks')
#
# Parse with json and look for a hook with these properties:
#   hook['name'] == "web" 
#   hook['active'] == "true" 
#   "push" in hook['events']
#   hook['config']['url'] == "{THIS_API_SERVER}/api/search/nudgeIndexOnUpdates"
# If found, maybe update it with PATCH. If not found, add it now.
