#!/usr/bin/python

# -*- coding: utf-8 -*-

import subprocess
import os.path
from bs4 import BeautifulSoup as bs
import urllib2
import sys
import shutil
import stat
import httplib
import urllib
import tempfile

import ConfigParser
from appdirs import *

import argparse

audioFormat='mp3'

def fixYoutubeURL(url):
	if not 'youtube.com' in url:
		url = 'http://youtube.com' + url
	return url


# Download audio from youtube.com by calling the external tool youtube-dl.
def downloadAudioFile(url, fn):
	print 'Downloading video...'

	subprocess.check_output(['youtube-dl', '--restrict-filenames', '--extract-audio', '--audio-format', audioFormat, url, "--output", fn])
	#'--id', 

	if not os.path.isfile(fn): 
		raise IOError('file not found')

# Construct a string by concatanating strings in the supplied list with spaces 
# in between them.
def combineWords(parts):
	result = ''
	for part in parts:
		# Add space if this is not the first element. 
		if result is not '':
			result = result + ' '
		result = result + part
	return result


def filterResults(searchResults, searchTerm):

	# Look for an exact match in title.
	target = 'how to pronounce' + ' ' + searchTerm.lower();
	for entry in searchResults:
		title = entry['title'].lower().strip();
		if title == target:
			return entry

	# More tolerant match.
	for entry in searchResults:
		title = entry['title'].lower().strip();
		if searchTerm.lower() in title and 'how to pronounce' in title:
			return entry

	return None

def printResults(results):
	print ""
	print "Search results:"
	for result in results:
		print result['url'] + "  " + result['title']
	print ""


# Produce of all potential entries in soupified search results.
def findEntryInSoup(soup):

	# Note: Another way would be to scan through any video links in the page.
	body_container = soup.body.find("div", {"id": "body-container"})
	page = body_container.find("div", {"id": "page"});
	content = page.find("div", {"id": "content"});
	results = content.find("div", {"id": "results"});
	entries = results.findAll("div", {"class":"yt-lockup-content"});
	entryFound = None

	results = []
	for entry in entries:
		yt_lockup_title = entry.find("h3", {"class":"yt-lockup-title"});

		# Other css classes: yt-ui-ellipsis yt-ui-ellipsis-2 yt-uix-sessionlink spf-link
		a = yt_lockup_title.find("a", {"class", "yt-uix-tile-link"})

		#a_elements.append(a)
		results.append( dict(title=a['title'], url=a['href']) )

	return results


# Processes command line arguments.
class Args:
	def __init__(self):
		self.args = None

	def readArgs(self):
		parser = self.createParser()
		self.args = parser.parse_args()


	def createParser(self):
		parser = argparse.ArgumentParser(description='Look up the pronunciation of a word or a phrase in Youtube.')

		parser.add_argument('words', metavar='WORDS', type=str, nargs='+', help='One or more words to be pronounced')
		parser.add_argument('--config', metavar='CONFIG_FILE', type=str, help='Use a custom configuration file')
		parser.add_argument('--api-key', metavar='YOUR_API_KEY', type=str, help='Your Youtube Data API key')

		group = parser.add_mutually_exclusive_group()
		group.add_argument('--use-api', dest='use_api', action='store_true')
		group.add_argument('--no-use-api', dest='use_api', action='store_false')
		parser.set_defaults(use_api=None)

		return parser

