#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit

DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
SUBMIT_URI = DOMAIN + "/v3/study/10"
data = {"nexson": {"bogus": 5}, "auth_token": auth_token}
if test_http_json_method(SUBMIT_URI, "PUT", data, expected_status=400):
    sys.exit(0)
sys.exit(1)
