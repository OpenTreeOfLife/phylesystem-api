def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')  # tiny README for the curious
    config.add_route('render_markdown', '/{api_version}/render_markdown')
    config.add_route('phylesystem_config', '/{api_version}/phylesystem_config')
