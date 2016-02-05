# Open Tree Phylesystem API Documentation

This file documents the design of the Open Tree Phylesystem API, including requirements defined by
the [Open Tree of Life](http://opentreeoflife.org) community and software team
and the reasons for various "details of implementation".

See elsewhere for documentation on the APIs for other Open Tree components such as treemachine and taxomachine.

## Open Tree Phylesystem API Version 1 Methods

All API calls are specific to the API version, which is a part
of the URL. This allows for new versions of the Phylesystem API to come out
which are not backward-compatible, while allowing old clients
to continue working with older API versions.

**NOTE**: substituting `https://devapi` for `https://api` will let you acess the more "bleeding edge" 
deployments of the code.

**NOTE**: Interface details are still under development and host names and paths are subject to change.


#### index

	curl https://api.opentreeoflife.org/phylesystem/v1/index
	
Returns a JSON structure with some simple documentation of the service that is running.

#### study_list

    curl https://api.opentreeoflife.org/phylesystem/v1/study_list

Returns a JSON array of all of the study IDs. 

#### phylesystem_config

    curl https://api.opentreeoflife.org/phylesystem/v1/phylesystem_config

Returns a JSON object with information about how the phylesystem doc store is 
configured. Including information about what sets of ID aliases map to the same
study. The returned struct is identical to what you get if you were to call
phylesystem.get_configuration_dict() on a local instance (using peyotl).


#### external_url

    curl https://api.opentreeoflife.org/phylesystem/external_url/9

Returns a JSON object with the canonical study ID and a url for the version of the 
study in the repo on the master branch:

    {
        "url": "https://raw.githubusercontent.com/OpenTreeOfLife/phylesystem-0/master/study/pg_09/pg_09/pg_09.json", 
        "study_id": "9"
    }

### Getting a Github Oauth token

Any API methods that allow writing (or changing the state of
the repo) require an authentication token. The examples below
assume a Github Oauth token is stored in the environment
variable

    $GITHUB_OAUTH_TOKEN

To get a Github OAuth token, you can use ```curl``` as well:

    curl -u USERNAME -X POST https://api.github.com/authorizations \
        --data '{"scopes":["public_repo"],"note":"description"}'

where USERNAME is your Github login/username. The above will
return JSON containing a "token" key, which is your new OAuth
token.

To put it into an environment variable:

    export GITHUB_OAUTH_TOKEN=codecafe

In the Open Tree curation webapp, we obtain this when a user logs into the
site via Github. Github returns a persistent token that streamlines
authentication in the future. (Basically, the user shouldn't need to login
again unless they revoke access to the curation app on Github.)

Here are other tips on managing auth tokens programmatically:

http://developer.github.com/v3/oauth/#get-or-create-an-authorization-for-a-specific-app

### WIP branches

We use "WIP" to stand for "Work in progress" branch. The naming convention
for these branches are:

    <curator github login>_study_<study #>_<WIP counter>

So if `mtholder` has 2 WIPs for study 9, they will show up as:

    mtholder_study_9_0
    mtholder_study_9_1

As discussed below, WIPs are created on a PUT. They are merged back to master and deleted
if the master's version of the study has not advanced in the interim between
GET and PUT. Thus, the WIPs are often very ephemeral and not 
noticeable by the user.

If the master has advanced, the WIP will be retained so that future PUT
operations by the curator will be guaranteed to be conflict-free 
updates somewhere in the repo. A call to `merge` will be needed to
merge the updated content from the master into the WIP. After the
merge (and subsequent PUTs) succeed, then the WIP should be 
able to merge to the master branch (resulting in the deletion of the WIP).

Clients of the Phylesystem API need never refer to the WIP names. All communication about
versions happens via SHA values.
However, they are returned in the `branch2sha` map from GET so that the 
curation client can remind the curator of any WIPs that they have started but 
not merged.


### Fetch a study

To get the entire NexSON of study N :

    curl https://api.opentreeoflife.org/phylesystem/v1/study/STUDYID.json
    
where STUDYID is of the form namespace_XX, for example pg_199 or ot_29.

Or equivalently, (after v2 has been it is deployed to the dev server):

    curl https://devapi.opentreeoflife.org/v2/study/STUDYID.json

#### GET arguments
*   The `output_nexml2json` arg specifies the version of the NeXML -> NexSON 
mapping to be used. See [the NexSON wiki](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish)
for details. Currently the only supported values are:
  *  0.0.0  badgerfish convention
  *  1.0.0  the first version of the "honey badgerfish" convention
  *  1.2.1  the "by ID" version of the "honey badgerfish" convention
The default for this parameter is 0.0.0, but this is subject to change.
Consider the call without the output_nexml2json argument to be brittle!
*   `starting_commit_SHA` This is optional 
which will return the version of the study from a specific commit sha.
If no `starting_commit_SHA` is given, GET will return study from master.



#### GET response

On success, a request for the full study in NexSON will return
 a JSON response similar to this:

    {
        "sha":  "e13343535837229ced29d44bdafad2465e1d13d8",
        "data": <Study NexSON object>,
        "branch2sha": WIP map
        "versionHistory": [history objects]
    }

*   `sha` is the parent sha of that GET and will need to be returned with 
edited study on a PUT. It can also be used as the `starting_commit_SHA`
in future GET calls to return the same data.
*   `data` will be the NexSON object using the syntactic convention
that was specified in `output_nexml2json` argument, and with the 
validator AnnotationEvent included.
*   `branch2sha` is an object summarizing the WIP branches for this study.
The keys will be the names of the branch; the value will be the commit `sha`
values that can be used in a GET call to get that version of the study. The
content of the key before the`_study_.*` regex pattern will be the name
of the curator whose PUT created the branch). An example `branch2sha` map is:

    {
        "mtholder_study_9_0": "f8d6ddacc2cef7a54847a4067ccb45915a4b4ebc",
        "master": "0841f890259686d74c7c1749a87026e1c4193ca0"
    }

