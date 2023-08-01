#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
frag_list = [
    "{d}/v3/study_list",
    "{d}/v3/amendments/amendment_list",
    "{d}/v3/collections/collection_list",
]
for frag in frag_list:
    SUBMIT_URI = frag.format(d=DOMAIN)
    print(SUBMIT_URI)
    r = test_http_json_method(
        SUBMIT_URI, "GET", expected_status=200, return_bool_data=True
    )
    if not r[0]:
        sys.exit(1)
    print(repr(r[1]))
    assert len(r) == 2
    assert isinstance(r[1], list)
