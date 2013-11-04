from github import Github
import github
import os
import sys

github.enable_console_debug_logging()

class GithubWriter(object):
    "Convenience class for interacting with the Github API from the OTOL API"
    def __init__(self, oauth='', org="OpenTreeOfLife", repo="testing", **kwargs):
        if not oauth:
            oauth = os.getenv('GITHUB_OAUTH_TOKEN', 'invalid')
        if oauth == 'invalid':
            print "Could not find OAUTH token!"
        self.oauth = oauth
        self.gh    = Github(oauth)

        if kwargs["user"]:
            self.user = self.gh.get_user(kwargs["user"])
            self.repo  = self.user.get_repo(repo)
        else:
            self.org   = self.gh.get_organization(org)
            self.repo  = self.org.get_repo(repo)

    def create_blob(self, content, encoding):
        return self.repo.create_git_blob(content, encoding)

    def get_commit(self,sha):
        return self.repo.get_git_commit(sha)

    def get_ref(self, sha, branch="master"):
        return self.repo.get_git_ref("heads/%s" % branch)

    def get_latest_sha(self, branch="master"):
        # i.e. curl https://api.github.com/repos/OpenTreeOfLife/api.opentreeoflife.org/git/refs/heads/master
        # we need to get the latest sha on master to use as our initial sha1 of our new branch

        ref = self.repo.get_git_ref("heads/%s" % branch)
        sha        = ref.object.sha
        return sha

    def branch_exists(self, branch):
        "Return true if a branch exists, false otherwise"
        try:
            ref = self.repo.get_git_ref("heads/%s" % branch)
        except github.UnknownObjectException, e:
            return 0

        return 1

    def get_tree(self, commit_sha):
        "Get the Tree of a given commit SHA"
        commit = self.repo.get_git_commit(commit_sha)
        return commit.tree

    def create_branch(self, branch, sha):
        "Create a branch on Github from a given name and SHA"
        # we must always use heads/branch_name to talk about branches via the API
        ref = "heads/%s" % branch

        # create a new "Git Reference" (i.e. branch) from the given sha
        return self.repo.create_git_ref(ref,sha)

    # http://developer.github.com/v3/git/trees/#create-a-tree
    def create_tree(self, tree, base_tree):
        return self.repo.create_git_tree(tree, base_tree)

    def create_commit(self, message, tree, parents):
        return self.repo.create_git_commit(message, tree, parents)