# Deals with configuration options and configuration file.
class Config:
	def __init__(self):
		self.config = None
		self.configFn = None
		self.use_api = False
		self.api_key = None

	def createConfigObject(self):
		return ConfigParser.RawConfigParser(allow_no_value=True)

	def readConfig(self):
		if not os.path.exists(self.configFn):
			sys.exit("Config file " + self.configFn + " does not exist.")		
		self.config = self.createConfigObject()
		self.config.read(self.configFn)

	def determineConfigFn(self, args):
		if args.config is not None:
			self.configFn = args.config
			print "Using custom config file:", self.configFn
		else:
			self.produceConfigFn()
			self.validateConfigFile()
	
	def validateConfigFile(self):
		if not os.path.exists(self.configFn):
			self.createDefaultConfigFile()
		elif not os.path.isfile(self.configFn):
			raise IOError(self.configFn + " exists but is not a regular file")

	def produceConfigFn(self):
		appname = "pronounce-lookup"
		appauthor = "kk"
		confDir = user_config_dir(appname, appauthor)
		self.configFn = os.path.join(confDir, "pronounce-lookup.cfg")

	def createDefaultConfigFile(self):

		print "Creating default configuration file."

		confDir = os.path.dirname(self.configFn)
		if not os.path.exists(confDir):
			os.makedirs(confDir)

		config = self.createConfigObject()
		config.add_section('youtube_api')
		config.set('youtube_api', 'use_api', 'false')
		config.set('youtube_api', 'api_key', '')
		with open(self.configFn, 'wb') as configfile:
			config.write(configfile)

		print "You may want to edit the file:", self.configFn
	
	def determineAPIKey(self, args):	
		if args.api_key is None:
			self.api_key = self.config.get("youtube_api", "api_key")
		else:
			self.api_key = args.api_key
		#print "Youtube API Key:", self.api_key
		print "Youtube API Key:", "***"

	def determineUseAPI(self, args):
		if args.use_api is None:
			self.use_api = self.config.getboolean("youtube_api", "use_api")
		else:
			self.use_api = args.use_api
		print "Use Youtube API:", self.use_api

	def configure(self, args):
		self.determineConfigFn(args)
		self.readConfig()
		self.determineUseAPI(args)
		if self.use_api:
			self.determineAPIKey(args)


# Creates and deletes temporary directory for downloaded and processed files.
class TempDir:
	def __init__(self):
		self.basetempdir = None
		self.tempdir = None

	def prepareTempDir(self):
		self.basetempdir = tempfile.mkdtemp()
		self.tempdir = os.path.join(self.basetempdir, 'pronounce-lookup');

		os.makedirs(self.tempdir)
		print "Creating temporary directory:" + self.tempdir

	def removeTempDir(self):
		if self.basetempdir is not None and os.path.exists(self.basetempdir):
			print "Deleting temporary directory: " + self.basetempdir
			shutil.rmtree(self.basetempdir)


# Various methods for calling external tools from ffmpeg project.
class Ffmpeg:
	def __init__(self):
		pass

	# Remove silence from the beginning and end of the video file.
	# Input video will be expected to be found in tempName(0), output file will be written 
	# to tempName(4)
	def trimSilence(self, app, expectedFilename):

		print "Removing silence from video..."

		#print os.popen( ... ).read()

		temp0 = app.tempName(0)
		temp1 = app.tempName(1)
		temp2 = app.tempName(2)
		temp3 = app.tempName(3)
		temp4 = app.tempName(4)

		os.popen("ffmpeg -i {} -loglevel quiet -af silenceremove=1:0:-96dB {}".format(temp0, temp1))
		os.popen("ffmpeg -i {} -loglevel quiet -af areverse                {}".format(temp1, temp2))
		os.popen("ffmpeg -i {} -loglevel quiet -af silenceremove=1:0:-96dB {}".format(temp2, temp3))
		os.popen("ffmpeg -i {} -loglevel quiet -af areverse                {}".format(temp3, temp4))

	def playAudioFile(self, fn):
		print "Playing audio from file..."
		#subprocess.check_output(['mplayer', '-quiet', fn])
		subprocess.check_output(['ffplay', '-loglevel', 'quiet', '-nodisp', '-autoexit', fn])



