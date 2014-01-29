import unittest
import os, sys
from oti_search import OTISearch
from ConfigParser import SafeConfigParser

class TestOTISearch(unittest.TestCase):
    @classmethod
    def setUp(self):
        conf = SafeConfigParser(allow_no_value=True)
        if os.path.isfile("../private/localconfig"):
            conf.read("../private/localconfig")
        else:
            conf.read("../private/config")

        if conf.has_option("apis", "oti_base_url")
            self.oti_base_url = conf.get("apis", "oti_base_url")
            self.api_base_url = "%s/db/data/ext/QueryServices/graphdb/" % (self.oti_base_url,)
        else:
            # fall back to older convention [TODO: remove this]
            self.host = conf.get("apis","oti_host")
            self.port = conf.get("apis","oti_port")
            self.api_base_url = "http://%s:%s/db/data/ext/QueryServices/graphdb/" % (self.host, self.port)

        self.oti = OTISearch(self.api_base_url)

    def test_tree(self):
        json = self.oti.do_search("tree",
            key="ot:ottTaxonName",
            value="Carex"
        )
        self.assertTrue("results" in json)
        results = json["results"]
        self.assertIsInstance(results, type(list()))

    def test_node(self):
        json = self.oti.do_search("node",
            key="ot:ottId",
            value="1000455",
        )
        self.assertTrue("results" in json)
        results = json["results"]
        self.assertIsInstance(results, type(list()))

    def test_study(self):
        json = self.oti.do_search("study",
            key="ot:studyPublicationReference",
            value="vorontsova"
        )
        self.assertTrue("results" in json)
        results = json["results"]
        self.assertIsInstance(results, type(dict()))

def suite():
    loader = unittest.TestLoader()
    testsuite = loader.loadTestsFromTestCase(TestOTISearch)
    return testsuite

def test_main():
    testsuite = suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity=2)
    result = runner.run(testsuite)

if __name__ == "__main__":
    test_main()
