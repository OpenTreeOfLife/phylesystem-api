from sh import git
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

    def write_study(self,study_id, content, author="OpenTree API <api@opentreeoflife.org>"):
        study_filename = "study/%s/%s.json" % (study_id, study_id)
        # TODO: create the containing directory if we are writing a new study
        file = open("%s/%s" % (self.repo,study_filename), 'w')
        file.write(content)
        file.close()

        orig_cwd = os.getcwd()
        os.chdir(self.repo)

        git.add(study_filename)
        git.commit(author=author, message="Update Study #%s via OpenTree API" % study_id)

        os.chdir(orig_cwd)

    def push(self):
        # TODO: set up GIT_SSH to use proper deployment key for repo
        git.push()
