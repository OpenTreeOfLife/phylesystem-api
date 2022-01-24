import unittest
import os
import sys
import time
from phylesystem_api.gitdata import GitData, MergeException
import simplejson as json
from sh import git
from ConfigParser import SafeConfigParser

class TestGitData(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        conf = SafeConfigParser(allow_no_value=True)
        if os.path.isfile("../private/localconfig"):
            conf.read("../private/localconfig")
        else:
            conf.read("../private/config")

        self.repo = conf.get("apis","repo_path")
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

    def test_merge(self):
        def cleanup_merge():
            git.checkout("master")
            # if something failed, the branch might still exist
            if self.gd.branch_exists("to_merge_1"):
                git.branch("-D", "to_merge_1")

            git.branch("-D", "base_branch")

        self.addCleanup(cleanup_merge)

        git.checkout("-b", "to_merge_1")
        git.checkout("-b", "base_branch")

        file = open("foo.txt", "w")
        file.write("ABC\n")
        file.close()

        git.add("foo.txt")

        git.commit("-m","Test commit")

        new_sha = self.gd.merge("to_merge_1", "base_branch")

        self.assertTrue( new_sha != "", "new_sha=%s is non-empty" % new_sha)
        self.assertEqual(len(new_sha), 40, "SHA is 40 chars")

        self.assertTrue(True, "Merge succeeded")

    def test_merge_conflict(self):
        def cleanup_merge_conflict():
            git.checkout("master")
            # if something failed, the branch might still exist
            if self.gd.branch_exists("to_merge_1"):
                git.branch("-D", "to_merge_1")

            if self.gd.branch_exists("to_merge_2"):
                git.branch("-D", "to_merge_2")

        self.addCleanup(cleanup_merge_conflict)

        git.checkout("master")
        git.checkout("-b", "to_merge_1")

        file = open("foo.txt", "w")
        file.write("ABC\n")
        file.close()

        git.add("foo.txt")
        git.commit("-m","Test commit")

        git.checkout("master")

        git.checkout("-b", "to_merge_2")

        file = open("foo.txt", "w")
        file.write("XYZ\n")
        file.close()

        git.add("foo.txt")
        git.commit("-m","Test commit")

        self.assertRaises(MergeException, lambda:  self.gd.merge("to_merge_1", "to_merge_2") )

    def test_current_branch(self):
        git.checkout(self.testing_branch_name)
        branch_name = self.gd.current_branch()
        self.assertEqual(branch_name, self.testing_branch_name)

    def test_fetch(self):
        study_id = 438
        study_nexson, head_sha = self.gd.fetch_study(study_id)
        valid = 1
        try:
            json.loads(study_nexson)
        except:
            valid = 0
        self.assertTrue( valid, "fetch_study(%s) returned valid JSON" % study_id)

    def test_write(self):
        def cleanup_write():
            git.checkout("master")
            git.branch("-D","johndoe_study_9998")
            git.branch("-D","johndoe_study_9999")

        self.addCleanup(cleanup_write)

        author   = "John Doe <john@doe.com>"
        content  = '{"foo":"bar"}'
        study_id = 9999
        branch   = "johndoe_study_%s" % study_id
        new_sha  = self.gd.write_study(study_id,content,branch,author)
        self.assertTrue( new_sha != "", "new_sha is non-empty")
        self.assertEqual(len(new_sha), 40, "SHA is 40 chars")
        fetched_content, head_sha = self.gd.fetch_study(9999)
        self.assertEqual( content, fetched_content, "correct content found via fetch_study")

        author   = "John Doe <john@doe.com>"
        content  = '{"foo2":"bar2"}'
        study_id = 9998
        branch   = "johndoe_study_%s" % study_id
        new_sha  = self.gd.write_study(study_id,content,branch,author)

        merge_base_sha1 = git("merge-base","johndoe_study_9999","johndoe_study_9998").strip()

        master_sha1     = git("rev-parse","master").strip()

        self.assertEqual(master_sha1, merge_base_sha1, "Verify that writing new study branches from master and not the current branch")

    def test_remove(self):
        def cleanup_remove():
            git.checkout("master")
            git.branch("-D","johndoe_study_777")

        self.addCleanup(cleanup_remove)

        author   = "John Doe <john@doe.com>"
        content  = '{"foo2":"bar3"}'
        study_id = 777
        branch   = "johndoe_study_%s" % study_id

        new_sha  = self.gd.remove_study(study_id, branch, author)
        self.assertTrue( new_sha != "", "new_sha is non-empty")
        self.assertEqual(len(new_sha), 40, "SHA is 40 chars")

        deleted_study_dir = "%s/study/%s" % (self.repo, study_id)
        self.assertFalse( os.path.exists(deleted_study_dir), "%s should no longer exist" % deleted_study_dir )


    def test_branch_exists(self):
        exists = self.gd.branch_exists("nothisdoesnotexist")
        self.assertTrue( exists == 0, "branch does not exist")

        branch_name = self.testing_branch_name

        exists = self.gd.branch_exists(branch_name)
        self.assertTrue( exists, "%s branch exists" % branch_name)
    def test_newest_study_id(self):
        def cleanup_newest():
            git.checkout("master")
            git.branch("-D","leto_study_o9999")

        self.addCleanup(cleanup_newest)

        git.checkout("master")
        newest_id = self.gd.newest_study_id()

        self.assertGreaterEqual( newest_id, 2600)

        git.checkout("-b", "leto_study_o9999")

        newest_id = self.gd.newest_study_id()
        self.assertGreaterEqual( newest_id, 9999 )

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
