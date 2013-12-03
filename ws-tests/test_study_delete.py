#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/12'
data = {
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
}
if test_http_json_method(SUBMIT_URI, 'DELETE',data=data, expected_status=200):
    sys.exit(0)
sys.exit(1)
