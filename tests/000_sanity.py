from nose       import with_setup
from nose.tools import assert_equals

import otol_api

def setup_module(module):
    ...

def teardown_module(module):
    ...

def setup_test():
    ...

def teardown_test():
    ...

@with_setup(setup_test, teardown_test)
def test_basic_api_call():
    assert_equals( 1, 1 )