# Main application code.
class App:
	def __init__(self):
		self.tempDir = None
		self.search = None
		self.searchTerm = None

	def initialize(self):

		args = Args()
		args.readArgs()

		cfg = Config()
		cfg.configure(args.args)

		if cfg.use_api:
			self.search = SearchWithAPI(cfg.api_key)
		else:
			self.search = SearchWithHTTP();

		self.searchTerm = combineWords(args.args.words)
		print "Search term:" + "'" + self.searchTerm + "'"

	def mainTask(self):
		try:
			self.tempDir = TempDir()
			self.tempDir.prepareTempDir()
			self.mainTaskInternal()
		finally:
			self.tempDir.removeTempDir()

	def mainTaskInternal(self):
		url = self.searchForBestVideo()
		if url is None:
			sys.exit("No relevant videos were found.")	

		url = fixYoutubeURL(url)
		print 'Youtube URL:' + url

		downloadAudioFile(url, self.tempName(0))

		ffmpeg = Ffmpeg()
		ffmpeg.trimSilence(self, self.tempName(0))
		ffmpeg.playAudioFile(self.tempName(4))

	def youtubeSearch(self, query):
		print "Search query: " + query
		results = self.search.search(query)
		printResults(results)

		return results
	
	def searchForBestVideo(self):

		query1 = 'how to pronounce emma saying "{}"'.format(self.searchTerm)
		searchResults = self.youtubeSearch(query1)
		result = filterResults(searchResults, self.searchTerm)

		if result is None:
			# Try a more tolerant query. 
			query2 = 'how to pronounce "{}"'.format(self.searchTerm)
			searchResults = self.youtubeSearch(query2)
			result = filterResults(searchResults, self.searchTerm)

		if result is None:
			return None

		return result['url']

	# Construct absolute filename for intermediate video files with id.
	# i.e. for id=3, result will be something like /tmp/tmpLGAS2U/pronounce-lookup/temp3.mp3
	def tempName(self, id):
		return os.path.join(self.tempDir.tempdir, 'temp' + str(id) + '.' + audioFormat)


# A class providing a method to search in youtube.com, which internally uses the Youtube Data API.
class SearchWithAPI:
	def __init__(self, api_key):
		self.api_key = api_key;

		# Import required modules.
		global build, HttpError, argparser
		from apiclient.discovery import build
		from apiclient.errors import HttpError
		from oauth2client.tools import argparser

	# Find a relevant video url in youtube.com.
	def search(self, query):
		args = argparse.Namespace(auth_host_name='localhost', 
			auth_host_port=[8080, 8090], 
			logging_level='ERROR', 
			max_results=25, 
			noauth_local_webserver=True, 
			q=query)

		try:
			return self.searchInternal(args, self.api_key)
		except HttpError, e:
			sys.exit( "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content) )

	def searchInternal(self, options, api_key):

		if len(api_key.strip()) == 0:
			raise ValueError("Youtube API key is empty string")

		YOUTUBE_API_SERVICE_NAME = "youtube"
		YOUTUBE_API_VERSION = "v3"
		youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)

		searchResponse = youtube.search().list(
			q=options.q,
			part="id,snippet",
			maxResults=options.max_results
		).execute()
		
		videos = []

		for searchResult in searchResponse.get("items", []):
			if searchResult["id"]["kind"] == "youtube#video":
				title = searchResult["snippet"]["title"]
				videoId = searchResult["id"]["videoId"]
				url = "/watch?v=" + videoId;
				videos.append( dict(title=title, url=url)   )

		return videos


# A class providing a method to search in youtube.com, which internally uses an HTTP request.
class SearchWithHTTP:
	def __init__(self):
		pass

	# Find a relevant video url in youtube.com.
	def search(self, query):
		query = urllib.quote_plus(query)
		print "Search query: " + query
		youtubeSearchURL = "https://www.youtube.com/results?search_query=" + query

		print 'Youtube search URL:' + youtubeSearchURL

		headers = {'Accept-Language': 'en-US,en;q=0.5'} # We want the english version of the title.
		request = urllib2.Request(youtubeSearchURL, headers=headers)
		response = urllib2.urlopen(request) 
		text = response.read()

		soup = bs(text, "lxml")

		return findEntryInSoup(soup)

# Main entry point.
def main():

	app = App()
	app.initialize()
	app.mainTask()

	print 'Finished...'

if __name__ == "__main__":
    main()

