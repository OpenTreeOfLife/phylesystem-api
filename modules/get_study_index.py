from threading import Lock
_study_index_lock = Lock()
_study_index = None

def _initialize_study_index(repo_dir):
    d = {} # Key is study id, value is repo,dir tuple
    for root, dirs, files in os.walk("."):      
       for file in files:
         if ".git" not in root:
             d[file]=root    # if file is in more than one place it gets over written

'''    for repo in os.walk(repo_dir).next()[1]:
        if os.path.isdir(repo+"/.git"):
              for dir in os.walk(repo).next()[1]:
                  if dir!= ".git":
                     fis=os.walk(repo+'/'+dir).next()[2]
                     for fi in fis:
                         d[fi]=(repo,dir)
                # ignore alphabetic prefix, o = created by opentree API
                if f[0].isalpha():
                    dirs.append(int(f[1:]))
                else:
                    dirs.append(int(f))''' #EJM garbage I think
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
