import unittest
import os
import sys
from gitdata import GitData
import simplejson as json

class TestGitData(unittest.TestCase):
    def setUp(self):
        self.repo = "/Users/jleto/git/opentree/treenexus"

    def test_fetch(self):
        gd = GitData(repo=self.repo)

        study_id = 438
        study_nexson = gd.fetch_study(study_id)
        valid = 1
        try:
            json.loads(study_nexson)
        except:
            valid = 0
        self.assertTrue( valid, "fetch_study(%s) returned valid JSON" % study_id)

    def test_write(self):
        gd = GitData(repo=self.repo)
        author   = "John Doe <john@doe.com>"
        content  = '{"foo":"bar"}'
        study_id = 9999
        branch   = "johndoe_study_%s" % study_id
        new_sha  = gd.write_study(study_id,content,branch,author)
        self.assertTrue( new_sha != "", "new_sha is non-empty")

    def test_branch_exists(self):
        gd = GitData(repo=self.repo)
        exists = gd.branch_exists("nothisdoesnotexist")
        self.assertTrue( exists == 0, "branch does not exist")

        branch_name = "only_here"
        exists = gd.branch_exists(branch_name)
        self.assertTrue( exists, "%s branch exists" % branch_name)

def suite():
    loader = unittest.TestLoader()
    testsuite = loader.loadTestsFromTestCase(TestGitData)
    return testsuite

def test_main():
    testsuite = suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity=2)
    result = runner.run(testsuite)

if __name__ == "__main__":
    test_main()
