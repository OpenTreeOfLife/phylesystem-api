from nose       import with_setup
from nose.tools import *
import os
import sys
from gitdata import GitData
import simplejson as json

def test_basic():
    gd = GitData(repo="./treenexus")

    study_id = 438
    study_nexson = gd.fetch_study(study_id)
    valid = 1
    try:
        json.loads(study_nexson)
    except:
        valid = 0
    assert valid, "fetch_study(%s) returned valid JSON" % study_id

test_basic()
