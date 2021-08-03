from pyramid.view import view_config


@view_config(route_name='home', renderer='phylesystem_api:templates/home.jinja2')
def home_view(request):
    return {'title': 'phylesystem API'}
