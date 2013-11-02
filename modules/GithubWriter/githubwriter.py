from github import Github
import os
import sys

class GithubWriter(object):
    "Convenience class for interacting with the Github API from the OTOL API"
    def __init__(self, oauth='', org="OpenTreeOfLife", repo="testing", **kwargs):
        if not oauth:
            oauth = os.getenv('GITHUB_OAUTH_TOKEN', 'invalid')
        if oauth == 'invalid':
            print "Could not find OAUTH token!"
        self.oauth = oauth
        self.gh    = Github(oauth)

        self.org   = self.gh.get_organization(org)
        self.repo  = self.org.get_repo(repo)

    def create_blob(self, content, encoding):
        return self.gh.create_git_blob(content, encoding)

    def get_latest_sha(self, branch="master"):
        # i.e. curl https://api.github.com/repos/OpenTreeOfLife/api.opentreeoflife.org/git/refs/heads/master
        # we need to get the latest sha on master to use as our initial sha1 of our new branch

        ref = self.repo.get_git_ref("heads/%s" % branch)
        sha        = ref.object.sha
        return sha

    def get_tree_sha(self, commit_sha):
        "Get the Tree SHA of a given commit SHA"
        commit = self.gh.get_git_commit(commit_sha)
        return commit.tree.sha

    def create_branch(self, branch, sha):
        "Create a branch on Github from a given name and SHA"
        # we must always use heads/branch_name to talk about branches via the API
        ref = "heads/%s" % branch

        # create a new "Git Reference" (i.e. branch) from the given sha
        return self.gh.create_git_ref(ref,sha)

    # http://developer.github.com/v3/git/trees/#create-a-tree
    def create_tree(self, tree):
        self.gh.create_git_tree(tree)
