from sh import git
import sh
import os, sys

class GitData(object):
    def __init__(self, repo):
        self.repo = repo

    def preserve_cwd(function):
        def decorator(*args, **kwargs):
            cwd = os.getcwd()
            try:
                return function(*args, **kwargs)
            finally:
                os.chdir(cwd)
        return decorator

    @preserve_cwd
    def current_branch(self):
        os.chdir(self.repo)
        branch_name = git("symbolic-ref", "--short", "HEAD")
        return branch_name.strip()

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
        else:
            git.checkout("-b",branch)

        git.rm("-rf", study_dir)

        git.commit(author=author, message="Delete Study #%s via OpenTree API" % study_id)

        new_sha = git("rev-parse","HEAD")

        return new_sha.strip()

    @preserve_cwd
    def write_study(self,study_id, content, branch, author="OpenTree API <api@opentreeoflife.org>"):
        os.chdir(self.repo)

        study_dir      = "study/%s" % study_id
        study_filename = "%s/%s.json" % (study_dir, study_id)

        # create a study directory if this is a new study
        if not os.path.isdir(study_dir):
            os.mkdir(study_dir)

        file = open(study_filename, 'w')
        file.write(content)
        file.close()

        if self.branch_exists(branch):
            git.checkout(branch)
        else:
            git.checkout("-b",branch)

        git.add(study_filename)

        git.commit(author=author, message="Update Study #%s via OpenTree API" % study_id)

        new_sha = git("rev-parse","HEAD")

        return new_sha.strip()

    @preserve_cwd
    def push(self):
        os.chdir(self.repo)
        # TODO: set up GIT_SSH to use proper deployment key for repo

        current_branch = self.current_branch()
        # be explicit about what we are pushing, since the default behavior
        # is different in different versions of Git and/or by configuration
        git.push("origin", current_branch)