*   `versionHistory` is a list of the history of edits to the study since
import or since transfer from phylografter (the edit history within phylografter
is not stored, although a curatorName field is maintained by phylografter). Each object will
contain the following information:

    {
    "author_email": <email of person who edited (if this is public in their GitHub profile)>, 
    "author_name": <name of person who edited (if this is public in their GitHub profile)>, 
    "message_subject": <summary line of the edit commit>,
    "date_ISO_8601": "2014-05-29 12:02:40 -0500",
    "date": "Thu, 29 May 2014 12:02:40 -0500", 
    "id": <commit sha>, 
    "relative_date": "7 days ago"
    }

##### Output conversion of GET
If the URL ends with a file extension, then the file type will be inferred for file conversion:
  * .nex -> NEXUS
  * .tre -> Newick
  * .nexml -> NeXML
  * .nexson, .json, or no extension -> NexSON

For NEXUS and Newick formats, by default tip labels will be those from the originally uploaded study.
Alternate labels can be accessed using `tip_label` argument. Values must be one of `ot:originallabel`, `ot:ottid`, or `ot:otttaxonname`.

e.g. 

    curl https://api.opentreeoflife.org/v2/study/pg_1144.nex/?tip_label=ot:ottid
    curl https://api.opentreeoflife.org/v2/study/pg_1144.nex/?tip_label=ot:otttaxonname

NexSON supports fine-grained access to parts of the study (see below).
NeXML can only be returned for the study. Newick and NEXUS formats can only return
the full study, trees or subtrees.


