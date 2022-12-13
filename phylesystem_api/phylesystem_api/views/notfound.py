from pyramid.view import notfound_view_config
from pyramid.response import Response
import logging
try:
    import anyjson
except:
    import json
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads


#_LOG = logging.getLogger('phylesystem_api')

# most API pages should be JSON, so here's a suitable 404 response
@notfound_view_config(renderer='json',
                      accept='application/json',
                      append_slash=True)
def notfound(request):
    #_LOG.debug("Request not found")
    #_LOG.debug(request)
    return Response(
        body=anyjson.dumps({'message': 'Nothing found at this URL'}),
        status='404 Not Found',
        charset='UTF-8',
        content_type='application/json')
