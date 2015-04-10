from peyotl.phylesystem.git_actions import PhylesystemGitAction
from sh import git
import os
import api_utils

class GitData(PhylesystemGitAction):
    def __init__(self, repo, **kwargs):
        PhylesystemGitAction.__init__(self, repo, **kwargs)
    def delete_remote_branch(self, remote, branch, env={}):
        "Delete a remote branch"
        # deleting a branch is the same as
        # git push remote :branch
        self.push(remote, env, ":%s" % branch)

    def pull(self, remote, env={}, branch=None):
        """
        Pull a branch from a given remote

        Given a remote, env and branch, pull branch
        from remote and add the environment variables
        in the env dict to the environment of the
        "git pull" command.

        If no branch is given, the current branch
        will be updated.
        """
        if branch:
            branch_to_pull = branch
        else:
            branch_to_pull = self.current_branch()

        # if there is no PKEY, we don't need to override env
        # We are explicit about what we are pushing, since the default behavior
        # is different in different versions of Git and/or by configuration
        if env["PKEY"]:
            new_env = os.environ.copy()
            new_env.update(env)
            git(self.gitdir, self.gitwd, "pull", remote, "{}:{}".format(branch_to_pull,branch_to_pull), _env=new_env)
        else:
            git(self.gitdir, self.gitwd, "pull", remote, "{}:{}".format(branch_to_pull,branch_to_pull))

        new_sha      = git(self.gitdir, self.gitwd, "rev-parse","HEAD")
        return new_sha.strip()


