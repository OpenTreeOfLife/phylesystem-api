#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/9'
data = { 'nexson': {'bogus' : 5},
         'auth_token': 'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token')

}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data,
                         expected_status=400):
    sys.exit(0)
sys.exit(1)
