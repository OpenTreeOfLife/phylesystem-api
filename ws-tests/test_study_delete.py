#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
starting_commit_SHA = config('host', 'parentsha')

if len(sys.argv) > 1:
    study_id = sys.argv[1]
else:
    study_id = 12

SUBMIT_URI = DOMAIN + '/v1/study/%s' % study_id
data = {
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
if test_http_json_method(SUBMIT_URI, 'DELETE', data=data, expected_status=200):
    sys.exit(0)
sys.exit(1)
