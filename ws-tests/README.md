This directory has a simple testing setup for testing the api.opentreeoflife.org 
web services. Either write test.conf or run one of the 2*conf.sh scripts
before you run the tests.

Run all of the tests using:

    $ sh run_tests.sh

*Details*

  * opentreetesting.py contains some helpful utilities for writing tests
        using python, and reading in a config file that controls the domain
        that the tests are run against.
  * test.conf is the config file.
  * 2globalconf.sh copies the global testing config to the active location
  * 2localconf.sh copies the local testing config to the active location.
  * test_*.py should take no arguments and use its exit code to indicate
        passing or failing the tests.
  * run_tests.sh runs all of the test_*.py files and summarizes the number
        of tests and failures.
  * to suppress tests that have side effects (PUT/POST), set configuration
    parameter allowwrite in the \[host\] section to false
  * configuration settings may be made from the command line; these
    override settings from test.conf.  They are passed as command line
    arguments of the form section:param=value, e.g. host:allowwrite=false

If VERBOSE_TESTING is in the env when you execute a test, you'll get more
verbose output.

