#!/usr/bin/env python
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit


DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
data = {"auth_token": auth_token}
frag_list = [
    "{d}/v3/push_docstore_changes/studies",
    "{d}/v3/push_docstore_changes/amendments",
    "{d}/v3/push_docstore_changes/collections",
]
for frag in frag_list:
    SUBMIT_URI = frag.format(d=DOMAIN)
    r = test_http_json_method(
        SUBMIT_URI, "PUT", data=data, expected_status=200, return_bool_data=True
    )
    if not r[0]:
        sys.exit(1)

SUBMIT_URI = "{d}/v3/push_docstore_changes/studies".format(d=DOMAIN)
if not test_http_json_method(SUBMIT_URI, "PUT", data={}, expected_status=400):
    sys.exit(1)
