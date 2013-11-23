#!/usr/bin/env python
import sys
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/9'
data = {
}
if test_http_json_method(SUBMIT_URI, 'PUT', data, expected_status=400):
    sys.exit(0)
sys.exit(1)
