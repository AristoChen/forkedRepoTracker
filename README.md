# forkedRepoTracker

### Usage
Fill in the user info in userInfo.json, ```username``` is your github account, and ```token``` is your access token to github

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
* If repo name of upstream is modified, then we will not able to get the correct ouput
* SSL verification may failed
