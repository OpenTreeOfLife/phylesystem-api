from pyramid.view import view_config
from pyramid.response import Response
from phylesystem_api.markdown import _markdown_to_html

@view_config(route_name='home', renderer='phylesystem_api:templates/home.jinja2')
def home_view(request):
    # a simple README web page for the curious
    return {'title': 'phylesystem API'}

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
