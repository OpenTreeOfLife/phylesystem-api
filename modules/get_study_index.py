from threading import Lock
_study_index_lock = Lock()
_study_index = None

def _initialize_study_index(repo_dir):
    d = {} # Key is study id, value is repo,dir tuple
    for root, dirs, files in os.walk("."):      
       for file in files:
         if ".git" not in root:
             d[file]=root    # if file is in more than one place it gets over written. EJM Needs work 

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
