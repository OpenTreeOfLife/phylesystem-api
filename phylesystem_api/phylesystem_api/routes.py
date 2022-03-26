def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    # show a simple HTML homepage for the curious
    config.add_route('index', '/')
    # some (unused) URLs just show a tiny API description, with links to code + docs
    config.add_route('api_root', '/')
    config.add_route('api_version_root', '/{api_version}/')
    config.add_route('api_version_noslash', '/{api_version}')
    config.add_route('studies_root', '/{api_version}/studies/')
    config.add_route('collections_root', '/{api_version}/collections/')
    config.add_route('amendments_root', '/{api_version}/amendments/')
    # utilities (generally for internal use, not documented)
    config.add_route('render_markdown', '/{api_version}/render_markdown')
    config.add_route('phylesystem_config', '/{api_version}/phylesystem_config')
    config.add_route('raw_study_list', '/{api_version}/study_list')
    config.add_route('pull_through_cache', '/cached/{target_url:.*}')
    #
    # STUDY/TREE ROUTES
    #
    config.add_route('study_properties', '/{api_version}/studies/properties')
    config.add_route('find_studies', '/{api_version}/studies/find_studies')
    config.add_route('find_trees', '/{api_version}/studies/find_trees')
    config.add_route('trees_in_synth', '/{api_version}/trees_in_synth')
    config.add_route('include_tree_in_synth', '/{api_version}/include_tree_in_synth')
    config.add_route('exclude_tree_from_synth', '/{api_version}/exclude_tree_from_synth')
    config.add_route('create_study', '/{api_version}/study')
    config.add_route('study_CORS_preflight', '/{api_version}/study/{study_id}', request_method='OPTIONS')
    config.add_route('fetch_study', '/{api_version}/study/{study_id}', request_method='GET')
    config.add_route('update_study', '/{api_version}/study/{study_id}', request_method='PUT')
    config.add_route('delete_study', '/{api_version}/study/{study_id}', request_method='DELETE')
    config.add_route('get_study_file_list', '/{api_version}/study/{study_id}/file')
    config.add_route('get_study_single_file', '/{api_version}/study/{study_id}/file/{file_id}')
    config.add_route('get_study_external_url', '/{api_version}/study/external_url/{study_id}')
    config.add_route('get_study_tree', '/{api_version}/study/{study_id}/tree/{tree_id_with_extension}')
    #
    # TREE COLLECTION ROUTES
    #
    config.add_route('list_all_collection_ids', '/{api_version}/collections/collection_list')
    config.add_route('get_collections_config', '/{api_version}/collections/store_config')
    config.add_route('collections_push_failure', '/{api_version}/collections/push_failure')
    config.add_route('collection_properties', '/{api_version}/collections/properties')
    config.add_route('find_trees_in_collections', '/{api_version}/collections/find_trees')
    config.add_route('find_collections', '/{api_version}/collections/find_collections')
    config.add_route('create_collection', '/{api_version}/collection')
    config.add_route('collection_CORS_preflight', '/{api_version}/collection/{collection_id}', request_method='OPTIONS')
    config.add_route('fetch_collection', '/{api_version}/collection/{collection_id}', request_method='GET')
    config.add_route('update_collection', '/{api_version}/collection/{collection_id}', request_method='PUT')
    config.add_route('delete_collection', '/{api_version}/collection/{collection_id}', request_method='DELETE')
    #
    # TAXONOMIC AMENDMENT ROUTES
    #
    config.add_route('list_all_amendment_ids', '/{api_version}/amendments/amendment_list')
    config.add_route('list_all_amendments', '/{api_version}/amendments/list_all')
    config.add_route('get_amendments_config', '/{api_version}/amendments/store_config')
    config.add_route('amendments_push_failure', '/{api_version}/amendments/push_failure')
    config.add_route('create_amendment', '/{api_version}/amendment')
    config.add_route('amendment_CORS_preflight', '/{api_version}/amendment/{amendment_id}', request_method='OPTIONS')
    config.add_route('fetch_amendment', '/{api_version}/amendment/{amendment_id}', request_method='GET')
    config.add_route('update_amendment', '/{api_version}/amendment/{amendment_id}', request_method='PUT')
    config.add_route('delete_amendment', '/{api_version}/amendment/{amendment_id}', request_method='DELETE')
