#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
# this amendment does not exist
SUBMIT_URI = DOMAIN + "/v3/amendment/additions-0000000-99999999"
if test_http_json_method(SUBMIT_URI, "GET", expected_status=404):
    sys.exit(0)
sys.exit(1)
