# Utility to automate creation of pull requests

The script ```makeprtraiana.py``` does the following steps:

For the -n option;

- check that current directory to be in a git tree, find the project name.
- creates a pull request for the current project (project must be other than ```okro-build```)
- submit pull request
- wait for continuous integration build to complete
- download the CI build log and extract the okro build id.
- make a beep and signal completion of build.

For the -u option:

- check that current directory to be in a git tree, find the project name.
- push the current feature branch
- wait for continuous integration build to complete
- download the CI build log and extract the okro build id.
- make a beep and signal completion of build.

For the -w option;

- check that current directory to be in a git tree, find the project name.
- wait for CI build of top commit to complete
- download the CI build log and extract the okro build id.
- make a beep and signal completion of build.

for the ```-d <okro-dir>``` option. (for example: ```-d ~/code/okro-lab/reals/dev/rlm-dev-shared```)

- in the original project: parse okro.yaml files under the directory, and extract the publication/image names
- in all yaml files that are under the directory specified by ```-d``` option:
    - fix the version number for all publications for the current project, and set to the build_id extracted from CI build.
    - create okro feature branch,
    - push okro feature branch 

The user still has to review the changes and open a PR for okro, by visiting the link.
 
you need to have the ```GITHUB_TOKEN``` environment variable to be set and exported.

## installation

You need pyton3 to be installed; also need to install the requirement packages:
    
- ```pip3 install Github```
- ```pip3 install websocket-client```
- ```pip install ruamel.yaml```

## help text

```
usage: makeprtraiana.py [-h] [--new-pr] [--update-pr] [--wait] [--org ORG] [--showlog] [--okrodir OKRODIR] [--verbose]

This program does the following steps; it assumes that the current directory is in a git tree. for the --new-pr option: 1. Creates a feature branch for the current branch, and pushes the
feature branch. 2. Opens a pull request, it is assumed that a continuous integration build is then triggered. 3. The program then waits that the continuous integration build for that
pull request has completed. 4. At the end of the build, a sound is played, and the url with the build log is written to standard output. for the --update-pr option: 1. Push the current
state of local branch to the feature banch 2. The program waits that the continuous integration build for the top commit has completed. 3. At the end of the build, a sound is played, and
the url with the build log is written to standard output. for the --wait option: 2. The program waits that the continuous integration build for the top commit has completed. 3. At the
end of the build, a sound is played, and the url with the build log is written to standard output. Note that ou need to set the organization (-o option) in the case of a private
repository. This program assumes that the environment GITHUB_TOKEN is exported, and that it has the token of the current user. This program assumes the github api to be installed - pip
install python-github-api

optional arguments:
  -h, --help            show this help message and exit

Push or update a pull request and wait for the continuous integration build to complete:
  --new-pr, -n          create new pull request (default: False)
  --update-pr, -u       update and push to existing pull request (default: False)
  --wait, -w            wait for ongoing build of top commit to complete (default: False)
  --org ORG, -o ORG     specify organization used to lookup the repository (default: traiana)
  --showlog, -s         show the build log in a bew browser (default: False)
  --okrodir OKRODIR, -d OKRODIR
                        if set: set version of images to project images that are referenced in yamls under this directory (default: )
  --verbose, -v         trace all commands, verbose output (default: False)
```
