import unittest
import os
import sys
from gitdata import GitData
import simplejson as json

class TestGitData(unittest.TestCase):
    def test_fetch(self):
        gd = GitData(repo="./treenexus")

        study_id = 438
        study_nexson = gd.fetch_study(study_id)
        valid = 1
        try:
            json.loads(study_nexson)
        except:
            valid = 0
        self.assertTrue( valid, "fetch_study(%s) returned valid JSON" % study_id)

    def test_write(self):
        gd = GitData(repo="./treenexus")
        author   = "John Doe <john@doe.com>"
        content  = '{"foo":"bar"}'
        study_id = 9999
        branch   = "johndoe_study_%s" % study_id
        new_sha  = gd.write_study(study_id,content,branch,author)
        self.assertTrue( new_sha != "", "new_sha is non-empty")

    def test_branch_exists(self):
        gd = GitData(repo="./treenexus")
        exists = gd.branch_exists("nothisdoesnotexist")
        self.assertTrue( exists == 0, "branch does not exist")

        exists = gd.branch_exists("master")
        self.assertTrue( exists, "master branch exists")

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
