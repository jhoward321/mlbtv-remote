import unittest
import sys
import datetime
sys.path.append('../')
import server
from MLBviewer import *


class ServerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = server.app.test_client()
        self.config = server.getConfig()

    def test_getConfig(self):
        """Test getConfig helper function returns a config object"""

        cfg = server.getConfig()
        self.assertIsInstance(cfg, MLBConfig,
                              msg='Returned object is not a config object!')

    def test_getGames(self):
        """Test getGames helper function for different arguments"""

        example_date = datetime.date(2016, 9, 7)
        team_code = 'atl'
        no_args = server.getGames()
        only_date = server.getGames(date=example_date)
        only_team = server.getGames(team=team_code)
        both_args = server.getGames(date=example_date, team=team_code)
        # Test no args
        self.assertIsInstance(no_args, list,
                              msg='Returned schedule is not a list (no args)')
        # Test specific date
        self.assertIsInstance(only_date, list,
                              msg='Testing only date failed')
        self.assertIsInstance(only_date[0], server.Listing,
                              msg='Not a list of Listing objects')
        # Test specific team
        self.assertIsInstance(only_team, list,
                              msg='Testing 1 team did not return a list')
        self.assertEqual(len(only_team), 1,
                         msg='Team test returned too many Listings')
        # Test date and team
        self.assertIsInstance(both_args, list,
                              msg='Testing both did not return a list')
        self.assertEqual(len(both_args), 1,
                         msg='Date and team test returned too many Listings')

    def test_GameList(self):
        """Test GameList to make sure that its correctly returning games"""

        test_date = 'date=2016-09-07'
        rv = self.app.get('/schedule', query_string=test_date)
        assert b'Atlanta Braves at Washington Nationals' in rv.data
        rv2 = self.app.get('/schedule/atl', query_string=test_date)
        assert b'Atlanta Braves at Washington Nationals' in rv.data

if __name__ == '__main__':
    unittest.main()
