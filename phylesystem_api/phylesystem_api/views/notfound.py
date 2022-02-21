from pyramid.view import notfound_view_config


@notfound_view_config(renderer='phylesystem_api:templates/404.jinja2',
                      accept='text/html',
                      append_slash=True)
def notfound_view(request):
    request.response.status = 404
    return {}
