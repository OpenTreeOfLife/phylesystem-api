#!/usr/bin/env python

import json, requests, sys

# check args for repo-URL, Open Tree API URL, GitHub auth-key?
this_script = sys.argv[0]

if len(sys.argv) > 1:
	opentree_docstore_url = sys.argv[1]
else:
    print "Please specify the Open Tree doc-store URL as first argument: '%s <repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 2:
	opentree_api_base_url = sys.argv[2].rstrip("/").rstrip("/api/v1")
else:
    print "Please specify the Open Tree API public URL as second argument: '%s <repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong
 
if len(sys.argv) > 3:
	oauth_token_file = sys.argv[3]
else:
    oauth_token_file = None
 
# To do this automatically via the GitHub API, we need an OAuth token for bot
# user 'opentreeapi' on GitHub, with scope 'public_repo' and permission to
# manage hooks. This is stored in yet another sensitive file.
if oauth_token_file:
    auth_token = open(oauth_token_file).readline().strip()
else:
    auth_token = '00000000000000000000000000'  # doomed to fail

# Alternately, we could prompt the user for their GitHub username and password...

docstore_repo_name = opentree_docstore_url.rstrip('/').split('/').pop()

r = requests.get('https://api.github.com/repos/OpenTreeOfLife/%s/hooks' % docstore_repo_name,
                 headers={"Authorization": ("token %s" % auth_token)})
hooks_info = json.loads(r.text)
print('---------')
print(r.text)
print('---------')
print(hooks_info)
print('---------')
# look for an existing hook that will do the job...
found_matching_webhook = False
for hook in hooks_info:
    if (hook.get('name') == "web" and 
        hook.get('active') == True and
        hook.get('events') and ("push" in hook['events']) and
        hook.get('config') and (hook['config']['url'] == "%s/api/search/nudgeIndexOnUpdates" % opentree_api_base_url)
    ):
        found_matching_webhook = True
        
if found_matching_webhook:
    print "Found a matching webhook in the docstore repo!"
    sys.exit(0)
else:
    print "Adding a webhook to the docstore repo..."
    hook_settings = {
        "name": "web",
        "active": True,
        "events": [
            "push"
        ],
        "config": {
            "url": ("%s/api/search/nudgeIndexOnUpdates" % opentree_api_base_url),
            "content_type": "json"
        }
    }

    r = requests.post('https://api.github.com/repos/OpenTreeOfLife/%s/hooks' % docstore_repo_name,
                      headers={"Authorization": ("token %s" % auth_token), 
                               "Content-type": "aplication/json"}, 
                      data=json.dumps(hook_settings))
    if r.status_code == 201:  # 201=Created
        print "Hook added successfully!"
    else:
        print "Failed to add webhook! API sent this response:"
        print r.url
        print r.text
        # fall back to our prompt for manual action
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

sys.exit(0)
