# pip install Flask-Restless
from flask import Flask#, jsonify
#reqparse is being deprecated for marshmallow in flask_restful
from flask_restful import Resource, Api, abort, inputs, reqparse#, marshal_with, reqparse, fields
from marshmallow import Schema, fields, pprint
from MLBviewer import *
import os, time, datetime#, json
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

# used to serialize Listing object
# This will be redone to serialize with marshmallow for future compatibility
# resource_fields = {
# 	'home': fields.String,
# 	'away': fields.String,
# 	'time': fields.DateTime,
# 	'summary': fields.String,
# 	#'tv': fields.List(fields.Raw),
# 	'status': fields.String
# }
# Marshmallow serialization for Listing object
class ListingSchema(Schema):
	home = fields.String()
	away = fields.String()
	time = fields.DateTime() #could also use old string format
	summary = fields.String()
	status = fields.String()
	tv = fields.List(fields.List(fields.String()))

# Object to store game info in a more readable form
class Listing(object):
	# each uglyGame is a list of different info about game - from MLBSchedule
	# 0 is the home and away teams
	# 1 is the start time
	# 2 is available TV streams - this is a list of lists where each list 
		# is stream info. First list is home teams stream info, second is away
	# 3 is radio streams
	# 4 is nothing?, 5 is game status ie if game is in progress, pregame, etc
	# 6 is an easy to parse general info about game
	# 7 is whether or not media is off or on
	# rest is mostly junk, 10 is available second audio feeds where available

	def __init__(self, uglyGame):
		self.home = uglyGame[0]['home']
		self.away = uglyGame[0]['away']
		self.status = uglyGame[5]
		self.tv = uglyGame[2]
		#self.time = uglyGame[1].strftime('%l:%M %p')
		self.time = uglyGame[1] #might be better to keep this as a time object
		self.summary = ' '.join(TEAMCODES[self.away][1:]).strip() + ' at ' +\
    		' '.join(TEAMCODES[self.home][1:]).strip()

		#self.c = padstr(uglyGame[5],2) + ": " +\
		#	uglyGame[1].strftime('%l:%M %p') + ': ' +\
		#	uglyGame[6]


# Show info about a particular game - probably need some sort of date thing
#class Game(Resource):
#	def get(self, game_id):

# Resource for starting a particular stream - return info about stream playing
# mlbplay.py takes in stream info in form mlbplay.py i=[inning] v=
class Play(Resource):
	# https://stackoverflow.com/questions/630453/put-vs-post-in-rest
	# GET will return info about current state (ie whether a game is playing)
	# PUT will play a certain game (ie change state)
	def put(self, game_id):
		global config
		global session
		global cur_game
		
		# First check state
		if config is None:
			config = getConfig()
		# might not even need session if its taken care of by mlbplay
		if session is None:
			try:
				session = getSession(config)
			# Will want to verify this error code is working correctly
			except MLBAuthError:
				abort(404,message="Could not login, check config")
				session = None
		if cur_game is None:
			#start playing game
			cur_game = game_id
			# Need some error handling here
			cmd = 'python mlbviewer-svn/mlbplay.py v=%s'%game_id
			player = subprocess.Popen(cmd.split())
		else:
			return cur_game


# shows a list of all games for a certain date
class GameList(Resource):

	# @marshal_with(resource_fields)
	# def get(self): #might wants **kwargs
	# 	# Argument parsing for game schedules
	# 	get_args = reqparse.RequestParser()
	# 	get_args.add_argument('date',type=inputs.date, help='Date of games')
	# 	#abort_no_games(date) - add this in with date support
	# 	args = get_args.parse_args(strict=True)
	# 	games = getGames(args.date)
	# 	return games

	#alternative with marshmallow - will probably want to implement error codes
	def get(self):
		get_args = reqparse.RequestParser()
		get_args.add_argument('date',type=inputs.date, help='Date of games')
		args = get_args.parse_args(strict=True)
		games = getGames(args.date)
		schema = ListingSchema(many=True) #to serialize collections of objects
		#change dump to dumps if want to return in json format
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
	                  'division_color' : 'red',
	                  'highlight_division' : 0,
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
	                  'coverage' : 'home',
	                  'show_inning_frames': 1,
	                  'use_librtmp': 0,
	                  'no_lirc': 0,
	                  'postseason': 0,
	                  'milbtv' : 0,
	                  'rss_browser': 'firefox -new-tab %s',
	                  'flash_browser': DEFAULT_FLASH_BROWSER}

		#create a default config then check for existing
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
def getGames(date=None):
	global config

	now = datetime.datetime.now()
	gametime = MLBGameTime(now)
	localtime = time.localtime()
	localzone = (time.timezone,time.altzone)[localtime.tm_isdst]
	localoffset = datetime.timedelta(0,localzone)
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
	#return listings

	# games is a more readable and useful form than listings

	games = []
	for game in listings:
		games.append(Listing(game))
	return games

# Create MLB.tv session - will need to send error code back on a failed login
def getSession(config):	
		try:
			session = MLBSession(user=config.get('user'),passwd=config.get('pass'),debug=config.get('debug'))
			session.getSessionData()
		except MLBAuthError as e:
			print "Login Failed"
			raise e
		config.set('cookies', {})
		config.set('cookies',session.cookies)
		config.set('cookie_jar', session.cookie_jar)
		return session
	
# initialize session, load config etc
def main():
	global config
	global session

	# Load config
	config = getConfig()
	# Login and start a session
	#session = getSession(config)

	#listings = getUglyListings()
	#print listings[0]#[6]
	#games = getGames()

	#for i in games:
	#	print i
		#newformat = {'home': i.home, 'away' : i.away, 's' : i.s}
		#print json.dumps(newformat)

# Api Routings - subject to change
api.add_resource(GameList,'/schedule', '/')
api.add_resource(Play,'/play/<game_id>')
# api.add_resource(Game,'/play/<game_id>')

if __name__ == "__main__":
	main()
	app.run(debug=True)