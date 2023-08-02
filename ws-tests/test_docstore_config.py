#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
frag_list = [
    "{d}/phylesystem_config",
    "{d}/v3/studies/store_config",
    "{d}/v3/amendments/store_config",
    "{d}/v3/collections/store_config",
]
for frag in frag_list:
    SUBMIT_URI = frag.format(d=DOMAIN)
    r = test_http_json_method(
        SUBMIT_URI, "GET", expected_status=200, return_bool_data=True
    )
    if not r[0]:
        sys.exit(1)
    assert len(r) == 2
    assert isinstance(r[1], dict)

SUBMIT_URI = "{d}/v3/bogus/store_config".format(d=DOMAIN)
if not test_http_json_method(SUBMIT_URI, "GET", expected_status=404):
    sys.exit(1)