##### fine-grained access via GET
You can request just parts of the study using a syntax of alternating resource IDs and names:

  * `*/v1/study/pg_10/meta` returns a shell of information about the study but has null entries
    in place of the trees and otus. This is useful because the response is typically much
    smaller than the full study
  * `*/v1/study/pg_10/tree` returns an object with property names corresponding to the 
    IDs of the trees in the study and values being the tree objects.
  * `*/v1/study/pg_10/tree/ABC` is similar to the tree resource mentioned above, but only 
    the tree with ID of "ABC" will be included. A 404 will result if no such tree is found in the study.
    If a `bracket_info=true` argument is added to the call, then the ingroup will be the 
    newick segment between `[pre-ingroup-marker]` and `[post-ingroup-marker]` comments in the 
    newick
  * `*/v1/study/pg_10/tree/ABC?starting_commit_SHA=a2c48df995` is similar to the tree resource mentioned above, 
    except that rather than retrieving the most recent version of the tree "ABC", get the version indexed 
    by git commit SHA "a2c48df995".
  * `*/v1/study/pg_10/subtree/ABC?subtree_id=XYZ` is similar to the tree resource
    mentioned above, but only a subtree of the tree with ID of "ABC" will be included. The subtree
    will be the part of the tree that is rooted at the node with ID "XYZ". A 404 will result if no such 
    subtree is found in the study.
  * `*/v1/study/pg_10/subtree/ABC?subtree_id=ingroup` ingroup is a wildcard that can be used
    to designate the ingroup node of any tree (may give a 404 for a tree, if the ingroup node
    has not been specified by a curator).
  * `*/v1/study/pg_10/otus` the `study["nexml"]["otusById"]` object 
  * `*/v1/study/pg_10/otus/ABC` is similar to otus, but only the otus group with ID "ABC" 
    will be included.
  * `*/v1/study/pg_10/otu` returns the union of the `study["nexml"]["otusById"][*]["otuById"]` objects 
  * `*/v1/study/pg_10/otu/ABC` is similar to otu, but only the otu with ID "ABC"  will be included.
  * `*/v1/study/pg_10/otumap` will return an object that maps the original label for each OTU to 
    either an object or list of objects (if there were two tips that originally had the same label). The
    objects in the values field will have properties from the mapping: either "^ot:ottId" and/or 
    "^ot:ottTaxonName" fields, or they will be empty (if the OTU has not been mapped to OTT)
  * `*/v1/study/pg_10/file` returns a list of object describing the supplementary files associated with a study, including (in the "id" property) the fileID (see the next bullet point)
  * `*/v1/study/pg_10/file/xyz` returns the contents of the file with fileID `xyz` if that file is associated with study `pg_10`. Typically, you would call the `v1/study/STUDY_ID/file` method first, then choose the file you want and fetch it with this call.

By default all of the fine-grained access methods return NexSON 1.2.1 
Currently they do not support back translation to older versions of NexSON.
The tree related fine-grained access methods (`*/tree/*` and `*/subtree/*`) will also support NEXUS
or newick via calls like: `*/v1/study/pg_10/tree/ABC.nex`

When returning slices of data in NexSON using the fine-grained access URLs, the content returned will
simply be the requested data. The "sha", "branch2sha", and "versionHistory" properties will not be
included. Nor will the requested data be packaged in a "data" field.


### Updating a study

If you want to update a study, for example study = ot_10, with a file called
`10-modified.json`, use the following PUT command:

    curl -X PUT https://api.opentreeoflife.org/phylesystem/v1/study/ot_10.json?auth_token=$GITHUB_OAUTH_TOKEN\
    &starting_commit_SHA=e13343535837229ced29d44bdafad2465e1d13d8 --data-urlencode nexson@10-modified.json

(Note the escaped '&'). For large studies, it's faster to skip the URL-encoding and pass the NexSON data as binary:

    curl -X PUT 'https://api.opentreeoflife.org/phylesystem/v1/study/ot_10?auth_token=26b5a59d2cbc921bdfe04ec0e9f6cc05c879a761'\
    &starting_commit_SHA=e13343535837229ced29d44bdafad2465e1d13d8 --data-binary @10-modified.json --compressed

#### PUT arguments

**Required arguments**

