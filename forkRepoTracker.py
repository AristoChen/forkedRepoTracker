from bs4 import BeautifulSoup
import requests
import getopt
import sys
import re

def usage():
	print "Usage:"
	print "-h / --help: print this help message"
	print "-u / --url: specify the github url"
	print "-v / --verbose: print more message"
	print "\nExample: python test.py -u https://github.com/AUTHOR/REPO"

def get(url):
	res = requests.get(url)
	while res.status_code != requests.codes.ok:
		print "[Error] http response code: " + str(res.status_code) + ", retrying"
		res = requests.get(url)
	return res

if __name__ == "__main__":
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
			if url.find("https://") == -1:
				url = "https://" + url
			if url[-1] != '/':
				url = url + '/'
			repoName = url[url[:-1].rfind('/')+1:-1]
			url = url + "network/members"
		else:
			assert False, "Invalid option"

	res = get(url)
	soup = BeautifulSoup(res.text, 'html.parser')
	userList = soup.find_all("div", {"class": "repo"})

	if len(userList) > 1:
		print "Found " + str(len(userList)-1) + " forked repo"

		for i in range(len(userList)):
			if i == 0:
				continue
			sys.stdout.write("Processing: %d / %d\r" % (i, len(userList)-1))
			sys.stdout.flush()
			userName = userList[i].find('a')['href'][1:]
			url = "https://github.com/" + userName + "/" + repoName
			res = get(url)
			soup = BeautifulSoup(res.text, 'html.parser')

			branchInfo = soup.find_all("div", {"class": "branch-infobar"})
			branchInfo[0].find('span').extract()

			if branchInfo[0].text.strip().find("ahead") != -1:
				print "Author: " + userName + ", " + branchInfo[0].text.strip()

				aheadCommits = re.findall(r'([0-9]+) commits? ahead', branchInfo[0].text.strip())[0]
				url = "https://github.com/" + userName + "/" + repoName + "/commits/master"
				res = get(url)
				soup = BeautifulSoup(res.text, 'html.parser')

				commitList = soup.find_all("li", {"class": "commit"})
				for i in range(int(aheadCommits)):
					commitMessage = commitList[i].find_all("a", {"class": "message"})[0].text.strip()
					commitTime = commitList[i].find("relative-time")['datetime']

					print "\tCommit message: " + commitMessage + ", time: " + commitTime

	else:
		print "Can not find any forked repo"
