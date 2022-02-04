#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/10/tree/tree3.tre'
data = {'tip_label': 'ot:ottTaxonName'}
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          data=data,
                          expected_status=200,
                          return_bool_data=True,
                          is_json=False)
if r[0]:
    print((r[1]))
    assert '[pre-ingroup-marker]' not in r[1]
else:
    sys.exit(1)
data['bracket_ingroup'] = True
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          data=data,
                          expected_status=200,
                          return_bool_data=True,
                          is_json=False)
if r[0]:
    print((r[1]))
    assert '[pre-ingroup-marker]' in r[1]
else:
    sys.exit(1)
