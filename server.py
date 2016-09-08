# -*- coding: utf-8 -*-

from flask import Flask
from flask_restful import Resource, Api, abort, inputs, reqparse
from marshmallow import Schema, fields, pprint
from MLBviewer import *
import os
import time
import datetime
import threading
import signal
import subprocess


# Globals
app = Flask(__name__)
api = Api(app)

config = None
cur_game = None
player = None
cleanupEvent = None


class ListingSchema(Schema):
    """Marshmallow schema for serializing Listing objects

    Attributes:
        away (str): away team
        home (str): home team
        playing (str): whether a stream is active or not
        status (str): status code of whether game is in play, over, etc
        summary (str): basic summary of the game info
        time (str): time of a game
        tv (list): list of tv streams available for a game
    """
    home = fields.String()
    away = fields.String()
    time = fields.DateTime()
    summary = fields.String()
    status = fields.String()
    playing = fields.String()
    tv = fields.List(fields.List(fields.String()))


class Listing(object):

    """This class is used to store game info in a more readable form.
       The listings provided from mlbviewer (uglyGame) provide lists with
       useful info at the following indices:
        - 0 is the home and away teams
        - 1 is the start time
        - 2 is available TV streams. This is a list where each list is
          stream info. First list is home team's stream, second is away
        - 3 is radio streams (not yet implemented)
        - 4 is typically empty - might be a special type of stream
        - 5 is game status ie if a game is in progress, pregame, etc
        - 6 is easy to parse general info about the game
        - 7 is whether media is off or on
        - rest is mostly junk, 10 is available second audio feeds

    Attributes:
        away (TYPE): away team
        home (TYPE): home team
        playing (TYPE): whether a stream is active or not
        status (TYPE): status code of whether game is in play, over, etc
        summary (TYPE): basic summary of the game info
        time (TYPE): time of a game
        tv (TYPE): list of tv streams available for a game
    """

    def __init__(self, uglyGame):
        """Initilization function for game Listing object

        Args:
            uglyGame (list): List containing lists of game info from
            the MLBSchedule class
        """
        self.home = uglyGame[0]['home']
        self.away = uglyGame[0]['away']
        self.status = uglyGame[5]
        self.tv = uglyGame[2]
        self.playing = uglyGame[7]
        self.time = uglyGame[1]
        self.summary = ' '.join(TEAMCODES[self.away][1:]).strip() + ' at ' +\
            ' '.join(TEAMCODES[self.home][1:]).strip()


class Play(Resource):
    """flask_restful Resource for selecting an MLBTv game"""

    def put(self, team_code):
        """Start game and return info about the game. Called with an HTTP PUT request

        TODO: implement additional stream options, have more error checking for
        when media is not yet available, figure out minor synch issue,
        figure out speed/inning issue. Speed seems to only work for 1200/1800

        Args:
            team_code (str): team code used to specify game

        Request Params:
            date (str): date of game in form YYYY-mm-dd.
            inning (str): inning to start stream in form t[0-9] or b[0-9]
            speed (int): bitrate of stream to watch

        Returns:
            Listing: a Listing object of the newly selected game
        """
        global cur_game
        global player
        global cleanupEvent

        if team_code and team_code not in TEAMCODES:
            abort(400, message="Invalid teamcode")

        # Setup valid requests
        # TODO: implement more stream options, fix innings/speed implementation
        request_args = reqparse.RequestParser()
        request_args.add_argument('date',
                                  type=inputs.date,
                                  help='Date of game in form [yyyy]-[mm]-[dd]')
        request_args.add_argument('inning',
                                  type=inputs.regex('^[tb]([1-9]|1[0-9])$'),
                                  help='Inning must be in form t[inning] or'
                                  'b[inning]. Ex: t9 for top of the 9th')
        request_args.add_argument('speed',
                                  type=inputs.regex('^(300|500|1200|1800|2400)$'),
                                  help='Valid speeds are 300, 500, 1200, 1800, and 2400')

        parsed_args = request_args.parse_args(strict=True)
        serialization_schema = ListingSchema()
        start_stream_cmd = 'python mlbplay.py'

        # Alter command string based off arguments
        if parsed_args.inning is not None:
            inning = ' i={}'.format(parsed_args.inning)
            start_stream_cmd += inning

        if parsed_args.speed is not None:
            speed = ' p={}'.format(parsed_args.speed)
            start_stream_cmd += speed

        if parsed_args.date is not None:
            date = parsed_args.date.strftime(' j=%m/%d/%y')
            start_stream_cmd += date

        team = ' v={}'.format(team_code)
        print start_stream_cmd
        start_stream_cmd += team
        print start_stream_cmd

        # Case where nothing playing
        if player is None:
            cleanupEvent.clear()

        # Case where a game is already playing
        # TODO: Fix occasional synchronization issue
        else:
            player.send_signal(signal.SIGINT)
            cleanupEvent.wait()

        cur_game = getGames(parsed_args.date, team_code)

        with open(os.devnull, "w") as devnull:
            # TODO: make mlbviewer directory configurable
            player = subprocess.Popen(start_stream_cmd.split(),
                                      cwd='mlbviewer-svn/',
                                      stdout=devnull,
                                      stderr=subprocess.PIPE)
            errorThread = threading.Thread(target=checkAlive,
                                           args=(cleanupEvent,)).start()

        cleanupEvent.clear()
        serialized_game_info = serialization_schema.dump(cur_game[0]).data
        return serialized_game_info, 200


class Stop(Resource):
    """flask_restful Resource for stopping a stream. Does nothing
       if no game is playing.
    """
    def get(self):
        """Stop MLBTv stream. Called with an HTTP GET request

        Returns:
            status_code: http status code of the request
        """
        global player
        global cleanupEvent
        if player is None:
            abort(406, message="No game currently playing")
        else:
            player.send_signal(signal.SIGINT)
            cleanupEvent.wait()
            return 200


