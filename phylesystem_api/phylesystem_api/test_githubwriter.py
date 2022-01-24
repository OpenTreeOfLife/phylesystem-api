from nose import with_setup
from nose.tools import *
import os
import sys
import github

from phylesystem_api.githubwriter import GithubWriter

def test_basic():

    gw  = GithubWriter(user="leto",repo="testing")

    assert_is_instance(gw, GithubWriter)

    sha = gw.get_latest_sha()
    assert_equals( len(sha) , 40, 'Got a reasonable looking sha back:%s ' % sha)
    print("sha of master = %s" % sha)

    assert_false( gw.branch_exists("really_please_dont_exist") )

    assert_true( gw.branch_exists("master") )

    tree = gw.get_tree(sha)

    assert_equals( len(tree.sha) , 40, 'Got a reasonable looking sha back:%s ' % tree.sha)
    print("tree sha of master = %s" % tree.sha)

    blob = gw.create_blob("some other content", "utf-8")

    # Create a new Tree, which will be part of our new commit
    new_tree = gw.create_tree(
        tree = [github.InputGitTreeElement(
            path = "foo.json",
            mode = '100644',
            type = 'blob',
            sha  = blob.sha,
        )],
        base_tree = tree,
    )

    # Actually create the Git commit from our tree and parent commit
    new_commit = gw.create_commit(
        message = "test commit message",
        tree    = new_tree,
        parents = [ gw.get_commit(sha) ],
    )

    branch = gw.create_branch("testing_%d" % os.getpid(), new_commit.sha )

    # Update the branch to point to our new commit ref
    branch.edit(sha=new_commit.sha, force=False)


def test_advanced():
    gw  = GithubWriter(user="leto",repo="testing")

    gw.create_or_update_file("study/10/10.json",'{"foo10":"barzbag101010"}',"Update foo.json some more", "testing_126")

#test_basic()
test_advanced()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
