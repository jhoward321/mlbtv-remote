import unittest
import sys
sys.path.append('../')
import server
from MLBviewer import *


class ServerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = server.app.test_client()
        self.config = server.getConfig()

    def test_getConfig(self):
        cfg = server.getConfig()
        self.assertIsInstance(cfg, MLBConfig,
                              msg='Returned object is not a config object!')

    def test_getGames_noargs(self):
        # two possible cases - return a list of Listing instances
        # or return -1 when no games available
        games = server.getGames()
        self.assertIsNotNone(games)

if __name__ == '__main__':
    unittest.main()
