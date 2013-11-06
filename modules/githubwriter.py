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

        if "user" in kwargs:
            self.user = self.gh.get_user(kwargs["user"])
            self.repo  = self.user.get_repo(repo)
        else:
            self.org   = self.gh.get_organization(org)
            self.repo  = self.org.get_repo(repo)

    def retry(f):
        def inner(*args, **kwargs):
            try:
                return f(*args,**kwargs)
            except github.GithubException, e:
                if e.status == 502:
                    # We got a bad gateway timeout, which happens occasionally
                    # Retry one more time
                    return f(*args,**kwargs)
                else:
                    raise
        return inner

    @retry
    def create_blob(self, content, encoding):
        "Create a git blob"
        return self.repo.create_git_blob(content, encoding)

    @retry
    def get_commit(self,sha):
        "Get the Git commit associated with a given SHA"
        return self.repo.get_git_commit(sha)

    @retry
    def get_ref(self, branch="master"):
        "Get a git reference from a given branch, or master"
        return self.repo.get_git_ref("heads/%s" % branch)

    @retry
    def get_latest_sha(self, branch="master"):
        "Return the latest commit SHA on a given branch. Assumes master if no branch is given"

        # i.e. curl https://api.github.com/repos/OpenTreeOfLife/api.opentreeoflife.org/git/refs/heads/master
        # we need to get the latest sha on master to use as our initial sha1 of our new branch

        ref = self.repo.get_git_ref("heads/%s" % branch)
        sha = ref.object.sha
        return sha

    @retry
    def branch_exists(self, branch):
        "Return true if a branch exists, false otherwise"
        try:
            ref = self.repo.get_git_ref("heads/%s" % branch)
        except github.UnknownObjectException, e:
            return 0

        return 1

    @retry
    def get_tree(self, commit_sha):
        "Get the Tree of a given commit SHA"
        commit = self.repo.get_git_commit(commit_sha)
        return commit.tree

    @retry
    def create_branch(self, branch, sha):
        "Create a branch on Github from a given name and SHA"
        # we must use refs/heads/branch_name when creating branches
        ref = "refs/heads/%s" % branch

        # create a new "Git Reference" (i.e. branch) from the given sha
        return self.repo.create_git_ref(ref,sha)

    @retry
    def create_tree(self, tree, base_tree):
        """Create a Git Tree
See http://developer.github.com/v3/git/trees/#create-a-tree for more details
"""
        return self.repo.create_git_tree(tree, base_tree)

    @retry
    def create_commit(self, message, tree, parents):
        """Create a Git Commit via the Github API"""
        return self.repo.create_git_commit(message, tree, parents)

    def create_or_update_file(self, filename, content, commit_message, branch="master"):
        """
Given a filename, content, commit message and branch, create
or update the file with the given content on the given
branch.

If no branch is given, assume master. If a branch is given,
update/create the file in a commit on the given branch.
        """
        branch_exists = self.branch_exists(branch)

        if branch_exists:
            sha   = self.get_latest_sha(branch)
        else:
            sha   = self.get_latest_sha()

        base_tree = self.get_tree(sha)
        blob      = self.create_blob(content, "utf-8")

        new_tree  = self.create_tree(
             tree = [github.InputGitTreeElement(
                path = filename,
                mode = '100644', # plain files
                type = 'blob',
                sha  = blob.sha,
            )],
            base_tree = base_tree,
        )

        new_commit = self.create_commit(
            message = commit_message,
            tree    = new_tree,
            parents = [ self.get_commit(sha) ],
        )

        if branch_exists:
            ref_to_update = self.get_ref(branch)
        else:
            ref_to_update = self.create_branch(branch, new_commit.sha )

        # Update the given branch HEAD reference to point to the newest commit
        ref_to_update.edit(sha=new_commit.sha, force=False)
