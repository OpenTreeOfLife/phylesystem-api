import unittest
import os
import sys
import time
from gitdata import GitData
import simplejson as json
from sh import git

class TestGitData(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.repo = "/Users/jleto/git/opentree/treenexus"
        self.gd   = GitData(repo=self.repo)
        self.orig_cwd = os.getcwd()

        # go into our data repo
        os.chdir(self.repo)

        self.testing_branch_name = "testing_%d" % int(time.time())
        # create the branch
        git.checkout("-b", self.testing_branch_name)

        # start all tests on the master branch
        git.checkout("master")

    @classmethod
    def tearDownClass(self):

        git.branch("-D",self.testing_branch_name)

    def test_current_branch(self):
        git.checkout(self.testing_branch_name)
        branch_name = self.gd.current_branch()
        self.assertEqual(branch_name, self.testing_branch_name)

    def test_fetch(self):
        study_id = 438
        study_nexson = self.gd.fetch_study(study_id)
        valid = 1
        try:
            json.loads(study_nexson)
        except:
            valid = 0
        self.assertTrue( valid, "fetch_study(%s) returned valid JSON" % study_id)

    def test_write(self):
        def cleanup_write():
            git.checkout("master")
            git.branch("-D","johndoe_study_9999")

        self.addCleanup(cleanup_write)

        author   = "John Doe <john@doe.com>"
        content  = '{"foo":"bar"}'
        study_id = 9999
        branch   = "johndoe_study_%s" % study_id
        new_sha  = self.gd.write_study(study_id,content,branch,author)
        self.assertTrue( new_sha != "", "new_sha is non-empty")
        self.assertEqual(len(new_sha), 40, "SHA is 40 chars")


    def test_branch_exists(self):
        exists = self.gd.branch_exists("nothisdoesnotexist")
        self.assertTrue( exists == 0, "branch does not exist")

        branch_name = self.testing_branch_name

        exists = self.gd.branch_exists(branch_name)
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
