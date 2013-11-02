from nose       import with_setup
from nose.tools import *
import os
import sys

from githubwriter import GithubWriter

def test_basic():
    gw  = GithubWriter(repo="api.opentreeoflife.org")

    assert_is_instance(gw, GithubWriter)

    sha = gw.get_latest_sha()
    assert_equals( len(sha) , 40, 'Got a reasonable looking sha back:%s ' % sha)

    assert_false( gw.branch_exists("really_please_dont_exist") )

    assert_true( gw.branch_exists("master") )

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
