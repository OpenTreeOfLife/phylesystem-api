#!/usr/bin/env python
import sys
from cStringIO import StringIO

class NexSONError(Exception):
    def __init__(self, v):
        self.value = v
    def __str__(self):
        return repr(self.v)

# An enum of WARNING_CODES
class WarningCodes():
    facets = ['MISSING_MANDATORY_KEY',
              'MISSING_OPTIONAL_KEY']
for _n, _f in enumerate(WarningCodes.facets):
    setattr(WarningCodes, _f, _n)

def write_warning(out, prefix, wc, data):
    if not out:
        return
    if wc == WarningCodes.MISSING_MANDATORY_KEY:
        out.write('{p}Missing required key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.MISSING_OPTIONAL_KEY:
        out.write('{p}Missing optional key "{k}"'.format(p=prefix, k=data))
    else:
        assert(False)

class DefaultRichLogger(object):
    def __init__(self):
        self.out = sys.stderr
        self.prefix = ''
    def warn(self, warning_code, data):
        write_warning(self.out, self.prefix, warning_code, data)
    def error(self, warning_code, data):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data)
        raise NexSONError(s.getvalue())

class ValidationLogger(DefaultRichLogger):
    pass

class NexSON(object):
    def __init__(self, o, rich_logger=None):
        '''Creates an object that validates `o` as a dictionary
        that represents a valid NexSON object.
        Warnings are errors will be passed to rich_logger (or 
        as new DefaultRichLogger if None is passed in)
        '''
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self._raw = o
        if 'nexml' not in o:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'nexml')

def indented_keys(out, o, indentation='', indent=2):
    next_indentation = indentation + (' '*indent)
    if isinstance(o, dict):
        key_list = o.keys()
        key_list.sort()
        #out.write('{i}{{\n'.format(i=indentation))
        for k in key_list:
            v = o[k]
            if isinstance(v, dict):
                out.write('{i}{k} :\n'.format(i=indentation, k=k))
                indented_keys(out, v, next_indentation, indent)
                out.write('{i}\n'.format(i=indentation))
            elif isinstance(v, list) or isinstance(v, tuple):
                out.write('{i}{k} :\n'.format(i=indentation, k=k))
                indented_keys(out, v, next_indentation, indent)
            else:
                if k == '@property':
                    out.write('{i}{k} : {v}\n'.format(i=indentation, k=k, v=v))
                else:
                    out.write('{i}{k}\n'.format(i=indentation, k=k))
        #out.write('{i}}}\n'.format(i=indentation))
    else:
        assert isinstance(o, list) or isinstance(o, tuple)
        has_sub_list = False
        sk = set()
        for el in o:
            if isinstance(el, list) or isinstance(el, tuple):
                has_sub_list = True
            else:
                sk.update(el.keys())
        key_list = list(sk)
        key_list.sort()
        out.write('{i}[\n'.format(i=indentation))
        if has_sub_list:
            for el in o:
                if isinstance(el, list) or isinstance(el, tuple):
                    indented_keys(out, el, next_indentation, indent)
        for k in key_list:
            out.write('{i}{k}\n'.format(i=next_indentation, k=k))
        out.write('{i}]\n'.format(i=indentation))
        

