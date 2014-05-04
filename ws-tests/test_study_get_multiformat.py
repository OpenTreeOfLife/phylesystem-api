#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
from peyotl import convert_nexson_format
import json
import sys
import os
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/10'
data = {'output_nexml2json':'0.0.0'}
pb = test_http_json_method(SUBMIT_URI, 
                           'GET',
                            data=data,
                            expected_status=200,
                            return_bool_data=True)
if not pb[0]:
    sys.exit(1)

data = {'output_nexml2json':'1.0.0'}
pl = test_http_json_method(SUBMIT_URI, 
                           'GET',
                            data=data,
                            expected_status=200,
                            return_bool_data=True)
if not pb[0]:
    sys.exit(1)
badger = pb[1]['data']
legacy = pl[1]['data']
assert(badger != legacy)
lfromb = convert_nexson_format(badger, '1.0.0', current_format='0.0.0')
if lfromb != legacy:
    with open('.tmp1', 'w') as fo_one:
        json.dump(legacy, fo_one, indent=0, sort_keys=True)
    with open('.tmp2', 'w') as fo_one:
        json.dump(lfromb, fo_one, indent=0, sort_keys=True)
    assert(lfromb == legacy)
sys.exit(0)