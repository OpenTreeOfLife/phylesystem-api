#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
CONTROLLER = DOMAIN + "/v3/studies"
SUBMIT_URI = CONTROLLER + "/find_studies"
r = test_http_json_method(
    SUBMIT_URI, "POST", expected_status=200, return_bool_data=True
)
assert r[0] is True
assert len(r[1]) > 0
assert len(r[1]["matched_studies"]) > 0
assert list(r[1]["matched_studies"][0].keys()) == ["ot:studyId"]
