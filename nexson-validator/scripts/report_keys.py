#!/usr/bin/env python
import sys
import codecs
import json
from nexson_validator import indented_keys

if __name__ == '__main__':
    for fn in sys.argv[1:]:
        fo = codecs.open(fn, 'rU', encoding='utf-8')
        o = json.load(fo)
        indented_keys(sys.stdout, o)
