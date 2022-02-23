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
    # study/tree routes
    config.add_route('study_properties', '/{api_version}/studies/properties')
    config.add_route('find_studies', '/{api_version}/studies/find_studies')
    config.add_route('find_trees', '/{api_version}/studies/find_trees')
    config.add_route('trees_in_synth', '/{api_version}/trees_in_synth')
    config.add_route('include_tree_in_synth', '/{api_version}/include_tree_in_synth')
    config.add_route('exclude_tree_from_synth', '/{api_version}/exclude_tree_from_synth')
    config.add_route('get_study', '/{api_version}/study/{study_id}')
    """
    config.add_route('get_study_file', '/{api_version}/study/{study_id}')
    config.add_route('get_study_external_url', '/{api_version}/study/{study_id}')
    config.add_route('get_study_tree', '/{api_version}/study/{study_id}')
    config.add_route('get_study_tree_newick', '/{api_version}/study/{study_id}')
    """
    # tree collection routes
    config.add_route('find_collections', '/{api_version}/collections/find_collections')
    # taxonomic amendment routes
