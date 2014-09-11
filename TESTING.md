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

IMPORTANT: The tests create bogus studies. So do not use the real (OpenTreeOfLife/phylesystem-1) repo as your shard!!!

2. launch an instance of web2py with the phylesystem-api linked in the applications folder.

2. `cp ws-tests/local.test.conf ws-tests/test.conf`

3. tweak test.conf by:
   1. correcting the `apihost` setting to point to the URL where you are running the 
        phylesystem-api.
   2. correcting the `parentsha` setting. Some of the tests use this sha as the parent
        for their commits. The value needs to be a SHA in the repo that is checkout
        as your repo_parent. 

4. create an environmental var with your GitHub OAUTH token. See https://github.com/OpenTreeOfLife/phylesystem-api/blob/master/docs/README.md#getting-a-github-oauth-token
for instructions on how to get the token. The name of the var should be GITHUB_OAUTH_TOKEN

    $ export GITHUB_OAUTH_TOKEN=0123456789012345678901234567890123456789
    

5. run the web-service tests by:


   $ cd ws-tests
   $ bash run_tests.sh


