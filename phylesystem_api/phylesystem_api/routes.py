def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('index', '/')  # simple homepage for the curious
    config.add_route('api_root', '/{api_version}/')  # tiny API description with links to code/docs
    config.add_route('study_properties', '/{api_version}/studies/properties')
    config.add_route('render_markdown', '/{api_version}/render_markdown')
    config.add_route('phylesystem_config', '/{api_version}/phylesystem_config')
    config.add_route('find_studies', '/{api_version}/studies/find_studies')
    config.add_route('find_trees', '/{api_version}/studies/find_trees')
    config.add_route('find_collections', '/{api_version}/collections/find_collections')
    config.add_route('trees_in_synth', '/{api_version}/trees_in_synth')
    config.add_route('include_tree_in_synth', '/{api_version}/include_tree_in_synth')
    config.add_route('exclude_tree_from_synth', '/{api_version}/exclude_tree_from_synth')
