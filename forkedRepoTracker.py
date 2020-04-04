# -*- coding: utf-8 -*-

import requests
import getopt
import json
import time
import sys
import re

def usage():
	print "Usage:"
	print "-h / --help: print this help message"
	print "-u / --url: specify the github url"
	print "-v / --verbose: print more message"
	print "\nExample: python forkedRepoTracker.py -u https://github.com/AUTHOR/REPO"

def get(url, username = "", token = ""):
	res = requests.get(url, auth=(username, token))
	while res.status_code != requests.codes.ok:
		print "[Error] url: {0}\n http response code: {1}, response body: {2}".format(url, str(res.status_code), res.text)
		if res.status_code == 404:
			break
		res = requests.get(url, auth=(username, token))
	return res

if __name__ == "__main__":
	if len(sys.argv) < 4 or "-u" not in sys.argv:
		usage()
		sys.exit(2)

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hu:v", ["help", "url=", "verbose"])
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit(2)
	verbose = False
	for o, a in opts:
		if o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-h", "--help"):
			usage()
			sys.exit(2)
		elif o in ("-u", "--url"):
			url = a
			if url.find("github") == -1:
				print "Invalid url: " + url
				usage()
				sys.exit(2)
			if url[-1] != '/':
				url = url + '/'
			authorOriginal = url[url[:url[:-1].rfind('/')-len(url)].rfind('/')+1:url[:-1].rfind('/')]
			repoName = url[url[:-1].rfind('/')+1:-1]
		else:
			assert False, "Invalid option"

	with open('userInfo.json', 'r') as file:
		userInfo = json.loads(file.read())
		username = userInfo["username"]
		token = userInfo["token"]
		if username == "" or token == "":
			print "Please fill in your github account info"

	baseURL = "https://api.github.com/"

	rateLimitURL = "{0}rate_limit".format(baseURL)
	res = get(rateLimitURL, username, token)
	rateLimitInfo = json.loads(res.text)
	remain = rateLimitInfo["resources"]["core"]["remaining"]
	resetTime = time.ctime(rateLimitInfo["resources"]["core"]["reset"])
	print "Remaining resources: {0}, and will be reset at: {1}".format(remain, resetTime)
	if remain == 0:
		print "Not enough resources, please wait until reset"
		sys.exit(1)

	page = 1
	forkList = []
	while True:
		forkListURL = "{0}repos/{1}/{2}/forks?page={3}".format(baseURL, authorOriginal, repoName, str(page))
		res = get(forkListURL, username, token)
		forkListTmp = json.loads(res.text)

		if len(forkListTmp) == 0:
			print "\nAll forked repo fetched"
			break
		else:
			sys.stdout.write("Processing fork list page:  %d\r" % page)
			sys.stdout.flush()
			forkList += forkListTmp
		page += 1

	print "Found " + str(len(forkList)) + " forked repo"

	for i in range(len(forkList)):
		sys.stdout.write("Processing: %d / %d\r" % (i+1, len(forkList)))
		sys.stdout.flush()

		authorFork = forkList[i]["owner"]["login"]
		authorParent = authorOriginal
		compareURL = "{0}repos/{1}/{2}/compare/{3}:master...{1}:master".format(baseURL, authorFork, repoName, authorParent)
		res = get(compareURL, username, token)
		compareResult = json.loads(res.text)
		try:
			compareStatus = compareResult["status"]
			aheadCommits = compareResult["ahead_by"]
			behindCommits = compareResult["behind_by"]
		except KeyError:
			repoURL = "{0}repos/{1}/{2}".format(baseURL, authorFork, repoName)
			res = get(repoURL, username, token)
			repoResult = json.loads(res.text)
			try:
				authorParent = repoResult["parent"]["owner"]["login"]
				compareURL = "{0}repos/{1}/{2}/compare/{3}:master...{1}:master".format(baseURL, authorFork, repoName, authorParent)
				res = get(compareURL, username, token)
				compareResult = json.loads(res.text)
				try:
					compareStatus = compareResult["status"]
					aheadCommits = compareResult["ahead_by"]
					behindCommits = compareResult["behind_by"]
				except KeyError:
					print "Warning: {0} seems to be not exists, index: {1}".format(authorFork, str(i))
			except KeyError:
				print "Warning: {0} seems to be not exists, index: {1}".format(authorFork, str(i))
				continue

		if aheadCommits > 0:
			print "Author: {0}, {1} commits ahead and {2} commits behind of {3}:master".format(authorFork, aheadCommits, behindCommits, authorParent)

			page = 1
			commitsList = []
			while True:
				commitURL = "{0}repos/{1}/{2}/commits?page={3}".format(baseURL, authorFork, repoName, str(page))
				res = get(commitURL, username, token)
				commitsList += json.loads(res.text)

				if len(commitsList) >= aheadCommits:
					break
			for j in range(aheadCommits):
				try:
					print "\t{0}".format(str(j) + ". " + commitsList[j]["commit"]["message"].encode('utf-8').replace("\n", "\n\t   "))
				except UnicodeEncodeError:
					print "Encoding error, index: {0}".format(str(i))
		else:
			if verbose == True:
				print "Author: {0}, {1} commits ahead and {2} commits behind of {3}:master".format(authorFork, aheadCommits, behindCommits, authorParent)

	print "\nCompleted"
