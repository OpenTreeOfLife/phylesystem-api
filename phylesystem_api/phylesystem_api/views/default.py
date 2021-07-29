from pyramid.view import view_config


@view_config(route_name='home', renderer='phylesystem_api:templates/mytemplate.jinja2')
def my_view(request):
    return {'project': 'phylesystem API'}
