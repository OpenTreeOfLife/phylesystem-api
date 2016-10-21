#!/usr/bin/env python

import json, requests, sys

# check args for repo-URL, Open Tree API URL, GitHub auth-key?
this_script = sys.argv[0]

if len(sys.argv) > 1:
    opentree_docstore_url = sys.argv[1]
else:
    print "Please specify the Open Tree doc-store URL as first argument: '%s <studies-repo-URL> <amendments-repo-URL> <illustrations-repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 2:
    amendments_repo_url = sys.argv[2]
else:
    print "Please specify the taxonomic-amendment repo URL as second argument: '%s <studies-repo-URL> <amendments-repo-URL> <illustrations-repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 3:
    illustrations_repo_url = sys.argv[3]
else:
    print "Please specify the tree-illustrations repo URL as third argument: '%s <studies-repo-URL> <amendments-repo-URL> <illustrations-repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 4:
    opentree_api_base_url = sys.argv[4].rstrip("/")
    nudge_study_index_url = "%s/phylesystem/search/nudgeStudyIndexOnUpdates" % opentree_api_base_url
    nudge_taxon_index_url = "%s/phylesystem/search/nudgeTaxonIndexOnUpdates" % opentree_api_base_url
    nudge_illustration_index_url = "%s/phylesystem/search/nudgeIllustrationIndexOnUpdates" % opentree_api_base_url
else:
    print "Please specify the Open Tree API public URL as fourth argument: '%s <studies-repo-URL> <amendments-repo-URL> <illustrations-repo-URL> <public-API-URL> [<GitHub-OAuth-token-file>]'" % (this_script,)
    sys.exit(1)  # signal to the caller that something went wrong

if len(sys.argv) > 5:
    oauth_token_file = sys.argv[5]
else:
    oauth_token_file = None

# To do this automatically via the GitHub API, we need an OAuth token for bot
# user 'opentreeapi' on GitHub, with scope 'public_repo' and permission to
# manage hooks. This is stored in yet another sensitive file.
prompt_for_manual_webhooks = False
if oauth_token_file:
    auth_token = open(oauth_token_file).readline().strip()
else:
    prompt_for_manual_webhooks = True

# Alternately, we could prompt the user for their GitHub username and password...

def install_webhook(repo_url, nudge_index_url):
    docstore_repo_name = repo_url.rstrip('/').split('/').pop()
    webhook_url = 'https://api.github.com/repos/OpenTreeOfLife/%s/hooks' % docstore_repo_name
    r = requests.get(webhook_url,
                     headers={"Authorization": ("token %s" % auth_token)})
    try:
        hooks_info = json.loads(r.text)
    except:
        print '\nUnable to load webhook info (bad OAuth token?) [auth_token=%s]:' % auth_token 
        print 'Webhook URL: [%s]' % webhook_url
        print 'Webhook response:\n%s\n' % r.text.encode('utf-8')
        prompt_for_manual_webhooks = True
        return

    # look for an existing hook that will do the job...
    found_matching_webhook = False
    for hook in hooks_info:
        try:
            if (hook.get('name') == "web" and 
                hook.get('active') == True and
                hook.get('events') and ("push" in hook['events']) and
                hook.get('config') and (hook['config']['url'] == nudge_index_url)
            ):
                found_matching_webhook = True
        except:
            print 'Unexpected webhook response: ', r.text
            # Rather than failing outright, let's keep going with the manual prompt below
            prompt_for_manual_webhooks = True
            return

    if found_matching_webhook:
        print "Found a matching webhook in the docstore repo!"
        return
    else:
        print "Adding a webhook to the %s repo..." % docstore_repo_name
        hook_settings = {
            "name": "web",
            "active": True,
            "events": [
                "push"
            ],
            "config": {
                "url": nudge_index_url,
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
            prompt_for_manual_webhooks = True

if not(prompt_for_manual_webhooks):
    # try to install webhooks via GitHub API
    # N.B. this might fail, flipping prompt_for_manual_webhooks!
    install_webhook(opentree_docstore_url, nudge_study_index_url)
    install_webhook(amendments_repo_url, nudge_taxon_index_url)
    install_webhook(illustrations_repo_url, nudge_illustration_index_url)
    # N.B. that there's currently now index for illustrations, so it's a no-op

if prompt_for_manual_webhooks:
    # fall back to our prompts for manual action
    print """
    ***************************************************************

    Please ensure the required webhook for re-indexing studies is in place on
    GitHub. You can manage webhooks for this repo at:

        %s/settings/hooks

    Find (or add) a webhook with these properties:
        Payload URL: %s
        Payload version: application/vnd.github.v3+json
        Events: push
        Active: true

    ***************************************************************
        """ %  (opentree_docstore_url, nudge_study_index_url)

    print """
    Please ensure the required webhook for indexing new taxa (and other
    taxonomic amendments) is in place on GitHub. You can manage webhooks for
    this repo at:

        %s/settings/hooks

    Find (or add) a webhook with these properties:
        Payload URL: %s
        Payload version: application/vnd.github.v3+json
        Events: push
        Active: true

    ***************************************************************
        """ %  (amendments_repo_url, nudge_taxon_index_url)

    print """
    Please ensure the required webhook for re-indexing tree illustrations is in
    place on GitHub. You can manage webhooks for this repo at:

        %s/settings/hooks

    Find (or add) a webhook with these properties:
        Payload URL: %s
        Payload version: application/vnd.github.v3+json
        Events: push
        Active: true

    ***************************************************************
        """ %  (illustrations_repo_url, nudge_illustration_index_url)

sys.exit(0)
