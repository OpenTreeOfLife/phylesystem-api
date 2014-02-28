from sh import git
import sh
import re
import os, sys
import locket
import functools
from locket import LockError
from subprocess import call
import api_utils
_LOG = api_utils.get_logger(__name__)

class MergeException(Exception):
    pass

class GitData(object):
    def __init__(self, dir):
        """Create a GitData object to interact with a Git repository

        Example:
        gd   = GitData(repo="/home/user/git/foo")

        Note that this requires write access to the
        git repository directory, so it can create a
        lockfile in the .git directory.

        """
        self.dir = dir
        if os.path.isdir(self.dir+"/.git"):
            self.repo=self.dir
        for file in 
        self.index={} #When/where should indexing happen?!
                
        self.lock_file     = "%s/.git/API_WRITE_LOCK" % self.repo
        self.lock_timeout  = 30
        self.lock          = locket.lock_file(self.lock_file, timeout=self.lock_timeout)


    def acquire_lock(self):
        "Acquire a lock on the git repository"
        _LOG.debug('Acquiring lock')
        self.lock.acquire()

    def release_lock(self):
        "Release a lock on the git repository"
        _LOG.debug('Releasing lock')
        self.lock.release()

    @preserve_cwd
    def current_branch(self):
        "Return the current branch name"
        os.chdir(self.repo)
        branch_name = git("symbolic-ref", "HEAD")
        return branch_name.replace('refs/heads/','').strip()

    def newest_study_id(self):
        "Return the numeric part of the newest study_id"
        os.chdir(self.repo)

        git.checkout("master")
        dirs = []
        # first we look for studies already in our master branch
        for f in os.listdir("study/"):
            if os.path.isdir("study/%s" % f):
                # ignore alphabetic prefix, o = created by opentree API
                if f[0].isalpha():
                    dirs.append(int(f[1:]))
                else:
                    dirs.append(int(f))

        # next we must look at local branch names for new studies
        # without --no-color we get terminal color codes in the branch output
        branches = git.branch("--no-color")
        branches = [ b.strip() for b in branches ]
        for b in branches:
            mo = re.match(".+_o(\d+)",b)
            if mo:
                dirs.append(int(mo.group(1)))

        dirs.sort()
        return dirs[-1]

    def fetch_study(self, study_id):
        """Return the contents of the given study_id

        If the study_id does not exist, it returns the empty string.
        """
        study_filename = "%s/study/%s/%s.json" % (self.repo, study_id, study_id)
        try:
            file = open(study_filename, 'r')
        except:
            return ''
        return file.read()

    @preserve_cwd
    def branch_exists(self, branch):
        """Returns true or false depending on if a branch exists"""
        os.chdir(self.repo)
        try:
            git(("rev-parse",branch))
        except sh.ErrorReturnCode:
            return False
        return True

    @preserve_cwd
    def remove_study(self,study_id, branch, author="OpenTree API <api@opentreeoflife.org>"):
        """Remove a study

        Given a study_id, branch and optionally an
        author, remove a study on the given branch
        and attribute the commit to author.

        Returns the SHA of the commit on branch.

        """
        os.chdir(self.repo)

        study_dir      = "study/%s" % study_id
        study_filename = "%s/%s.json" % (study_dir, study_id)

        if self.branch_exists(branch):
            git.checkout(branch)
            if not os.path.isdir(study_dir):
                # branch already exists locally with study removed
                # so just return the commit SHA
                return git("rev-parse","HEAD").strip()
        else:
            # Create this new branch off of master, NOT the currently-checked out branch!
            git.checkout("master")
            git.checkout("-b",branch)

        git.rm("-rf", study_dir)

        git.commit(author=author, message="Delete Study #%s via OpenTree API" % study_id)

        new_sha = git("rev-parse","HEAD")

        return new_sha.strip()

    @preserve_cwd
    def write_study(self,study_id, content, branch, author="OpenTree API <api@opentreeoflife.org>"):
        """Write a study

        Given a study_id, content, branch and
        optionally an author, write a study on the
        given branch and attribute the commit to
        author. If the branch does not yet exist,
        it will be created. If the study is being
        created, it's containing directory will be
        created as well.

        Returns the SHA of the new commit on branch.

        """
        os.chdir(self.repo)

        # If there are uncommitted changes to our repo, stash them so this commit can proceed
        git.stash()

        if self.branch_exists(branch):
            git.checkout(branch)
        else:
            # Create this new branch off of master, NOT the currently-checked out branch!
            git.checkout("master")
            git.checkout("-b",branch)

        study_dir      = "study/%s" % study_id #TODO what if more funky ids
        study_filename = "%s/%s.json" % (study_dir, study_id)

        # create a study directory if this is a new study
        if not os.path.isdir(study_dir):
            os.mkdir(study_dir)

        file = open(study_filename, 'w') #should be a move in here
        file.write(content) #Should be outside of lock
        file.close()

        git.add(study_filename)

        git.commit(author=author, message="Update Study #%s via OpenTree API" % study_id, _in='') #TODO use _in to avoid waiting for authorization?

        new_sha = git("rev-parse","HEAD")

        return new_sha.strip()

    @preserve_cwd
    def merge(self, branch, base_branch="master"):
        """
        Merge the the given WIP branch to master (or base_branch, if specified)

        If the merge fails, the merge will be aborted
        and then a MergeException will be thrown. The
        message of the MergeException will be the
        "git status" output, so details about merge
        conflicts can be determined.

        """

        os.chdir(self.repo)

        current_branch = self.current_branch()
        if current_branch != base_branch:
            git.checkout(base_branch)

        # Always create a merge commit, even if we could fast forward, so we know
        # when merges occured
        try:
            merge_output = git.merge("--no-ff", branch)
        except sh.ErrorReturnCode:
            # attempt to reset things so other operations can
            # continue
            output = git.status()
            git.merge("--abort")

            # re-raise the exception so other code can decide
            # what to do with it
            raise MergeException(output)

        # the merge succeeded, so remove the local WIP branch
        git.branch("-d", branch)

        new_sha      = git("rev-parse","HEAD")
        return new_sha.strip()

    @preserve_cwd
    def delete_remote_branch(self, remote, branch, env={}):
        "Delete a remote branch"
        # deleting a branch is the same as
        # git push remote :branch
        self.push(remote, env, ":%s" % branch)

    @preserve_cwd
    def push(self, remote, env={}, branch=None):
        """
        Push a branch to a given remote

        Given a remote, env and branch, push branch
        to remote and add the environment variables
        in the env dict to the environment of the
        "git push" command.

        If no branch is given, the current branch
        will be used.

        The ability to specify env is so that PKEY
        and GIT_SSH can be specified so Git can use
        different SSH credentials than the current
        user (i.e. deploy keys for Github). If PKEY
        is not defined, the environment will not be
        over-ridden.

        """
        os.chdir(self.repo)

        if branch:
            branch_to_push = branch
        else:
            branch_to_push = self.current_branch()

        # if there is no PKEY, we don't need to override env
        # We are explicit about what we are pushing, since the default behavior
        # is different in different versions of Git and/or by configuration
        if env["PKEY"]:
            new_env = os.environ.copy()
            new_env.update(env)
            git.push(remote, branch_to_push, _env=new_env)
        else:
            git.push(remote, branch_to_push)

    @preserve_cwd
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
        os.chdir(self.repo)
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
            git.pull(remote, branch_to_pull, _env=new_env)
        else:
            git.pull(remote, branch_to_pull)

        new_sha      = git("rev-parse","HEAD")
        return new_sha.strip()
