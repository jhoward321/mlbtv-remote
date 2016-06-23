#!/usr/bin/env python

#import curses
#from curses import wrapper
#import curses.textpad
#import re
from blessings import Terminal
import time
import datetime
from twisted.internet.protocol import Protocol
from MLBviewer import MLBGameTime, MLBSchedule, MLBUrlError, MLBXmlError

#by default we are going to rely on mlbviewer settings on destination
#future versions will add support for all the keyboard shortcuts and maybe remote config changes

#Basically I want to create a curses front end that will ask for the remote host, and save a list 
#of previously used hosts in a config file of sorts. Then it will use the normal listing stuff but 
#will redirect chosen things to the remote host. Will need an intermediate receiver as well.
#Can probably use twisted to 

#I think I want to emulate the mlbviewer curses interface, but send
#all commands back to the server instead of launching instance directly

def getGames():

	#get date and time information for local and eastern timezones
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
		listings = mlbsched.getListings()
	except (MLBUrlError, MLBXmlError):
		print "Could not fetch schedule"
		return -1

#def main():
#	t = Terminal()

if __name__ == "__main__":
	getGames()
	