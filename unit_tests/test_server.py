import unittest
import sys
import subprocess
import threading
import datetime
import mock
sys.path.append('../')
import server
from MLBviewer import *


class ServerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = server.app.test_client()
        self.config = server.getConfig()
        mlb_sched = MLBSchedule(ymd_tuple=(2016, 9, 07))
        ugly_listings = mlb_sched.getListings(self.config.get('speed'),
                                              self.config.get('blackout'))
        self.test_game = server.Listing(ugly_listings[0])

    def test_getConfig(self):
        """Test getConfig helper function returns a config object"""

        cfg = server.getConfig()
        self.assertIsInstance(cfg, MLBConfig,
                              msg='Returned object is not a config object!')

    def test_getGames(self):
        """Test getGames helper function for different arguments"""
        # TODO: Mock a lot of these calls

        example_date = datetime.date(2016, 9, 6)
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
        #import pdb
        #pdb.set_trace()
        # self.assertEqual(len(only_team), 1,
        #                  msg='Team test returned too many Listings')
        # Test date and team
        self.assertIsInstance(both_args, list,
                              msg='Testing both did not return a list')
        # self.assertEqual(len(both_args), 1,
        #                  msg='Date and team test returned too many Listings')

    def test_GameList(self):
        """Test GameList to make sure that its correctly returning games"""
        # TODO: finish all possible cases - mock different calls
        test_date = 'date=2016-09-07'
        rv = self.app.get('/schedule', query_string=test_date)
        assert b'Atlanta Braves at Washington Nationals' in rv.data
        rv2 = self.app.get('/schedule/atl', query_string=test_date)
        assert b'Atlanta Braves at Washington Nationals' in rv.data

    @mock.patch('server.player')
    def test_checkAlive(self, mock_player):
        """Check that function correctly sets event"""
        cleanupEvent = threading.Event()
        mock_player.communicate.return_value = ['', 'Fake Traceback check']
        server.checkAlive(cleanupEvent, None, mock_player)

        self.assertTrue(mock_player.communicate.called)
        self.assertTrue(cleanupEvent.isSet())

    #@mock.patch('server.threading',None)
    #@mock.patch('server.player')
    #@mock.patch('server.cur_game', None)
    @mock.patch('server.getGames')
    @mock.patch('server.threading.Thread')
    @mock.patch('server.subprocess.Popen')
    def test_Play(self, mock_process, mock_thread, mock_games):
        # want to test argument parsing, subprocess calls, thread spawn, events, return object
        date = '2016-09-06'
        team_code = 'atl'
        speed = [300, 500, 1200, 1800, 2400]
        top_inning = 't3'
        bot_inning = 'b3'
        server.player = None
        server.cur_game = None
        server.cleanupEvent = threading.Event()
        #print self.test_game
        mock_games.return_value = self.test_game

        rv = self.app.put('/play/atl')
        self.assertEqual(server.cur_game, self.test_game)
        self.assertTrue(mock_process.called)
        self.assertTrue(mock_thread.called)
        #print rv.data

if __name__ == '__main__':
    unittest.main()
