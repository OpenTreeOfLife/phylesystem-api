def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')  # tiny README for the curious
    # config.add_route('task_detail', '/api/v1/accounts/{username}/tasks/{id}')
