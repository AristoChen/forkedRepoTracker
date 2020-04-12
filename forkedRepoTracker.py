# -*- coding: utf-8 -*-

import requests
import getopt
import json
import time
import sys
import re
import os

def usage():
	print "Usage:"
	print "-h / --help: print this help message"
	print "-s / --show-patch-disabled: do not show patch of compared commits"
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
	if len(sys.argv) < 3 or "-u" not in sys.argv:
		usage()
		sys.exit(2)

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hsu:v", ["help", "show-patch-disabled", "url=", "verbose"])
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit(2)
	verbose = False
	showPatch = True
	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit(2)
		elif o in ("-s", "--show-patch-disabled"):
			showPatch = False
		elif o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-u", "--url"):
			url = a
			if url.find("github") == -1:
				print "Invalid url: " + url
				usage()
				sys.exit(2)
			if url[-1] != '/':
				url = url + '/'
			authorOriginal = url[url[:url[:-1].rfind('/')-len(url)].rfind('/')+1:url[:-1].rfind('/')]
			repoNameOriginal = url[url[:-1].rfind('/')+1:-1]
		else:
			assert False, "Invalid option"

	rows, columns = os.popen('stty size', 'r').read().split()

	with open('userInfo.json', 'r') as file:
		userInfo = json.loads(file.read())
		username = userInfo["username"]
		token = userInfo["token"]
		if username == "" or token == "":
			print "Please fill in your github account info"

	baseURL = "https://api.github.com/"

	# Get remaining resources for api
	rateLimitURL = "{0}rate_limit".format(baseURL)
	res = get(rateLimitURL, username, token)
	rateLimitInfo = json.loads(res.text)
	remain = rateLimitInfo["resources"]["core"]["remaining"]
	resetTime = time.ctime(rateLimitInfo["resources"]["core"]["reset"])
	print "Remaining resources: {0}, and will be reset at: {1}".format(remain, resetTime)
	if remain == 0:
		print "Not enough resources, please wait until reset"
		sys.exit(1)

	# Get basic info of repo
	repoURL = "{0}repos/{1}/{2}".format(baseURL, authorOriginal, repoNameOriginal)
	res = get(repoURL, username, token)
	repoInfo = json.loads(res.text)
	defaultBranchOriginal = repoInfo["default_branch"]

	page = 1
	forkList = []
	while True: # To fetch list of forked repo
		forkListURL = "{0}repos/{1}/{2}/forks?page={3}".format(baseURL, authorOriginal, repoNameOriginal, str(page))
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

	for i in range(len(forkList)): # Process each repo
		sys.stdout.write("Processing: %d / %d\r" % (i+1, len(forkList)))
		sys.stdout.flush()

		authorFork = forkList[i]["owner"]["login"]
		repoNameFork = forkList[i]["name"]
		defaultBranchFork = forkList[i]["default_branch"]
		authorParent = authorOriginal
		compareURL = "{0}repos/{1}/{2}/compare/{3}:{4}...{1}:{5}".format(baseURL, authorFork, repoNameFork, authorParent, defaultBranchOriginal, defaultBranchFork)
		res = get(compareURL, username, token)
		compareResult = json.loads(res.text)
		try: # Try to get info
			compareStatus = compareResult["status"]
			aheadCommits = compareResult["ahead_by"]
			behindCommits = compareResult["behind_by"]
		except KeyError: # Comparison failed, maybe forked from another author
			repoURL = "{0}repos/{1}/{2}".format(baseURL, authorFork, repoNameFork)
			res = get(repoURL, username, token)
			repoResult = json.loads(res.text)
			try:
				authorParent = repoResult["parent"]["owner"]["login"]
				compareURL = "{0}repos/{1}/{2}/compare/{3}:{4}...{1}:{5}".format(baseURL, authorFork, repoNameFork, authorParent, defaultBranchOriginal, defaultBranchFork)
				res = get(compareURL, username, token)
				compareResult = json.loads(res.text)
				try:
					compareStatus = compareResult["status"]
					aheadCommits = compareResult["ahead_by"]
					behindCommits = compareResult["behind_by"]
				except KeyError:
					print "Warning: {0}/{1} seems to be not exists, index: {2}".format(authorFork, repoNameFork, str(i))
			except KeyError:
				print "Warning: {0}/{1} seems to be not exists, index: {2}".format(authorFork, repoNameFork, str(i))
				continue

		if aheadCommits > 0: # Process all the ahead commits
			print "{0}Author : {1}, {2} commits ahead and {3} commits behind of {4}:master".format("="*int(columns), authorFork, aheadCommits, behindCommits, authorParent)

			page = 1
			commitsList = []
			while True: # Fetch commit list
				commitURL = "{0}repos/{1}/{2}/commits?page={3}".format(baseURL, authorFork, repoNameFork, str(page))
				res = get(commitURL, username, token)
				commitsList += json.loads(res.text)
				if len(commitsList) >= aheadCommits+1:
					break

			for j in range(aheadCommits): # Process commit patch
				commitTitle = commitsList[j]["commit"]["message"]
				commitSHA_head = commitsList[j]["sha"]
				commitSHA_base = commitsList[j+1]["sha"]
				try:
					print "{0}\n{1:<7}|   Title   | {2}".format("-"*int(columns), str(j+1) + ". ", commitTitle.encode('utf-8').replace("\n", "\n       |           | "))
					if showPatch == True:
						commitPatchURL = "{0}repos/{1}/{2}/compare/{3}...{4}".format(baseURL, authorFork, repoNameFork, commitSHA_base, commitSHA_head)
						res = get(commitPatchURL, username, token)
						patchInfo = json.loads(res.text)
						if "files" in patchInfo:
							patchFiles = patchInfo["files"]
						else:
							continue

						for k in range(len(patchFiles)):
							fileName = patchFiles[k]["filename"]
							if "patch" in patchFiles[k]:
								patch = patchFiles[k]["patch"].replace("\t", "    ")
							else:
								patch = "[Warning]: No patch found, maybe a binary file or permission change?"

							try:
								print "{0}\n       |   File    | {1}".format("-"*int(columns), fileName)
								pos = patch.find("\n")
								firstLine = True
								while pos != -1:
									if pos / (int(columns)-22) != 0:
										loop = pos / (int(columns)-22)
										tmp = loop
										while loop != 0:
											if firstLine == True:
												firstLine = False
												print("-"*int(columns))
												print "       |   Patch   | {0}".format(patch[(tmp-loop)*(int(columns)-22):(tmp-loop)*(int(columns)-22)+int(columns)-22].encode('utf-8'))
											else:
												print "       |           | {0}".format(patch[(tmp-loop)*(int(columns)-22):(tmp-loop)*(int(columns)-22)+int(columns)-22].encode('utf-8'))
											loop -= 1
										print "       |           | {0}".format(patch[pos-(pos%(int(columns)-22)):pos].encode('utf-8'))
									else:
										if firstLine == True:
											firstLine = False
											print("-"*int(columns))
											print "       |   Patch   | {0}".format(patch[:pos].encode('utf-8'))
										else:
											print "       |           | {0}".format(patch[:pos].encode('utf-8'))
									patch = patch[pos+1:]
									pos = patch.find("\n")
								print "       |           | {0}".format(patch[-(pos%(int(columns)-22)):].encode('utf-8'))

							except UnicodeEncodeError:
								print "Encoding error, index: {0}".format(str(i))
				except UnicodeEncodeError:
					print "Encoding error, index: {0}".format(str(i))
		else:
			if verbose == True:
				print "Author: {0}, {1} commits ahead and {2} commits behind of {3}:master".format(authorFork, aheadCommits, behindCommits, authorParent)

	print "\nCompleted"