class GameList(Resource):
    """flask_restful Resource for retrieving game schedule for a specified date
    """
    def get(self, team_code=None):
        """Retrieve a single team's game for a date, or all the games for a date.

        Args:
            team_code (None, optional): used if you only want info for 1 game.

        Request Params (optional):
            date (str): date of game in form YYYY-mm-dd. Defaults to today

        Returns:
            ListType: list object of game Listing objects. List has 1 Listing
            if a team_code was specified.
        """

        if team_code and team_code not in TEAMCODES:
            abort(404, message="Invalid teamcode")

        # Setup valid requests
        request_args = reqparse.RequestParser()
        request_args.add_argument('date', type=inputs.date, help='Date of games')

        parsed_args = request_args.parse_args(strict=True)
        games = getGames(parsed_args.date, team_code)

        # Make sure there was no error in retrieving games
        try:
            numgames = len(games)
            if numgames == 0:
                abort(404, message="Could not retrieve schedule for "
                      "this request. No games on this date")
        # if theres a type error then a -1 error code was returned
        except TypeError:
            abort(404, message="Could not retrieve schedule for this request.")

        serialization_schema = ListingSchema(many=True)
        serialized_game_info = serialization_schema.dump(games).data
        return serialized_game_info


def checkAlive(cleanupEvent):
    """Helper function spawned in a separate thread to detect when a stream ends

    Args:
        cleanupEvent (Event): a threading Event object for synchronization
    """
    global cur_game
    global player

    try:
        error = player.communicate()[1]
    except AttributeError, e:
        return

    # Due to constraints of python subprocesses,
    # I have to manually search for exceptions
    if "Traceback" in error:
        print error
    cur_game = None
    player = None
    # tell main thread that cleanup has finished
    cleanupEvent.set()


def getConfig():
    """Helper function to load mlbviewer config options or load default options
       if no config file exists.

    Returns:
        MLBConfig: MLBConfig object
    """
    config_dir = os.path.join(os.environ['HOME'], AUTHDIR)
    config_file = os.path.join(config_dir, AUTHFILE)
    mlbviewer_defaults = {'speed': DEFAULT_SPEED,
                          'video_player': DEFAULT_V_PLAYER,
                          'audio_player': DEFAULT_A_PLAYER,
                          'audio_follow': [],
                          'alt_audio_follow': [],
                          'video_follow': [],
                          'blackout': [],
                          'favorite': [],
                          'use_color': 1,
                          'favorite_color': 'cyan',
                          'free_color': 'green',
                          'division_color': 'red',
                          'highlight_division': 0,
                          'bg_color': 'xterm',
                          'show_player_command': 0,
                          'debug': 0,
                          'curses_debug': 0,
                          'wiggle_timer': 0.5,
                          'x_display': '',
                          'top_plays_player': '',
                          'max_bps': 2500,
                          'min_bps': 1200,
                          'live_from_start': 0,
                          'use_nexdef': 0,
                          'use_wired_web': 1,
                          'adaptive_stream': 0,
                          'coverage': 'home',
                          'show_inning_frames': 1,
                          'use_librtmp': 0,
                          'no_lirc': 0,
                          'postseason': 0,
                          'milbtv': 0,
                          'rss_browser': 'firefox -new-tab %s',
                          'flash_browser': DEFAULT_FLASH_BROWSER}

    #  create a default config then check for existing
    config = MLBConfig(mlbviewer_defaults)

    try:
        os.lstat(config_file)
    except:
        try:
            os.lstat(config_dir)
        except:
            dir = config_dir
        else:
            dir = None
        config.new(config_file, mlbviewer_defaults, dir)

    config.loads(config_file)

    return config


def getGames(date=None, team=None):
    """Helper function to get game schedule from MLBSchedule and convert
       it to a useful form.

    Args:
        date (None, optional): Date of games to return. Default is current date
        team (None, optional): optional team code to return game for 1 team

    Returns:
        list: Returns a list of game Listing objects or empty list if specifed
              game does not exist. Returns -1 if there was an error
    """
    global config

    if config is None:
        config = getConfig()

    now = datetime.datetime.now()
    gametime = MLBGameTime(now)
    localtime = time.localtime()
    localzone = (time.timezone, time.altzone)[localtime.tm_isdst]
    localoffset = datetime.timedelta(0, localzone)
    eastoffset = gametime.utcoffset()

    # current datetime object adjusted for timezones
    view_day = now + localoffset - eastoffset
    # get a timedelta between current (adjusted) date and provided date
    try:
        dateOffset = date.date() - view_day.date()
    except AttributeError:
        dateOffset = datetime.timedelta(0)

    view_day = view_day + dateOffset
    sched_date = (view_day.year, view_day.month, view_day.day)

    try:
        mlbsched = MLBSchedule(ymd_tuple=sched_date)
        ugly_listings = mlbsched.getListings(config.get('speed'),
                                             config.get('blackout'))
    except (MLBUrlError, MLBXmlError):
        print "Could not fetch schedule"
        return -1

    pretty_listings = []

    if team is None:
        for game in ugly_listings:
            pretty_listings.append(Listing(game))
    else:
        for game in ugly_listings:
            if team in game[0].values():
                pretty_listings.append(Listing(game))
    return pretty_listings


# Api Routings
api.add_resource(GameList, '/schedule/<team_code>', '/', '/schedule')
api.add_resource(Play, '/play/<team_code>')
api.add_resource(Stop, '/stop')

if __name__ == "__main__":
    config = getConfig()
    cleanupEvent = threading.Event()
    # app.run(debug=True)
    app.run(host='0.0.0.0')
