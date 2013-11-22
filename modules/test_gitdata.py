from nose       import with_setup
from nose.tools import *
import os
import sys
from gitdata import GitData
import simplejson as json

def test_fetch():
    gd = GitData(repo="./treenexus")

    study_id = 438
    study_nexson = gd.fetch_study(study_id)
    valid = 1
    try:
        json.loads(study_nexson)
    except:
        valid = 0
    assert valid, "fetch_study(%s) returned valid JSON" % study_id

def test_write():
    gd = GitData(repo="./treenexus")
    author   = "John Doe <john@doe.com>"
    content  = '{"foo":"bar"}'
    study_id = 999
    branch   = "johndoe_study_%s" % study_id
    new_sha  = gd.write_study(study_id,content,branch,author)
    assert new_sha != "", "new_sha is non-empty"

def test_branch_exists():
    gd = GitData(repo="./treenexus")
    exists = gd.branch_exists("nothisdoesnotexist")
    assert exists == 0, "branch does not exist"

    exists = gd.branch_exists("master")
    assert exists, "master branch exists"

test_branch_exists()
test_fetch()
test_write()