*   `auth_token` is required, and is your [GitHub authorization token](https://github.com/OpenTreeOfLife/phylesystem-api/tree/master/docs#getting-a-github-oauth-token) 
*   `starting_commit_SHA` is required, and should be the commit SHA of the parent of the edited study.

**Optional arguments**

*  `commit_msg` is optional, but it is good practice to include it
*   `merged_SHA` is optional. If the master branch's version of this study has advanced
    a PUT will not be merged to master. The curation app will need to call 
    the merge URL (see below). That controller will return a `merged_SHA` value. 
    Calling PUT with this `merged_SHA` key-value pair as an argument, is a signal 
    that the curator has examined the changes that have been made to the master branch 
    and that he/she confirms that the edits are not incompatible. The presence of the `merged_SHA`
    argument will allow the branch to merge to master despite the fact that the master has advanced
    since `starting_commit_SHA`. Note that, if the master has advanced again since the 
    client calls the merge controller, the client will need to merge


Either form of this command will create a commit with the updated JSON on a branch of the form

    USERNAME_study_ID_i
    
where USERNAME is the authenticated users Github login and ID
is the study ID number, and i is an iterator for if the user has more than one branch open for that study.
If branch can be merged to master, it will be and the branch will be deleted.

#### PUT response

On success, it will return a JSON response similar to this:

    {
        "error": "0",
        "resource_id": "12",
        "branch_name": "usr_study_12_0",
        "description": "Updated study 12",
        "sha":  "e13343535837229ced29d44bdafad2465e1d13d8",
        "merge_needed": true,
    }


*   `error` is set to 0 on success. On failure, `error` will be set to 1.
*   `description` a textual description of what occurred. This will hold the details of the error (if `error` is 1)
*   `resource id` is the id of the study that was edited
*   `branch_name` is the WIP branch that was created. This is not useful (because the `sha`
is all that really matters), and may be deprecated
*   `sha` is the handle for the commit that was created by the PUT (if `error` was 0). This must be used as `starting_commit_SHA` in the next PUT (assuming that the curator wants a linear edit history)
*   `merge_needed` descibes whether the merge controller has to be called before the commit will
be included in the master branch. If false, then the WIP will have been deleted (so that the `branch_name` returned is stale)

If the study has moved forward on the master branch since `starting_commit_SHA`, the
content of this PUT will be successfully stored on a WIP, but the merge into master
will not happen automatically.
This merge will not happen even if there is no conflict. 
The client needs to use the MERGE 
controller to merge master into that branch, then PUT that branch including the 'merged_sha'
returned by the merge. 
Even if a `merged_sha` is included in the PUT,
`merge_needed` may still be `true`.
This happens if the master has moved forward since the merge was vetted.
Then a second merge and PUT with the new `merged_sha` is required.

Any PUT request attempting to update a study with invalid JSON
will be denied and an HTTP error code 400 will be returned.

[Here](https://github.com/OpenTreeOfLife/phylesystem-1/commit/c3312d2cbb7fc608a62c0f7de177305fdd8a2d1a) is an example commit created by the OpenTree API.

### Merge a study in a WIP branch

Merges to master are done automatically on PUTs when the version of the study on master has 
not moved forward from the version in the parent commit.
The MERGE controller merges master into outstanding WIP branch.
The merged output should be vetted by a curator, because the
merge can generate semantic conflicts even if not git (textual) conflicts arise.

To merge a study from master into a branch with a given `starting_commit_sha`

    curl -X POST https://api.opentreeoflife.org/phylesystem/v1/merge/?resource_id=9&starting_commit_SHA=152316261261342&auth_token=$GITHUB_OAUTH_TOKEN


If the request is successful, a JSON response similar to this will be returned:

        {
            "error": 0,
            "branch_name": "my_user_9_2",
            "description": "Updated branch",
            "sha": "dcab222749c9185797645378d0bda08d598f81e7",
            "merged_SHA": "16463623459987070600ab2757540c06ddepa608",
        }

`merged_SHA` must be included in the next PUT for this study (unless you are 
happy with your work languishing on a WIP branch instead of master).

If there is an error, an HTTP 400 error will be returned with a JSON response similar 
to this:

        {
            "error": 1,
            "description": "Could not merge master into WIP! Details: ..."
        }

### Creating a new study

To create a new study from a file in the current directory called ```study.json```:

    curl -X POST "https://api.opentreeoflife.org/phylesystem/v1/study/?auth_token=$GITHUB_OAUTH_TOKEN" --data-urlencode nexson@study.json

This will generate the output

    {
        "error": "0",
        "resource_id": "12",
        "branch_name": "usr_study_12_0",
        "description": "Updated study 12",
        "sha":  "e13343535837229ced29d44bdafad2465e1d13d8",
        "merge_needed": false
    }

See the PUT response for an explanation of the output.
For a new study merge_needed should always be `false`

POSTS fall into 2 general categories:
  1. With a study ID. These take the same arguments as a PUT, and are only to be used
        if a study is being added to the doc store, and it is known that it already
        has a valid, namespaced ID in another curation tool (such as phylografter).
        See the PUT documentation for the arguments.
  2. Studies without an ID:
     * import_from_location can be "IMPORT_FROM_UPLOAD" or some other string
     * cc0_agreement is checked if import_from_location="IMPORT_FROM_UPLOAD",
            if cc0_agreement is the 'true', then CC0 deposition will be noted
            in the metadata.
     * publication_reference', '')
     * import_method can be:
        * import-method-TREEBASE_ID should be used with treebase_id argument
        * import-method-NEXML should be used with nexml_fetch_url OR
                with nexml_pasted_string argument
        * import-method-PUBLICATION_DOI should be used with publication_DOI argument
        * import-method-PUBLICATION_REFERENCE' should be used with
                publication_reference argument

### Pushing the master branch to Github
IN FLUX!

This API method will push the master branch of the local Git repo
to the master on GitHub

    curl -X PUT https://api.opentreeoflife.org/phylesystem/v1/push/9

On success, it will return JSON similar to this:

    {
        "description": "Push succeeded",
        "error": 0
    }

If there is an error in syncing the local git repository with the remote, an HTTP 409 (conflict) error code will be returned with a JSON response of the form:

    {
        "error": 1,
        "description": "Could not push! Details: ..."
    }

where the description will contain a stacktrace.


### Using different author information

By default, the Phylesystem API uses the name and email associated with the Github Oauth token to assign provenance to API calls. To over-ride that you can provide ```author_name``` and ```author_email``` arguments:

    curl -X PUT 'https://api.opentreeoflife.org/phylesystem/v1/study/13.json?auth_token=$GITHUB_OAUTH_TOKEN&author_name=joe&author_email=joe@joe.com' --data-urlencode nexson@1003.json

## Not Yet Implemented Methods

The following methods have not been implemented yet.

### Searching, filtering, sorting, paginating studies

    # Add searching, sorting, pagination, filters on the query string
    curl https://api.opentreeoflife.org/phylesystem/v1/studies?q=mammal&sort=status,-date&page=3&filter=state-draft

### Listing your own studies (as a curator), sorted by status

This is the default __dashboard__ view for a logged-in curator. Of course it's
just a special case of the filtered list above.

    # the curator's "dashboard" is just a preset filter
    curl https://api.opentreeoflife.org/phylesystem/v1/studies?q=jimallman&sort=-status,-date&page=1&filter=state-draft

This and other "canned" views might have friendlier URLs:

    curl https://api.opentreeoflife.org/phylesystem/v1/studies/dashboard

    curl https://api.opentreeoflife.org/phylesystem/v1/studies/draft

    curl https://api.opentreeoflife.org/phylesystem/v1/studies/published

    curl https://api.opentreeoflife.org/phylesystem/v1/studies/latest


### Incorporating "namespaced" study identifiers from different sources

We need to avoid collisions between studies created in phylografter, the
Open Tree web curation tool, and other tools. Rather than keeping a global
counter or using GUIDs, we're planning to use a prefix for tool or system
that contributes Nexson studies to the repository.

The prefixes currently planned include:
- __ot__ for the [Open Tree curation tool](https://tree.opentreeoflife.org/curator/study)
- __pg__ for [phylografter](http://reelab.net/phylografter/)


These "namespaces" will appear in different forms, depending on context: 

- as CURIEs in NexSON or NeXML

    ```
    'nexml': { "@id": "ot:123", ... }
    ```
    ```
    <nexml id="pg:987" ... >
    ```

- as folders in the datastore (filesystem or git repo)

    ```
    ot/123.json
    pg/987.json
    ```

- as subpaths in RESTful URLs

    ```
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree
    https://api/phylesystem/v1/study/pg/987/tree
    ```
    
- as elements of WIP branch names (in a branching repo)

    ```
    jimallman_study_ot_123
    leto_study_pg_987
    ```

See related discussion in https://github.com/OpenTreeOfLife/api.opentreeoflife.org/issues/44

### Creating, fetching, updating subresources (not yet implemented)

We should be able to extend the RESTful style used for studies to manage
"subresources" (__trees__, __nodes__, __OTUs__?) within a study.  Where possible, this
would provide a uniform set of CRUD (create, retrieve, update,
delete) operations using URLs like:

    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/5
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/5/node/789
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/otu/456

Apart from normal elements in NexSON, we might also consider using this
convention for __supporting files__ and __annotations__ :

    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/file/3
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/file/alignment_data.xsl
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/annotation/456

Ideally, it would be good to also allow fetching (and more?) of sets of
related objects:

- contiguous __ranges__ of objects
- non-contiguous __sets__ of objects
- arbitrary sets of __mixed types__?

Here are some possible examples:

    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/1...4
    https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/1,5,8

The last case (arbitrary setes of mixed types) might include the cluster of
elements needed for a complex annotation. This would probably be handled
best in a more general diff/patch solution, probably in RPC style rather
than REST. Or as a choreographed series of RESTful operations on the
individual elements, as shown above.

See related discussion in https://github.com/OpenTreeOfLife/api.opentreeoflife.org/issues/4, https://github.com/OpenTreeOfLife/api.opentreeoflife.org/issues/32

### NexSON fragments and decomposition

It can be beneficial to load entire studies in memory, esp. to manage
integrity and relationships among study elements. Still, this can be
difficult when managing large NexSON documents, due to limitations in
working storage and network speed. Also, some operations can be applied
cleanly to parts of the whole, e.g., reading and manipulating a single
tree. 

We have considered a simple, general model for "decomposing" NexSON into
fragments, while ensuring that these can be reassembled exactly as before. This
might be as simple as removing an element (say, a tree) and replacing it with a
token that identifies this element in context. For example, here's a study:
    
    http://api.opentreeoflife.org/phylesystem/v1/study/ot/123

    ...
    "trees": {
        "@id": "trees10", 
        "@otus": "otus10", 
        "tree": [
            {
                "@id": "tree1", 
                "@label": "Untitled (#tree1)", 
                "edge": [
                ...
            }, 
            {
                "@id": "tree3", 
                "@label": "Untitled (#tree3)", 
                "edge": [
                ...
            }, 
    
Upon request, we might extract its first tree (_tree1_) as a fragment:

    http://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/1

    {
        "@id": "tree1", 
        "@label": "Untitled (#tree1)", 
        "edge": [
        ...
    } 

We can either use the URL to replace this element in an update, or we can leave a placeholder:

    http://api.opentreeoflife.org/phylesystem/v1/study/ot/123

    ...
    "trees": {
        "@id": "trees10", 
        "@otus": "otus10", 
        "tree": [
            {
                "@PLACEHOLDER": true, 
                "@type": "object", 
                "@href": "https://api.opentreeoflife.org/phylesystem/v1/study/ot/123/tree/1" 
            }, 
            {
                "@id": "tree3", 
                "@label": "Untitled (#tree3)", 
                "edge": [
                ...
            }, 

Placeholders like this should support loading a large NexSON document
"piecemeal" from a local or remote source, replacing placeholders with full
content as it arrives. 

Ideally these fragments could include ranges or sets
of elements, as described above. This would address known performance
challenges like large studies with "flat" collections (eg, tens of
thousands of OTUs in an array).

    http://api.opentreeoflife.org/phylesystem/v1/study/pg/987

    ...
    "otus": {
        "@id": "otus10", 
        "otu": [
            {
                "@PLACEHOLDER": true, 
                "@type": "range", 
                "@href": "https://api.opentreeoflife.org/phylesystem/v1/study/pg/987/otu/1...1000" 
            }, 
            {
                "@PLACEHOLDER": true, 
                "@type": "range", 
                "@href": "https://api.opentreeoflife.org/phylesystem/v1/study/pg/987/otu/1001...2000" 
            }, 
            ...

## Authors

Jonathan "Duke" Leto wrote the previous version of this API

Jim Allman, Emily Jane McTavish, and Mark Holder wrote the current version.
