#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")

frag_list = [
    "{d}/",
    "{d}/v3",
    "{d}/v3/",
    "{d}/v3/studies",
    "{d}/v3/studies/",
    "{d}/v3/collections",
    "{d}/v3/collections/",
    "{d}/v3/amendments",
    "{d}/v3/amendments/",
]
for frag in frag_list:
    SUBMIT_URI = frag.format(d=DOMAIN)
    print(SUBMIT_URI)
    if not test_http_json_method(SUBMIT_URI, "GET", expected_status=200):
        sys.exit(1)
