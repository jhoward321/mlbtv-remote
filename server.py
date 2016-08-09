# pip install Flask-Restless
from flask import Flask, jsonify
from flask_restful import Resource, Api, abort, reqparse, fields, marshal_with
from MLBviewer import *
import os, time, datetime, json

app = Flask(__name__)
api = Api(app)

# Session placeholder
session = None

# Config placeholder
config = None

#used to serialize Listing object
resource_fields = {
	'home': fields.String,
	'away': fields.String,
	'time': fields.String,
	's': fields.String
}

# Object to store game info in a more readable form
class Listing(object):
	def __init__(self, uglyGame):
		self.home = uglyGame[0]['home']
		self.away = uglyGame[0]['away']
		self.time = uglyGame[1].strftime('%l:%M %p')
		self.s = ' '.join(TEAMCODES[self.away][1:]).strip() + ' at ' +\
    		' '.join(TEAMCODES[self.home][1:]).strip()
		#self.c = padstr(uglyGame[5],2) + ": " +\
		#	uglyGame[1].strftime('%l:%M %p') + ': ' +\
		#	uglyGame[6]


# shows info about a game 
# class Game(Resource):
# 	def get(self, game_id):


# shows a list of all games for a certain date
class GameList(Resource):
	# date support will be added after i add date support to my listings
	@marshal_with(resource_fields)
	def get(self):
		#abort_no_games(date) - add this in with date support
		games = getGames()
		return games

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

# Clean up listings into a more readable format
def getGames():
	# each listing is a list of different info about game
	# 0 is the home and away teams
	# 1 is the start time
	# 2 is available TV streams
	# 3 is radio streams
	# 4 is nothing?, 5 is game status ie if game is in progress, pregame, etc
	# 6 is an easy to parse general info about game
	# 7 is whether or not media is off or on
	# rest is mostly junk, 10 is available second audio feeds where available
	listings = getUglyListings()
	Games = []
	for i in range(len(listings)):
		Games.append(Listing(listings[i]))
		#print str(listings[i][10]) + '\n'
		#print Games[i].s
	return Games

# Get game listings - ugly format from MLBSchedule
def getUglyListings():

	global config

	# get date and time information for local and eastern timezones
	now = datetime.datetime.now()
	gametime = MLBGameTime(now)
	localtime = time.localtime()
	localzone = (time.timezone,time.altzone)[localtime.tm_isdst]
	localoffset = datetime.timedelta(0,localzone)
	eastoffset = gametime.utcoffset()

	#once I'm farther along I will add time offset support

	view_day = now + localoffset - eastoffset
	sched_date = (view_day.year, view_day.month, view_day.day)
	#print view_day
	#print sched_date

	#get game listing for requested day (other dates to be added)
	try:
		mlbsched = MLBSchedule(ymd_tuple=sched_date)
		#print mlbsched
		listings = mlbsched.getListings(
			config.get('speed'),
			config.get('blackout'))
	except (MLBUrlError, MLBXmlError):
		print "Could not fetch schedule"
		return -1

	return listings

# initialize session, load config etc
def main():
	global config
	global session

	# Load config
	config = getConfig()

	#listings = getUglyListings()
	#print listings[0]#[6]
	#games = getGames()

	#for i in games:
	#	print i
		#newformat = {'home': i.home, 'away' : i.away, 's' : i.s}
		#print json.dumps(newformat)

# Setup the Api resource routing
api.add_resource(GameList,'/')

if __name__ == "__main__":
	main()
	app.run(debug=True)