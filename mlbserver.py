
import os
from twisted.internet.protocol import Protocol
#from MLBviewer import * #this will change as I determine what I actually need here
from MLBviewer import AUTHDIR, AUTHFILE, MLBConfig, MLBSession, MLBAuthError

#lets use a custom twisted protocol to handle the different event
#need to find a secure method of communication
	#https://twistedmatrix.com/documents/current/core/howto/ssl.html
#need to tell receiver what game to play
#need to tell commander whether or not a game is playing
	# if a game is playing, maybe give controls?
#close current game if another is chosen
#pass info to server about what bitrate and quality

#maybe allow multiple types of interfaces such as web or commandline
	#I think using normal http will give me the most options here
	#other options are spin my own, or use AMP which is probably more secure
class Command(Protocol):
	def __init__(self, factory):
		self.factory = factory


class Backend(object):
	def __init__(self):
		self.config = getConfig
		self.session = getSession
		self.player = None
		self.game = None
	#helper function to create or load current config file
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
	#function to start mlb.tv session
	def getSession(self):	
		try:
			self.session = MLBSession(user=self.config.get('user'),passwd=self.config.get('pass'),debug=self.config.get('debug'))
			self.session.getSessionData()
		except MLBAuthError:
			print "Login Failed"
			exit(-1)
		self.config.set('cookies', {})
		self.config.set('cookies',self.session.cookies)
		self.config.set('cookie_jar', self.session.cookie_jar)



if __name__ == "__main__":

	