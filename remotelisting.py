#!/usr/bin/env python

#import curses
#from curses import wrapper
#import curses.textpad
#import re
from blessings import Terminal
import time
import os
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
	for i in listings:
		print str(i) + '\n'
#def main():
#	t = Terminal()

if __name__ == "__main__":
	getGames()
	