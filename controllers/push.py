import api_utils
import traceback
import datetime
import codecs
import json
import os

@request.restful()
def v1():
    """The OpenTree API v1: Merge Controller

    This controller can be used to merge changes from master into
    a WIP. After this succeeds, subsequent GETs and POSTs to the document
    should be able to merge to master.
    """
    response.view = 'generic.json'

    def PUT(resource_id=None, jsoncallback=None, callback=None, _=None, resource_type='study', **kwargs):
        """OpenTree API methods relating to updating branches

        'resource_type' should be 'study' (default), 'collection', or 'favorites'

        curl -X POST http://localhost:8000/api/push/v1?resource_id=9
        curl -X POST http://localhost:8000/api/push/v1?resource_id=TestUserB/my-favorite-trees&resource_type=collection
        """
        _LOG = api_utils.get_logger(request, 'ot_api.push.v1.PUT')
        fail_file = api_utils.get_failed_push_filepath(request)
        _LOG.debug(">> fail_file for type '{t}': {f}".format(t=resource_type, f=fail_file))
        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'




        phylesystem = api_utils.get_phylesystem(request)
        try:
            phylesystem.push_study_to_remote('GitHubRemote', resource_id)
        except:
            m = traceback.format_exc()
            _LOG.warn('Push of study {s} failed. Details: {m}'.format(s=resource_id, m=m))
            if os.path.exists(fail_file):
                _LOG.warn('push failure file "{f}" already exists. This event not logged there'.format(f=fail_file))
            else:
                timestamp = datetime.datetime.utcnow().isoformat()
                try:
                    ga = phylesystem.create_git_action(resource_id)
                except:
                    m = 'Could not create an adaptor for git actions on study ID "{}". ' \
                        'If you are confident that this is a valid study ID, please report this as a bug.'
                    m = m.format(resource_id)
                    raise HTTP(400, json.dumps({'error': 1, 'description': m}))
                master_sha = ga.get_master_sha()
                obj = {'date': timestamp,
                       'study': resource_id,
                       'commit': master_sha,
                       'stacktrace': m}
                api_utils.atomic_write_json_if_not_found(obj, fail_file, request)
                _LOG.warn('push failure file "{f}" created.'.format(f=fail_file))
            raise HTTP(409, json.dumps({
                "error": 1,
                "description": "Could not push! Details: {m}".format(m=m)
            }))



        if os.path.exists(fail_file):
            # log any old fail_file, and remove it because the pushes are working
            with codecs.open(fail_file, 'rU', encoding='utf-8') as inpf:
                prev_fail = json.load(inpf)
            os.unlink(fail_file)
            fail_log_file = codecs.open(fail_file + '.log', mode='a', encoding='utf-8')
            json.dump(prev_fail, fail_log_file, indent=2, encoding='utf-8')
            fail_log_file.close()

        return {'error': 0,
                'description': 'Push succeeded'}
    return locals()
