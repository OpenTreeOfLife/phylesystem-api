from pyramid.config import Configurator
from .api_utils import get_conf_object, get_docstore_from_type


def main(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    with Configurator(settings=settings) as config:
        config.include("pyramid_jinja2")
        config.include(".cors")
        config.add_cors_preflight_handler()
        config.include(".routes")
        config.scan()
    # for k, v in settings.items():
    #     print("{k}: {v}".format(k=k, v=repr(v)))
    localconfig_filename = settings["config_file_path"]
    conf_obj = get_conf_object(localconfig_filename=localconfig_filename)
    _ps = get_docstore_from_type("study", request=None, conf_obj=conf_obj)
    return config.make_wsgi_app()
