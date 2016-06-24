#!/usr/bin/env python

#import curses
#from curses import wrapper
#import curses.textpad
#import re
from blessings import Terminal
import time
import os
import re
import json
import datetime
from twisted.internet.protocol import Protocol
from MLBviewer import MLBConfig, MLBGameTime, MLBSchedule, MLBUrlError, MLBXmlError
from MLBviewer import AUTHDIR, AUTHFILE, TEAMCODES, DEFAULT_SPEED

#by default we are going to rely on mlbviewer settings on destination
#future versions will add support for all the keyboard shortcuts and maybe remote config changes

#Basically I want to create a curses front end that will ask for the remote host, and save a list 
#of previously used hosts in a config file of sorts. Then it will use the normal listing stuff but 
#will redirect chosen things to the remote host. Will need an intermediate receiver as well.
#Can probably use twisted to 

#I think I want to emulate the mlbviewer curses interface, but send
#all commands back to the server instead of launching instance directly

#for client just need a minimum config for listings
#might eventually get these from server so dont need mlbviewer on client
class Listing:
	def __init__(self, uglyGame):
		self.home = uglyGame[0]['home']
		self.away = uglyGame[0]['away']
		self.s = s = uglyGame[1].strftime('%l:%M %p') + ': ' +\
       ' '.join(TEAMCODES[self.away][1:]).strip() + ' at ' +\
       ' '.join(TEAMCODES[self.home][1:]).strip()
		# self.c = padstr(uglyGame[5],2) + ": " +\
		# uglyGame[1].strftime('%l:%M %p') + ': ' +\
		# uglyGame[6]
	


def getConfig():

	config_dir = os.path.join(os.environ['HOME'], AUTHDIR)
	config_file = os.path.join(config_dir, AUTHFILE)
	mlbviewer_defaults = {'audio_follow': [],
                          'video_follow': [],
                          'blackout': [],
                          'favorite': [],
                          'speed': DEFAULT_SPEED}

	#create a minimum config to get listings then return
	config = MLBConfig(mlbviewer_defaults)
	config.loads(config_file)
	
	return config
#function to clean up listing into a more useful and readable format
#def niceListing(origList):
def getFullConfig():
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

def getGames():

	#get date and time information for local and eastern timezones
	now = datetime.datetime.now()
	gametime = MLBGameTime(now)
	localtime = time.localtime()
	localzone = (time.timezone,time.altzone)[localtime.tm_isdst]
	localoffset = datetime.timedelta(0,localzone)
	eastoffset = gametime.utcoffset()

	minconfig = getConfig()
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
			minconfig.get('speed'),
			minconfig.get('blackout'))
	except (MLBUrlError, MLBXmlError):
		print "Could not fetch schedule"
		return -1
	Games = []
	for i in range(len(listings)):
		Games.append(Listing(listings[i]))
		#each listing is a list of different info about game
		#0 is the home and away teams
		#1 is the start time
		#2 is available TV streams
		#3 is radio streams
		#4 is nothing?, 5 is game status ie if game is in progress, pregame, etc
		#6 is an easy to parse general info about game
		#7 is whether or not media is off or on
		# rest is mostly junk, 10 is available second audio feeds where available
		#print str(listings[i][10]) + '\n'
		#print Games[i].s

	#eventually I want to get the listings remotely from server using server config
	#i think i can send my own objects with perspective broker and call remote methods
	return Games
#function called by curses
def setupWindow(myscr,mycfg, games):
	#need to configure myscreen first
	listwin = MLBListWin(myscr, mycfg, games)
def main():
	t = Terminal()
	games = getGames()
	# for i in range(len(games)):
	# 	with t.location(0,t.height + i):
	# 		print games[i].s
	with t.fullscreen():
		with t.location(0,0):
			print t.underline(games[0].s) 
	while(1):
		x=1

	#might be able to use interface from MLBListWin, MLBTopWin,opt,help etc


if __name__ == "__main__":
	#getGames()
	main()
