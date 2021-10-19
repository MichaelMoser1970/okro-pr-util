# utility to automate creation of pull requests

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

The user still has to review the changes and open a commit.
 
you need to have the ```GITHUB_TOKEN``` environment variable to be set and exported.

## installation

You need pyton3 to be installed
install the requirement packages:
    
- ```pip3 install Github```
- ```pip3 install websocket-client```

