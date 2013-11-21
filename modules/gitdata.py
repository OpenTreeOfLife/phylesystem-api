
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
