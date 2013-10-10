#!/usr/bin/env python
import sys
import os
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...
from nexson_validator import NexSON, NexSONError, ValidationLogger, WarningCodes

def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('ERROR: {m}'.format(m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def warn(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('WARNING: {m}'.format(m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def info(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write(msg)
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def get_nexsons_filepath_list(inp_filepath):
    ifp = []
    for root, d, file_list in os.walk(inp_filepath):
        for filename in file_list:
            lf = filename.lower()
            if lf.endswith('.json') or lf.endswith('.nexson'):
                ifp.append(os.path.join(root, filename))
    return ifp

if __name__ == '__main__':
    import json
    import codecs
    import argparse
    parser = argparse.ArgumentParser(description='Validate a json file as Open Tree of Life NexSON')
    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('input', metavar='filepath', type=unicode, nargs=1, help='filename')
    args = parser.parse_args()
    SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    if os.path.isdir(inp_filepath):
        inp_fp_list = get_nexsons_filepath_list(inp_filepath)
    else:
        inp_fp_list = [inp_filepath]
    err_dict = {}
    warn_dict = {}
    for inp_filepath in inp_fp_list:
        inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
        try:
            obj = json.load(inp)
        except ValueError as vx:
            error('Not valid JSON.')
            if args.verbose:
                raise vx
            else:
                sys.exit(1)
        v = ValidationLogger(store_messages=True)
        try:
            n = NexSON(obj, v)
        except NexSONError as nx:
            error(nx.value)
            sys.exit(1)
        for e in v.errors:
            err_dict.setdefault(e.warning_code, []).append(e.getvalue())
        for w in v.warnings:
            warn_dict.setdefault(w.warning_code, []).append(w.getvalue())
    ekl = err_dict.keys()
    ekl.sort()
    for k in ekl:
        e_list = err_dict[k]
        e_list.sort()
        for el in e_list:
            error(el)
    wkl = warn_dict.keys()
    wkl.sort()
    for k in wkl:
        w_list = warn_dict[k]
        w_list.sort()
        for el in w_list:
            warn(el)
    info('Errors:')
    for k in ekl:
        m = '    {n} errors of type {t}'.format(n=str(len(err_dict[k])), t=WarningCodes.facets[k])
        info(m)
    info('Warnings:')
    for k in wkl:
        m = '    {n} errors of type {t}'.format(n=str(len(warn_dict[k])), t=WarningCodes.facets[k])
        info(m)
