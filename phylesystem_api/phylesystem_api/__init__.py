from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings) as config:
        config.include('pyramid_jinja2')
        #config.include('.cors')  # Python 2
        config.include('cors')  # Python 3
        config.add_cors_preflight_handler()
        config.include('.routes')
        config.scan()
    return config.make_wsgi_app()
