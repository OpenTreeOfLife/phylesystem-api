from pyramid.response import Response
from pyramid.view import notfound_view_config
import json

# most API pages should be JSON, so here's a suitable 404 response
@notfound_view_config(renderer="json", accept="application/json", append_slash=True)
def notfound(request):
    # _LOG.debug("Request not found")
    # _LOG.debug(request)
    return Response(
        body=json.dumps({"message": "Nothing found at this URL"}),
        status="404 Not Found",
        charset="UTF-8",
        content_type="application/json",
    )
