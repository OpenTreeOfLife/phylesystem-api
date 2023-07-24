#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
SUBMIT_URI = DOMAIN + "/v3/amendments/list_all"
# NB - This vaguely-named methd returns all amendments (complete JSON)
r = test_http_json_method(SUBMIT_URI, "GET", expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(1)
assert len(r) == 2
assert isinstance(r[1], list)
# print r[1]
