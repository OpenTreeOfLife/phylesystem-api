#!/usr/bin/env python
import sys
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...
from nexson_validator import NexSON, NexSONError, ValidationLogger, FilteringLogger, WarningCodes, VERSION
def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: ERROR: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def warn(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: WARNING: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def info(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

if __name__ == '__main__':
    import json
    import os
    import codecs
    import argparse
    import platform
    import datetime
    import uuid
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    parser = argparse.ArgumentParser(description='Convert a NexSON file to another file format')
    parser.add_argument('--format', dest='out_format', type=str, default='newick', help='output format: currently "newick" is the only valid value')
    parser.add_argument('--ott-id', dest='use_ott_it', action='store_true', default=False, help="Use OTT IDs instead of labels in output")
    parser.add_argument('input', metavar='filepath', type=unicode, nargs=1, help='filename')
    args = parser.parse_args()
    SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
    flower = args.out_format.lower()
    if flower not in ['newick']:
        sys.exit('Output format "{o}" not recognized'.format(o=args.out_format))
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
    try:
        obj = json.load(inp)
    except ValueError as vx:
        error('Not valid JSON.')
        sys.exit(1)
    v = ValidationLogger(store_messages=True)
    check_codes = list(WarningCodes.numeric_codes_registered)
    checks_performend = [WarningCodes.facets[i] for i in check_codes]
    try:
        n = NexSON(obj, v)
    except NexSONError as nx:
        error(nx.value)
        sys.exit(1)

    output = sys.stdout
    if v.errors:
        for m in v.errors:
            error(m.getvalue())
        sys.exit(1)
    for tree in n.trees._as_list:
        print tree.get_newick()