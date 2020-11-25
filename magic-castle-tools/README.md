# Magic Castle tools
Once a Magic Castle instance is ready, we usually need to import the material in all userXY's home directory.
The following tools allow this.

## `pusersh`
This script is only meant to be run by `centos` in order to run a command as each `userXY`.
* To be installed in the `centos`'s `~/bin` directory:
  1. Create a `bin` folder in the `centos`'s home directory
  1. Import the `pusersh` script in `~/bin`
  1. Run `chmod +x ~/bin/pusersh`
* Common usage examples:
```
$ pusersh whoami  # To test if LDAP and related services work properly
$ pusersh "/project/def-sponsor00/update_home_git.sh python-ecology-lesson cq-notebooks"
$ pusersh /project/def-sponsor00/clean_home.sh
```

## `update_home_git.sh`
Depending on the existence of the repository folder in the user's home,
  the script will either `git clone` or `git pull` from GitHub.
* To be installed in `/project/def-sponsor00` by one `userXY`
  1. Make sure the GroupID `def-sponsor00` is set
  1. Make sure the group can read and execute (`r-x`) the script
* First argument (mandatory): the GitHub repository name
* Second argument (optional): the repository branch to clone

## `clean_home.sh`
This resets the home directory to an "empty" state.
* To be installed in `/project/def-sponsor00` by one `userXY`
  1. Make sure the GroupID `def-sponsor00` is set
  1. Make sure the group can read and execute (`r-x`) the script
