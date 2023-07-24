#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config

DOMAIN = config("host", "apihost")
SUBMIT_URI = DOMAIN + "/v3/study_list"
# NB this is not a duplicate of /v3/studies/find_studies !
# It's a rarely-used method to fetch all studies prior to building the oti index!
# See this helpful issue from @jar398:
#   https://github.com/OpenTreeOfLife/germinator/issues/94#issuecomment-227027174

r = test_http_json_method(SUBMIT_URI, "GET", expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(1)
