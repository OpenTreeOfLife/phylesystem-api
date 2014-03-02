from threading import Lock
_study_index_lock = Lock()
_study_index = None

def _initialize_study_index():
    d = {}
    for f in os.listdir("study/"):
            if os.path.isdir("study/%s" % f):
                # ignore alphabetic prefix, o = created by opentree API
                if f[0].isalpha():
                    dirs.append(int(f[1:]))
                else:
                    dirs.append(int(f))
    return d

def get_paths_for_study_id(study_id):
    global _study_index, _study_index_lock
    _study_index_lock.acquire()
    try:
        if _study_index is None:
            _study_index = _initialize_study_index()
        _study_index[study_id]
    finally:
        _study_index_lock.release()

def create_new_path_for_study_id(study_id):
    global _study_index, _study_index_lock
    _study_index_lock.acquire()
    try:
        pass
    finally:
        _study_index_lock.release()
try:
    get_paths_for_study_id('abdha')
except:
    pass



for f in os.listdir("study/"):
            if os.path.isdir("study/%s" % f):
                # ignore alphabetic prefix, o = created by opentree API
                if f[0].isalpha():
                    dirs.append(int(f[1:]))
                else:
                    dirs.append(int(f))