from pyramid.view import (
                          view_config,
                          notfound_view_config,
                         )
from pyramid.response import Response
from phylesystem_api.markdown import _markdown_to_html
import phylesystem_api.api_utils as api_utils

@view_config(route_name='home', renderer='phylesystem_api:templates/home.jinja2')
def home_view(request):
    # a simple README web page for the curious
    return {'title': 'phylesystem API'}

# all other pages should be JSON, so here's a suitable 404 response
@notfound_view_config(renderer='json',
                      accept='application/json')
def notfound(request):
    return Response(
        body=json.dumps({'message': 'Nothing found at this URL'}),
        status='404 Not Found',
        content_type='application/json')

@view_config(route_name='render_markdown')
def render_markdown(request):
    # Convert POSTed Markdown to HTML (e.g., for previews in web UI)
    src = request.body.decode('utf-8')
    html = _markdown_to_html( src, open_links_in_new_window=True )
    return Response(body=html, content_type='text/html')

@view_config(route_name='phylesystem_config', renderer='json')
def phylesystem_config(request):
    # general information about the hosted phylesystem
    phylesystem = api_utils.get_phylesystem(request)
    return phylesystem.get_configuration_dict()
