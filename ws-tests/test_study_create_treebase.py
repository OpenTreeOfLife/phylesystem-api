#!/usr/bin/env python
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
import datetime
import codecs
import json
import sys
import os

DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
SUBMIT_URI = DOMAIN + "/v3/study/"
# refresh a timestamp so that the test generates a commit
data = {
    "import_method": "import-method-TREEBASE_ID",
    "import_from_location": "IMPORT_FROM_TREEBASE",
    "treebase_id": "12586",
    "publication_DOI": None,
    "cc0_agreement": False,
    "auth_token": auth_token,
    "cc0_agreement": "true",
}

r = test_http_json_method(
    SUBMIT_URI, "POST", data=data, expected_status=200, return_bool_data=True
)
if not r[0]:
    sys.exit(1)
resp = r[1]
print(resp)
