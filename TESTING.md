# Setup for any testing

You'll need to have peyotl installed to run the tests.

Tests can be configured using `test.conf` or via command line arguments

See https://github.com/OpenTreeOfLife/germinator/blob/master/TESTING.md
for a description of how to put germinator's opentreetesting.py on your
PYTHONPATH.

    $ cd ws-tests
    $ ../../germinator/ws-tests/run_tests.sh -t . https://devapi.opentreeoflife.org

Use `export VERBOSE_TESTING=1` before running the test if you want to see
more explanations of the test skips and failures.

# Setup for tests against a local instance

To test locally you need to:
1. configure your `repo_parent` setting in you phyleystem-api/private/config
    This setting should refer to the *parent* of a directory that is a git
    clone of a phylesystem "shard". You can do this by 

    $ cd /my-favorite-dir
    $ mkdir shards
    $ cd shards
    $ git clone [the URL of the testing shard here]

    and then setting `repo_parent = /my-favorite-dir/shards`. You want the 
    shard that you check out to be a testing version of the phylesystem repo. 
    For example, Mark Holder forked https://github.com/OpenTreeOfLife/phylesystem-0
    to his own account on GH, so that he can checkout https://github.com/mtholder/phylesystem-0
    and use that directory as his repo_parent. That assures that there will not be
    clashes during testing with other developers. For the tests to complete, you 
    need to have studies 9 and 10, so do not simply use an empty git dir. 

IMPORTANT: The tests create bogus studies. So do 
NOT use the real (OpenTreeOfLife/phylesystem-1) repo 
as your shard!!!

2. If you are testing locally, launch an instance of web2py with the
phylesystem-api linked in the applications folder.


# Setup for tests that write to the data stores.

By default, these tests are skipped.

You cannot run these tests against the "production" server at api.opentreeofelife.org


1. create an environmental var with your GitHub OAUTH token. See https://github.com/OpenTreeOfLife/phylesystem-api/blob/master/docs/README.md#getting-a-github-oauth-token
for instructions on how to get the token. The name of the var should be GITHUB_OAUTH_TOKEN

    $ export GITHUB_OAUTH_TOKEN=0123456789012345678901234567890123456789

2. use the host.allowwrite=true argument when you run the tests (or put that
setting in your `ws-tests/test.conf` file):

   $ cd ws-tests
   $ ../../germinator/ws-tests/run_tests.sh -t . https://devapi.opentreeoflife.org host:allowwrite=true




# Details of the files in `ws-tests`

  * test.conf is the config file.
  * 2globalconf.sh copies the global testing config to the active location
  * 2localconf.sh copies the local testing config to the active location.
  * test_*.py should take no arguments and use its exit code to indicate
        passing (0), failing (1), or skipping (3) the tests
  * to allow tests that have side effects (PUT/POST), set configuration
    parameter allowwrite in the \[host\] section to true
  * configuration settings may be made from the command line; these
    override settings from test.conf.  They are passed as command line
    arguments of the form section:param=value, e.g. host:allowwrite=true

Here are some of the configuration settings: (all for 'host' section,
see test.conf for config file examples)

  * apihost - base URL for all tests, the part preceding "/v2",
    perhaps including a port number.  Value should start with 'http'
    and should not end with '/'.
  * translate - true or false, default false.  If true, URLs are first
    rewritten the same way the open tree apache server would rewrite
    them before being used in an HTTP request.  This is intended for
    local testing in the absence of a locally configured apache
    server.  This allows tests to be written in terms of advertised /v2
    URLs even if they are not directly supported by the web2py or neo4j server.

The `host:allowwrite=true` command line argument allows tests that have 
    side effects (e.g. writing to a phylesystem) to run. This can only 
    be invoked via the command line. The default for this setting is false.
    Useful for checking a production server.
  