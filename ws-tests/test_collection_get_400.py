#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
# study 1 does not exist
SUBMIT_URI = DOMAIN + "/v3/collection/nonexistentuser/fake-id"
if test_http_json_method(SUBMIT_URI, "GET", expected_status=400):
    sys.exit(0)
sys.exit(1)
