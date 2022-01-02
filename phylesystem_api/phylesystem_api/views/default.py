from pyramid.view import (
                          view_config,
                          notfound_view_config,
                         )
from pyramid.response import Response
from phylesystem_api.markdown import _markdown_to_html
import requests
from peyotl import concatenate_collections
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

@view_config(route_name='trees_in_synth', renderer='json')
def trees_in_synth(request):
    """Return an "artificial" collection that contains all trees (and
    contributors) from all of the tree collections that contribute to
    synthesis.
    """
    coll_id_list = _get_synth_input_collection_ids()
    coll_list = []
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            coll_list.append(cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0])
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            # _LOG.exception(msg)
            raise HTTP(404, json.dumps({"error": 1, "description": msg}))
    try:
        result = concatenate_collections(coll_list)
    except:
        # _LOG.exception('concatenation of collections failed')
        e = sys.exc_info()[0]
        _raise_HTTP_from_msg(e)
    return json.dumps(result)

@view_config(route_name='include_tree_in_synth', renderer='json')
def include_tree_in_synth(request):
    pass

@view_config(route_name='exclude_tree_from_synth', renderer='json')
def exclude_tree_from_synth(request):
    pass

def _get_synth_input_collection_ids():
    """Return a list of all collection ids for the collections that contribute
    to synthesis (based on the current propinquity configuration).
    """
    # URL could be configurable, but I'm not sure we've ever changed this...
    url_of_synth_config = 'https://raw.githubusercontent.com/mtholder/propinquity/master/config.opentree.synth'
    try:
        resp = requests.get(url_of_synth_config)
        conf_fo = StringIO(resp.content)
    except:
        raise HTTP(504, 'Could not fetch synthesis list from {}'.format(url_of_synth_config))
    cfg = SafeConfigParser()
    try:
        cfg.readfp(conf_fo)
    except:
        raise HTTP(500, 'Could not parse file from {}'.format(url_of_synth_config))
    try:
        coll_id_list = cfg.get('synthesis', 'collections').split()
    except:
        raise HTTP(500, 'Could not find a collection list in file from {}'.format(url_of_synth_config))
    return coll_id_list

