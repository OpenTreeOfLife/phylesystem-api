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
              'MISSING_OPTIONAL_KEY',
              'UNRECOGNIZED_KEY',
              'MISSING_LIST_EXPECTED',
              ]
for _n, _f in enumerate(WarningCodes.facets):
    setattr(WarningCodes, _f, _n)

def write_warning(out, prefix, wc, data, context=None):
    if not out:
        return
    if wc == WarningCodes.MISSING_MANDATORY_KEY:
        out.write('{p}Missing required key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.MISSING_OPTIONAL_KEY:
        out.write('{p}Missing optional key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.UNRECOGNIZED_KEY:
        out.write('{p}Unrecognized key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.MISSING_LIST_EXPECTED:
        out.write('{p}Expected a list found "{k}"'.format(p=prefix, k=type(data)))
    else:
        assert(False)
    if context is not None:
        out.write(' in "{el}"'.format(el=context))
    out.write('\n')

class DefaultRichLogger(object):
    def __init__(self):
        self.out = sys.stderr
        self.prefix = ''
    def warn(self, warning_code, data, context=None):
        write_warning(self.out, self.prefix, warning_code, data, context)
    def error(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        raise NexSONError(s.getvalue())

class ValidationLogger(DefaultRichLogger):
    def __init__(self):
        DefaultRichLogger.__init__(self)
        self.warnings = []
        self.errors = []
    def warn(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        self.warnings.append(s.getvalue())
    def error(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        self.errors.append(s.getvalue())

class OTU(object):
    REQUIRED_KEYS = ('@id',)
    EXPECTED_KEYS = ('@id', 'otu')
    def __init__(self, o, rich_logger=None):
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self._raw = o
        self._as_list = []
        self._as_dict = {}
        for k in o.keys():
            if k not in OTUSet.EXPECTED_KEYS:
                rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k, context='otus')

class NexsonDictWrapper(object):
    def get_nexson_id(self):
        return self._raw.get('@id')
    nexson_id = property(get_nexson_id)

class OTU(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECTED_KEYS = ('@id', '@about', '@label', 'meta')
    def __init__(self, o, rich_logger=None):
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self._raw = o
        for k in o.keys():
            if k not in OTU.EXPECTED_KEYS:
                rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k, context='otus')

class OTUSet(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECTED_KEYS = ('@id', 'otu')
    def __init__(self, o, rich_logger=None):
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self._raw = o
        self._as_list = []
        self._as_dict = {}
        for k in o.keys():
            if k not in OTUSet.EXPECTED_KEYS:
                rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k, context='otus')
        v = o.get('otu')
        if v is None:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'otu', context='otus')
        elif not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='otu')
        else:
            for el in v:
                n_otu = OTU(el, rich_logger)
                nid = n_otu.nexson_id
                if nid:
                    if nid in self._as_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, context='otu')
                    else:
                        self._as_dict[nid] = n_otu
                self._as_list.append(n_otu)

class NexSON(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECTED_KEYS = ("@about",
                     "@generator",
                     "@id",
                     "@nexmljson",
                     "@version",
                     "@xmlns",
                     "otus",
                     "trees",
                     "meta",
                     )
    def __init__(self, o, rich_logger=None):
        '''Creates an object that validates `o` as a dictionary
        that represents a valid NexSON object.
        Warnings are errors will be passed to rich_logger (or 
        as new DefaultRichLogger if None is passed in)
        '''
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self._raw = o
        for k in o.keys():
            if k not in ['nexml']:
                rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k)
        self._nexml = None
        if 'nexml' not in o:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'nexml')
        else:
            self._nexml = o['nexml']
            for k in self._nexml.keys():
                if k not in NexSON.EXPECTED_KEYS:
                    rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k, context='nexml')
            for k in NexSON.REQUIRED_KEYS:
                if k not in self._nexml:
                    rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, k, context='nexml')
            v = self._nexml.get('otus')
            if v is None:
                rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'otus', context='nexml')
            else:
                self.otus = OTUSet(v, rich_logger)

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
        

