#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
from peyotl import convert_nexson_format
import json
import sys
import os
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/10'
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

def dict_eq(a, b):
    if a == b:
        return True
    d = True
    ka, kb = a.keys(), b.keys()
    ka.sort()
    kb.sort()
    if ka != kb:
        sa = set(ka)
        sb = set(kb)
        ao = sa - sb
        ao = list(ao)
        ao.sort()
        bo = sb - sa
        c = set([u'^ot:candidateTreeForSynthesis', u'^ot:tag'])
        bextra = bo - c
        bo = list(bextra)
        bo.sort()
        if bextra or ao:
            sys.stdout.write('  keys in a only "{a}"."\n'.format(a=ao))
            sys.stdout.write('  keys in b only "{a}"."\n'.format(a=bo))
            d = False
    for k in ka:
        va = a[k]
        vb = b[k]
        if va != vb:
            if isinstance(va, dict) and isinstance(vb, dict):
                if not dict_eq(va, vb):
                    d = False
            elif isinstance(va, list) and isinstance(vb, list):
                for n, ela in enumerate(va):
                    elb = vb[n]
                    if not dict_eq(ela, elb):
                        d = False
                if len(va) != len(vb):
                    d = False
                    sys.stdout.write('  lists for {} differ in length.\n'.format(k))
            else:
                d = False
                sys.stdout.write('  value for {k}: "{a}" != "{b}"\n'.format(k=k, a=va, b=vb))
    return d


if lfromb != legacy:
    with open('.tmp1', 'w') as fo_one:
        json.dump(legacy, fo_one, indent=0, sort_keys=True)
    with open('.tmp2', 'w') as fo_one:
        json.dump(lfromb, fo_one, indent=0, sort_keys=True)
    assert(dict_eq(lfromb, legacy))
sys.exit(0)
