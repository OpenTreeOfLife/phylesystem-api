from ConfigParser import SafeConfigParser
import os

def read_config(request):
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    localconfig_filename = "%s/applications/%s/private/localconfig" % (request.env.web2py_path, app_name)

    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    else:
        filename = "%s/applications/%s/private/config" % (request.env.web2py_path, app_name)
        conf.readfp(open(filename))

    repo_path   = conf.get("apis","repo_path")
    repo_remote = conf.get("apis", "repo_remote")
    git_ssh     = conf.get("apis", "git_ssh")
    pkey        = conf.get("apis", "pkey")

    return repo_path, repo_remote, git_ssh, pkey
