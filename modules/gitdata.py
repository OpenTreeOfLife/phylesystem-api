from sh import git
import sh
import re
import os, sys
import locket
from locket import LockError

class MergeException(Exception):
    pass

class GitData(object):
    def __init__(self, repo):
        self.repo = repo

        self.lock_file     = "%s/.git/API_WRITE_LOCK" % self.repo
        self.lock_timeout  = 30
        self.lock          = locket.lock_file(self.lock_file, timeout=self.lock_timeout)

    def preserve_cwd(function):
        def decorator(*args, **kwargs):
            cwd = os.getcwd()
            try:
                return function(*args, **kwargs)
            finally:
                os.chdir(cwd)
        return decorator

    def acquire_lock(self):
        self.lock.acquire()

    def release_lock(self):
        self.lock.release()

    @preserve_cwd
    def current_branch(self):
        os.chdir(self.repo)
        branch_name = git("symbolic-ref", "HEAD")
        return branch_name.replace('refs/heads/','').strip()

    def newest_study_id(self):
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
        study_filename = "%s/study/%s/%s.json" % (self.repo, study_id, study_id)
        try:
            file = open(study_filename, 'r')
        except:
            return ''
        return file.read()

    @preserve_cwd
    def branch_exists(self, branch):
        """Returns true or false depending on if a branch exists"""
        try:
            git(("rev-parse",branch))
        except sh.ErrorReturnCode:
            return False
        return True

    @preserve_cwd
    def remove_study(self,study_id, branch, author="OpenTree API <api@opentreeoflife.org>"):
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
        os.chdir(self.repo)

        # If there are uncommitted changes to our repo, stash them so this commit can proceed
        git.stash()

        if self.branch_exists(branch):
            git.checkout(branch)
        else:
            # Create this new branch off of master, NOT the currently-checked out branch!
            git.checkout("master")
            git.checkout("-b",branch)

        study_dir      = "study/%s" % study_id
        study_filename = "%s/%s.json" % (study_dir, study_id)

        # create a study directory if this is a new study
        if not os.path.isdir(study_dir):
            os.mkdir(study_dir)

        file = open(study_filename, 'w')
        file.write(content)
        file.close()

        git.add(study_filename)

        git.commit(author=author, message="Update Study #%s via OpenTree API" % study_id)

        new_sha = git("rev-parse","HEAD")

        return new_sha.strip()

    @preserve_cwd
    def merge(self, branch, base_branch="master"):
        "Merge the the given WIP branch to master (or base_branch, if specified)"
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

    @preserve_cwd
    def push(self, remote, env={}):
        os.chdir(self.repo)

        current_branch = self.current_branch()

        # if there is no PKEY, we don't need to override env
        # We are explicit about what we are pushing, since the default behavior
        # is different in different versions of Git and/or by configuration
        if env["PKEY"]:
            new_env = os.environ.copy()
            new_env.update(env)
            git.push(remote, current_branch, _env=new_env)
        else:
            git.push(remote, current_branch)

