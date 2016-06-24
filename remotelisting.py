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
		print str(listings[i][10]) + '\n'
		#print Games[i].s

	#eventually I want to get the listings remotely from server using server config
	#i think i can send my own objects with perspective broker and call remote methods

#def main():
#	t = Terminal()

if __name__ == "__main__":
	getGames()
	