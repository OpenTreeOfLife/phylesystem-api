def includeme(config):
    config.add_static_view("static", "static", cache_max_age=3600)
    # show a simple HTML homepage for the curious
    config.add_route("index", "/")
    # some (unused) URLs just show a tiny API description, with links to code + docs
    config.add_route("api_root", "/")
    config.add_route("api_version_root", "/v{api_version:[123]}")
    config.add_route("api_version_root_slash", "/v{api_version:[123]}/")
    config.add_route("studies_root", "/v{api_version:[123]}/studies")
    config.add_route("studies_root_slash", "/v{api_version:[123]}/studies/")
    config.add_route("collections_root", "/v{api_version:[123]}/collections")
    config.add_route("collections_root_slash", "/v{api_version:[123]}/collections/")
    config.add_route("amendments_root", "/v{api_version:[123]}/amendments")
    config.add_route("amendments_root_slash", "/v{api_version:[123]}/amendments/")
    # utilities (generally for internal use, not documented)
    config.add_route("render_markdown", "/v{api_version:[123]}/render_markdown")
    config.add_route("phylesystem_config", "/v{api_version:[123]}/phylesystem_config")
    config.add_route("phylesystem_config_no_vers", "/phylesystem_config")
    config.add_route("phylesystem_config_no_vers_slash", "/phylesystem_config/")
    config.add_route("raw_study_list", "/v{api_version:[123]}/study_list")
    config.add_route("pull_through_cache", "/cached/{target_url:.*}")
    config.add_route("clear_cache_keys", "/clear_cache_keys/{key_pattern:.*}")
    config.add_route(
        "merge_docstore_changes",
        "/v{api_version:[123]}/merge_docstore_changes/{doc_id}/{starting_commit_SHA}",
    )
    config.add_route(
        "push_docstore_changes",
        "/v{api_version:[123]}/push_docstore_changes/{doc_type}/{doc_id}",
    )
    config.add_route(
        "push_docstore_changes_bare",
        "/v{api_version:[123]}/push_docstore_changes/{doc_type}",
        request_method="PUT",
    )
    #
    # STUDY/TREE ROUTES
    #
    config.add_route("study_properties", "/v{api_version:[123]}/studies/properties")
    config.add_route(
        "conventional_study_list", "/v{api_version:[123]}/studies/study_list"
    )

    config.add_route("find_studies", "/v{api_version:[123]}/studies/find_studies")
    config.add_route("find_trees", "/v{api_version:[123]}/studies/find_trees")
    config.add_route("trees_in_synth", "/v{api_version:[123]}/trees_in_synth")
    config.add_route(
        "include_tree_in_synth", "/v{api_version:[123]}/include_tree_in_synth"
    )
    config.add_route(
        "exclude_tree_from_synth", "/v{api_version:[123]}/exclude_tree_from_synth"
    )
    config.add_route("create_study", "/v{api_version:[123]}/study/")
    config.add_route(
        "study_CORS_preflight",
        "/v{api_version:[123]}/study/{study_id}",
        request_method="OPTIONS",
    )
    config.add_route(
        "fetch_study", "/v{api_version:[123]}/study/{study_id}", request_method="GET"
    )
    config.add_route(
        "fetch_study_label",
        "/v{api_version:[123]}/study/{study_id}/",
        request_method="GET",
    )
    config.add_route(
        "update_study", "/v{api_version:[123]}/study/{study_id}", request_method="PUT"
    )
    config.add_route(
        "delete_study",
        "/v{api_version:[123]}/study/{study_id}",
        request_method="DELETE",
    )
    config.add_route(
        "get_study_file_list", "/v{api_version:[123]}/study/{study_id}/file"
    )
    config.add_route(
        "get_study_single_file", "/v{api_version:[123]}/study/{study_id}/file/{file_id}"
    )
    config.add_route(
        "get_study_external_url", "/v{api_version:[123]}/study/external_url/{study_id}"
    )
    config.add_route(
        "get_study_tree",
        "/v{api_version:[123]}/study/{study_id}/tree/{tree_id_with_extension}",
    )
    config.add_route(
        "get_study_tree_label",
        "/v{api_version:[123]}/study/{study_id}/tree/{tree_id_with_extension}/",
    )
    #
    # STUDY/OTHER FINE-GRAINED ACCESS ROUTES
    #
    config.add_route(
        "get_study_otu_by_id", "/v{api_version:[123]}/study/{study_id}/otu/{otu_id}"
    )
    config.add_route(
        "get_study_otu_by_id_slash",
        "/v{api_version:[123]}/study/{study_id}/otu/{otu_id}/",
    )
    config.add_route("get_study_otu", "/v{api_version:[123]}/study/{study_id}/otu")
    config.add_route(
        "get_study_otu_slash", "/v{api_version:[123]}/study/{study_id}/otu/"
    )
    config.add_route("get_study_otus", "/v{api_version:[123]}/study/{study_id}/otus")
    config.add_route(
        "get_study_otus_slash", "/v{api_version:[123]}/study/{study_id}/otus/"
    )
    config.add_route(
        "get_study_otumap", "/v{api_version:[123]}/study/{study_id}/otumap"
    )
    config.add_route(
        "get_study_otumap_slash", "/v{api_version:[123]}/study/{study_id}/otumap/"
    )
    config.add_route("get_study_meta", "/v{api_version:[123]}/study/{study_id}/meta")
    config.add_route(
        "get_study_meta_slash", "/v{api_version:[123]}/study/{study_id}/meta/"
    )
    #
    # GENERIC routes
    #
    config.add_route(
        "get_docstore_config",
        "/v{api_version:[123]}/{doc_type_name}/store_config",
    )
    config.add_route(
        "docstore_push_failure", "/v{api_version:[123]}/{doc_type_name}/push_failure"
    )
    config.add_route("doc_list", "/v{api_version:[123]}/{doc_type_name}/doc_list")
    #
    # TREE COLLECTION ROUTES
    #
    config.add_route(
        "list_all_collection_ids", "/v{api_version:[123]}/collections/collection_list"
    )
    config.add_route(
        "collection_properties", "/v{api_version:[123]}/collections/properties"
    )
    config.add_route(
        "find_trees_in_collections", "/v{api_version:[123]}/collections/find_trees"
    )
    config.add_route(
        "find_collections", "/v{api_version:[123]}/collections/find_collections"
    )
    config.add_route("create_collection", "/v{api_version:[123]}/collection/")
    config.add_route(
        "collection_CORS_preflight",
        "/v{api_version:[123]}/collection/{collection_id:.*}",
        request_method="OPTIONS",
    )
    config.add_route(
        "fetch_collection",
        "/v{api_version:[123]}/collection/{collection_id:.*}",
        request_method="GET",
    )
    config.add_route(
        "update_collection",
        "/v{api_version:[123]}/collection/{collection_id:.*}",
        request_method="PUT",
    )
    config.add_route(
        "delete_collection",
        "/v{api_version:[123]}/collection/{collection_id:.*}",
        request_method="DELETE",
    )
    #
    # TAXONOMIC AMENDMENT ROUTES
    #
    config.add_route(
        "list_all_amendment_ids", "/v{api_version:[123]}/amendments/amendment_list"
    )
    config.add_route("list_all_amendments", "/v{api_version:[123]}/amendments/list_all")
    config.add_route("create_amendment", "/v{api_version:[123]}/amendment/")
    config.add_route(
        "amendment_CORS_preflight",
        "/v{api_version:[123]}/amendment/{amendment_id}",
        request_method="OPTIONS",
    )
    config.add_route(
        "fetch_amendment",
        "/v{api_version:[123]}/amendment/{amendment_id}",
        request_method="GET",
    )
    config.add_route(
        "update_amendment",
        "/v{api_version:[123]}/amendment/{amendment_id}",
        request_method="PUT",
    )
    config.add_route(
        "delete_amendment",
        "/v{api_version:[123]}/amendment/{amendment_id}",
        request_method="DELETE",
    )
