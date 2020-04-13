# forkedRepoTracker

### Usage
Fill in the user info in userInfo.json, ```username``` is your github account, and ```token``` is your access token to github which can be generated from https://github.com/settings/tokens


```
$ -h / --help: print this help message
$ -s / --show-patch-disabled: do not show patch of compared commits
$ -u / --url: specify the github url
$ -v / --verbose: print more message
```
Example: 
```
$ python forkedRepoTracker.py -u https://github.com/AUTHOR/REPO
```

### To do
* If default branch of two user are different, comparison may failed
