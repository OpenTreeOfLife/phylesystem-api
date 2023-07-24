#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
SUBMIT_URI = DOMAIN + "/v3/amendments/push_failure"
r = test_http_json_method(SUBMIT_URI, "GET", expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(1)
assert len(r) == 2
push_details = r[1]
assert isinstance(push_details, dict)
assert push_details["doc_type"] == "amendment"
