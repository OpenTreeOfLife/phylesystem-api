#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import sys

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/merge/v1/master/master'

data = {
         'auth_token': 'bogus'
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=400):
    sys.exit(0)
sys.exit(1)
