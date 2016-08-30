# pip install Flask-Restless, rq, need redis-server
from flask import Flask
from flask_restful import Resource, Api, abort, inputs, reqparse
from marshmallow import Schema, fields, pprint
from MLBviewer import *
# from redis import Redis
# from rq import Queue
import os
import time
import datetime
import threading
import signal
import subprocess


app = Flask(__name__)
api = Api(app)

# Session placeholder
session = None
# Config placeholder
config = None
# Current game placeholder
cur_game = None
# Media player process placeholder
player = None
# Event object for synchronizing threads
cleanupEvent = threading.Event()


class ListingSchema(Schema):
    home = fields.String()
    away = fields.String()
    time = fields.DateTime()
    summary = fields.String()
    status = fields.String()
    playing = fields.String()
    tv = fields.List(fields.List(fields.String()))


class Listing(object):

    """ This class is used to store game info in a more readable form.
        The listings provided from the mlbviewer (uglyGame) provide lists with
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
    """

    def __init__(self, uglyGame):
        self.home = uglyGame[0]['home']
        self.away = uglyGame[0]['away']
        self.status = uglyGame[5]
        self.tv = uglyGame[2]
        self.playing = uglyGame[7]
        #  self.time = uglyGame[1].strftime('%l:%M %p')
        self.time = uglyGame[1]
        self.summary = ' '.join(TEAMCODES[self.away][1:]).strip() + ' at ' +\
            ' '.join(TEAMCODES[self.home][1:]).strip()

        #  self.c = padstr(uglyGame[5],2) + ": " +\
        #   uglyGame[1].strftime('%l:%M %p') + ': ' +\
        #   uglyGame[6]


# helper function running in separate thread to check if player had errors
# will add more functionality here such as parsing different errors
def checkAlive(cleanupEvent):
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
    cleanupEvent.set()  # tell other thread that cleanup has finished


# Resource for starting a particular stream - return info about stream playing
# mlbplay.py takes in stream info in form mlbplay.py i=[inning] v=


class Play(Resource):
    # https://stackoverflow.com/questions/630453/put-vs-post-in-rest
    # GET will return info about current state (ie whether a game is playing)
    # PUT will play a certain game (ie change state)
    # Think i want to have teamcode url, and then date, inning and speed
    def put(self, team_code):

        global cur_game
        global player
        global cleanupEvent

        # 1. Check for options - teamcode required, rest optional
        # only teamcode is required,
        # Want to be able to specify team, date, inning, and speed
        # Might eventually add nexdef support but not now
        # STREAM_SPEEDS = ( '300', '500', '1200', '1800', '2400' )
        get_args = reqparse.RequestParser()
        get_args.add_argument('date', type=inputs.date,
                              help='Date of game in form [yyyy]-[mm]-[dd]')
        get_args.add_argument('inning',
                              type=inputs.regex('^[tb]([1-9]|1[0-9])$'),
                              help='Inning must be in form t[inning] or'\
                              'b[inning]. Ex: t9 for top of the 9th')
        get_args.add_argument('speed',
                              type=inputs.regex('^(300|500|1200|1800|2400)$'),
                              help='Valid speeds are 300, 500, 1200, 1800, and 2400')
        args = get_args.parse_args(strict=True)
        schema = ListingSchema()

        if team_code and team_code not in TEAMCODES:
            abort(400, message="Invalid teamcode")

        cmd = 'python mlbplay.py v={}'.format(team_code)

        if args.date is not None:
            date = args.date.strftime(' j=%m/%d/%y')
            cmd += date
        if args.inning is not None:
            cmd += ' i={}'.format(args.inning)
        if args.speed is not None:
            cmd += ' p={}'.format(args.speed)

        # Case where nothing playing
        if player is None:
            cleanupEvent.clear()
        # Case where a game is already playing
        # There is a bug here with multiple simultaneous requests
        # where a request will hang until the player is killed
        # Will be fixed in future versions - need a redis task queue
        else:
            player.send_signal(signal.SIGINT)
            # cleanupEvent.wait(5.0)
            cleanupEvent.wait()

        cur_game = getGames(args.date, team_code)
        with open(os.devnull, "w") as devnull:
            player = subprocess.Popen(cmd.split(), cwd='mlbviewer-svn/',
                                      stdout=devnull,
                                      stderr=subprocess.PIPE)
            errorThread = threading.Thread(target=checkAlive,
                                           args=(cleanupEvent,)).start()
        cleanupEvent.clear()
        return schema.dump(cur_game[0]).data, 202
        # return cur_game, 202

