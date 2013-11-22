from sh import git
import sh
import os

class GitData(object):
    def __init__(self, repo):
        self.repo = repo

    def fetch_study(self, study_id):
        study_filename = "%s/study/%s/%s.json" % (self.repo, study_id, study_id)
        try:
            file = open(study_filename, 'r')
        except:
            return ''
        return file.read()

    def branch_exists(self, branch):
        try:
            git(("rev-parse",branch))
        except sh.ErrorReturnCode:
            return 0
        return 1

    def write_study(self,study_id, content, branch, author="OpenTree API <api@opentreeoflife.org>"):
        study_filename = "study/%s/%s.json" % (study_id, study_id)
        # TODO: create the containing directory if we are writing a new study
        file = open("%s/%s" % (self.repo,study_filename), 'w')
        file.write(content)
        file.close()

        orig_cwd = os.getcwd()
        os.chdir(self.repo)

        if self.branch_exists(branch):
            git.checkout(branch)
        else:
            git.checkout("-b",branch)

        git.add(study_filename)

        git.commit(author=author, message="Update Study #%s via OpenTree API" % study_id)

        new_sha = git("rev-parse","HEAD")

        os.chdir(orig_cwd)
        return new_sha

    def push(self):
        # TODO: set up GIT_SSH to use proper deployment key for repo
        git.push()
