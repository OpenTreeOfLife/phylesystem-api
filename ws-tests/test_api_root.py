#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
if test_http_json_method(DOMAIN, 'GET', expected_status=200):
    sys.exit(0)
sys.exit(1)