# Stop game if one is currently playing, otherwise do nothing

class Stop(Resource):
    def get(self):
        global player
        global cleanupEvent
        if player is None:
            abort(406, message="No game currently playing")
        else:
            player.send_signal(signal.SIGINT)
            cleanupEvent.wait()
            return 204


# shows a list of all games for a certain date
class GameList(Resource):

    def get(self, team_code=None):
        get_args = reqparse.RequestParser()
        get_args.add_argument('date', type=inputs.date, help='Date of games')
        args = get_args.parse_args(strict=True)

        # 1st check for an invalid team code
        if team_code and team_code not in TEAMCODES:
            abort(404, message="Invalid teamcode")

        games = getGames(args.date, team_code)
        # Make sure there was no error in retrieving games
        try:
            numgames = len(games)
            if numgames == 0:
                # Want to verify that this is actually whats always happening when this code is called
                abort(404, message="Could not retrieve schedule for "\
                      "this request. No games on this date")
        # if theres a type error then a -1 error code was returned
        except TypeError:
            abort(404, message="Could not retrieve schedule for this request.")

        schema = ListingSchema(many=True)

        return schema.dump(games).data

# Load config or create new one if one doesn't exist


def getConfig():
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

# Get game listings - takes in an optional date if current day isn't wanted
# Returns a list of games. Specifying a team will return a list with only that one game.
# Returning a list of only one game makes it easier to reuse code than returning the game data structure itself


def getGames(date=None, team=None):
    global config

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
        listings = mlbsched.getListings(
            config.get('speed'),
            config.get('blackout'))
    except (MLBUrlError, MLBXmlError):
        print "Could not fetch schedule"
        return -1

    # games is a more readable and useful form than listings
    # return entire schedule if a team is not mentioned specific game if mentioned - empty list if specified game doesnt exist
    games = []
    #  print "Team is {}".format(team)
    if team is None:
        for game in listings:
            games.append(Listing(game))
    else:
        for game in listings:
            if team in game[0].values():
                games.append(Listing(game))
    return games

# Create MLB.tv session - will need to send error code back on a failed login


def getSession(config):
        try:
            session = MLBSession(user=config.get('user'), passwd=config.get('pass'), debug=config.get('debug'))
            session.getSessionData()
        except MLBAuthError as e:
            print "Login Failed"
            raise e
        config.set('cookies', {})
        config.set('cookies', session.cookies)
        config.set('cookie_jar', session.cookie_jar)
        return session

# initialize session, load config etc


def main():
    global config
    global session

    # Load config
    config = getConfig()
    # Login and start a session
    # session = getSession(config)

    # listings = getUglyListings()
    # print listings[0]#[6]
    # games = getGames()

    # for i in games:
    #   print i
    # newformat = {'home': i.home, 'away' : i.away, 's' : i.s}
    # print json.dumps(newformat)

# Api Routings - subject to change
api.add_resource(GameList, '/schedule/<team_code>', '/', '/schedule')  # probably want to add date options here
api.add_resource(Play, '/play/<team_code>')
api.add_resource(Stop, '/stop')
# api.add_resource(Game,'/play/<game_id>')

if __name__ == "__main__":
    main()
    app.run(debug=True)
