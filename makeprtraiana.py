#!/usr/bin/env python3

import io
import os
import os.path
import shlex
import subprocess
import sys
import glob
import webbrowser
import re
import traceback
import time
import ssl
from platform import system
from pathlib import Path
import argparse
import ctypes
import ruamel.yaml as yaml
from github import Github
import websocket
#import pprintex


# *** adapted from https://raw.githubusercontent.com/nekumelon/simpleSound/main/simpleSound.py ***


def windows_command(command):
    ctypes.windll.winmm.mciSendStringW(command, ctypes.create_unicode_buffer(600), 559, 0)

def play(file_name):
    os_name = system()

    if os_name == "Windows":
        windows_command("open " + file_name)
        windows_command("play " + file_name + " wait")
        windows_command("close " + file_name)
    else:
        cmd = ''
        if os_name == "Darwin":
            cmd = "exec afplay \"" + file_name + "\""
        elif os_name == "Linux":
            cmd = "exec aplay --quiet " + file_name
        else:
            print("can't play sound on ",os_name)
            return

        with subprocess.Popen(cmd, universal_newlines = True, shell = True, stdout = -1, stderr = -1) as proc:
            proc.communicate()

def beep(success):
    if success:
        data_file = Path(__file__).with_name('Blow.aiff')
    else:
        data_file = Path(__file__).with_name('Basso.aiff')
    play(str(data_file))

# *** eof copied ***


class RunCommand:
    trace_on = False
    exit_on_error = False

#    @staticmethod
#    def trace(on_off):
#        RunCommand.trace_on = on_off
#
#    @staticmethod
#    def exit_on_error(on_off):
#        RunCommand.exit_on_error = on_off
#
    def __init__(self, command_line = None):
        self.command_line = command_line
        self.exit_code = 0
        if command_line is not None:
            self.run(command_line)

    def run(self, command_line):
        try:
            if RunCommand.trace_on:
                print('>', command_line)

            with subprocess.Popen(shlex.split(command_line), \
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:

                self.command_line = command_line

                (output, error_out) = process.communicate()

                self.exit_code = process.wait()

                self.output = output.decode("utf-8")
                self.error_out = error_out.decode("utf-8")


                self.exit_code = process.wait()

                if RunCommand.trace_on:
                    msg = ">exit_code: " + str(self.exit_code)
                    if self.output != "":
                        msg += "\n  stdout: " + self.output
                    if self.error_out != "":
                        msg += "\n  stderr: " + self.error_out
                    print(msg)

                if RunCommand.exit_on_error and self.exit_code != 0:
                    print(self.make_error_message())
                    sys.exit(1)

                return self.exit_code
        except FileNotFoundError:
            self.output = ""
            self.error_out = "file not found"
            self.exit_code = 1
            return self.exit_code

    def result(self):
        return self.exit_code, self.output

    def make_error_message(self):
        return_value = ""
        if self.command_line != "":
            return_value += f" command line: {self.command_line}."
        if self.exit_code != 0:
            return_value += f" exit status: {self.exit_code}. "
        if self.error_out != "":
            return_value += " " + self.error_out
        return return_value



def get_remote_origin():
    cmd = RunCommand()
    if cmd.run("git config --get remote.origin.url") != 0:
        print("Error: can't get remote origin url", cmd.make_error_message())
        sys.exit(1)

    remote_origin = cmd.output.rstrip('\n')
    pos_1 = remote_origin.rfind('/')
    pos_2 = remote_origin.rfind('.')
    if pos_1 == -1:
        print("Error: can't get repository name from remote url: ", remote_origin)

    if pos_2 == -1 or pos_2 < pos_1:
        pos_2 = len(remote_origin)

    repo_name = remote_origin[pos_1+1:pos_2]
    if repo_name == "":
        print("Error: can't get repository namefrom remote url: ", remote_origin, " ", cmd.make_error_message())
        sys.exit(1)

    return remote_origin, repo_name

def is_remote_ahead(remote_origin_url, branch_name, local_branch_top_commit):
    cmd = RunCommand()

    if cmd.run("git ls-remote --heads " + remote_origin_url) != 0:
        print("Error: can't list remote heads", cmd.make_error_message())
        sys.exit(1)

    remote_head_commit = None
    for line in cmd.output.split("\n"):
        if line != "":
            columns = line.split('\t')
            if columns[1] == "refs/heads/" + branch_name:
                remote_head_commit = columns[0]

    if remote_head_commit is None:
        print("Error: can't get remote head from: ", cmd.output)
        sys.exit(1)

    print("local branch top: ",  local_branch_top_commit, "remote branch top:", remote_head_commit)

    if local_branch_top_commit == remote_head_commit:
        print("local and remote branches are in sync.")
        return 0

    # check if local branch is ahead; it is if the remote top is contained in the local branch
    cmd.run("git branch --contains " + remote_head_commit)

    for line in cmd.output.split("\n"):
        line = line[2:]
        if line == branch_name:
            print("local branch is ahead of remote branch")
            return 1

    print("Error: local and remote branch have diverged. remote top: ", remote_head_commit, " is not contained in local branch ", branch_name)
    sys.exit(1)

def get_last_tag():
    cmd = RunCommand()

    if cmd.run("git ls-remote --tags") != 0:
        print("Error: current list remote tags", cmd.make_error_message())
        sys.exit(1)

    last_tag = None
    for line in cmd.output.split("\n").reverse():
        if line != "":
            columns = line.split('\t')
            last_tag = columns[1]
            break

    if last_tag is not None:
        prefix = "refs/tags"
        if last_tag.starswith(prefix):
            return last_tag[len(prefix):]

    return None


def init():
    cmd = RunCommand()

    if cmd.run("git rev-parse --show-toplevel" ) != 0:
        print("Error: current directory not part of git tree")
        sys.exit(1)
    repo_root_dir = cmd.output.rstrip('\n')

    if cmd.run("git show -s --format=%H") != 0:
        print("Error: can't get top commit", cmd.make_error_message())
        sys.exit(1)
    top_commit = cmd.output.rstrip('\n')

#    if  cmd.run("git branch -r --contains " + top_commit) != 0:
#        print("Error: top commit ", top_commit, "has not been pushed yet", cmd.make_error_message())
#        sys.exit(1)

    if cmd.run("git rev-parse --abbrev-ref HEAD") != 0:
        print("Error: can't get current branch name", cmd.make_error_message())
        sys.exit(1)
    local_branch_name = cmd.output.rstrip('\n')

    if cmd.run('/bin/bash -c \'git status -b --porcelain=v2 | grep -m 1 "^# branch.upstream " | cut -d " " -f 3-\'') != 0:
        print("Error: can't get name of remote branch", cmd.make_error_message())
        sys.exit(1)
    remote_branch_name = cmd.output.rstrip('\n')

    if cmd.run("git show -s --format='%s %h'") != 0:
        print("Error: can't get last commit comment", cmd.make_error_message())
        sys.exit(1)
    last_commit_sha_and_comment = cmd.output.rstrip('\n')
    last_commit_sha_and_comment = re.sub(r'\s+','-', last_commit_sha_and_comment)
    last_commit_sha_and_comment = re.sub(r'[^\w]+','-', last_commit_sha_and_comment)

    if cmd.run("git show -s --format='%b'") != 0:
        print("Error: can't get body of last commit", cmd.make_error_message())
        sys.exit(1)
    last_commit_body = cmd.output

    remote_origin, repo_name = get_remote_origin()
    if repo_name in ("okro-lab", "okro-staging", "okro-prod"):
        print("Error: curent directory must be in repository other than ", repo_name)
        sys.exit(1)

    print("top_commit:", top_commit, \
            "repo_name:", repo_name, \
            "local_branch_name:", local_branch_name, \
            "remote_branch_name: ", remote_branch_name, \
            "last-commit-comment:", last_commit_sha_and_comment, \
            "last-commit-body: ", last_commit_body)
    return  repo_root_dir, top_commit, repo_name, local_branch_name, remote_branch_name, last_commit_sha_and_comment, last_commit_body, remote_origin



def wait_for_commit_to_build(repo, commit):
    commit = repo.get_commit(commit)
    print(commit)

    print("Waiting for the build to complete...")
    if RunCommand.trace_on:
        print("Commit: ", commit)
        print(repo.full_name)

    while True:
        if not RunCommand.trace_on:
            print(".", end="", flush=True)
        else:
            print("\nchecking statuses...")

        for status in commit.get_statuses():
            if RunCommand.trace_on:
                print( "created_at", status.created_at ,"creator:", status.creator,  " id:", status.id, "state:", status.state, "context:", status.context, "target_url:", status.target_url,  "url:", status.url, "description:", status.description )

            # failure of any stage fails the build
            if status.state == "failure":
                return  False, status.target_url

            if status.context == "build":
                if status.state == "success":
                    return  True, status.target_url

        time.sleep(5)

def create_branch_and_pr(repo, local_branch_name, last_commit_sha_and_comment, last_commit_body):

    if local_branch_name == "":
        local_branch_name = "master"
        local_br_name = last_commit_sha_and_comment
    else:
        local_br_name = last_commit_sha_and_comment
        local_br_name = re.sub(r"[^a-zA-Z0-9\ ]+",'-', local_br_name)
        local_br_name = re.sub(r"\s+", '-', local_br_name)

    cmd = RunCommand()

    print("local_br_name; ", local_br_name)

    if cmd.run("git branch -m '" + local_br_name + "'") != 0:
        print("Error: can't rename branch", cmd.make_error_message())
        sys.exit(1)

    if cmd.run("git push --set-upstream origin " + local_br_name + ":feature/" + local_br_name) != 0:
        print("Error: can't push to remote branch", cmd.make_error_message())
        sys.exit(1)

    base_name = "feature/" + local_br_name
    head_name = local_branch_name
    print("create_pull_request base:", head_name, "head:", base_name)

    # doc for create_repo:  https://docs.github.com/en/rest/reference/pulls#create-a-pull-request
    pull_request = repo.create_pull(
            title=last_commit_sha_and_comment,
            body=last_commit_body,
            base=head_name,
            head=base_name,
            maintainer_can_modify=True
            )

    print("pull request created: ", pull_request)

def parse_cmd_line():

    usage = '''
This program does the following steps; it assumes that the current directory is in a git tree.

for the --new-pr option:
    1. Creates a feature branch for the current branch, and pushes the feature branch.
    2. Opens a pull request, it is assumed that a continuous integration build is then triggered.
    3. The program then waits that the continuous integration build for that pull request has completed.
    4. At the end of the build, a sound is played, and the url with the build log is written to standard output.

for the --update-pr option:
    1. Push the current state of local branch to the feature banch
    2. The program waits that the continuous integration build for the top commit has completed.
    3. At the end of the build, a sound is played, and the url with the build log is written to standard output.

For the --last-tag option:
    1. extract the last tag from the remote branch
    2. use the last tag as the build_id, to be deployed if -w option is specified.

for the --wait option:
    2. The program waits that the continuous integration build for the top commit has completed.
    3. At the end of the build, a sound is played, and the url with the build log is written to standard output.

Note that ou need to set the organization (-o option) in the case of a private repository.

This program assumes that the environment GITHUB_TOKEN is exported, and that it has the token of the current user.
This program assumes the github api to be installed - pip install python-github-api

'''
    parse = argparse.ArgumentParser(description=usage, \
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    group = parse.add_argument_group("Push or update a pull request and wait for the continuous integration build to complete")

    group.add_argument('--last_tag', '-g',  default=False, \
            action='store_true', dest='use_last_tag', help='deploy the last tag instead of build id of last build')

    group.add_argument('--new-pr', '-n',  default=False, \
            action='store_true', dest='new_pr', help='create new pull request')

    group.add_argument('--update-pr', '-u',  default=False, \
            action='store_true', dest='update_pr', help='update and push to existing pull request')

    group.add_argument('--wait', '-w',  default=False, \
            action='store_true', dest='wait', help='wait for ongoing build of top commit to complete')

    group.add_argument('--org', '-o',  default='traiana', \
            type=str, dest='org', help='specify organization used to lookup the repository')

    group.add_argument('--showlog', '-s',  default=False, \
            action='store_true', dest='showlog', help='show the build log in a bew browser')

    group.add_argument('--okrodir', '-d',  default='', \
            type=str, dest='okrodir', help='if set: set version of images to project images that are referenced in yamls under this directory')

    group.add_argument('--tabs', '-t',  default=4, \
            type=int, dest='tabs', help='if set: convert tab characters to specified amount of spaces for yaml files in okro.')


    group.add_argument('--verbose', '-v',  default=False, \
            action='store_true', dest='verbose', help='trace all commands, verbose output')


    return parse.parse_args(), parse

def push_state_to_branch(remote_branch_name):
    if not remote_branch_name.startswith("origin/feature/"):
        print("Error. Remote origin does not start with 'origin/feature', curent remote branch name is:", remote_branch_name)
        sys.exit(1)

    cmd = RunCommand()
    if cmd.run("git push origin HEAD:" + remote_branch_name[7:]) != 0:
        print("Error: can't push  local changes. ", cmd.make_error_message())
        sys.exit(1)


def show_build_log(url):
    # show it in a web browser.
    # can't get the data through websockets via api call: the page may need non trivial authentication, for private repos.
    webbrowser.open(url)


def dump_build_log(url):
    ws_url = url.replace("https://", "wss://")
    ws_url += "/ws"
    print("ws_url:", ws_url)

    # shows exchanged headers.
    if RunCommand.trace_on:
        websocket.enableTrace(True)

    web_sock = websocket.create_connection(ws_url,
            sslopt={
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False
                },
            header = [ "Sec-Fetch-Dest: websocket",
                       "Sec-Fetch-Mode: websocket",
                       "Sec-Fetch-Site: same-origin" ,
                       "Sec-WebSocket-Key: 7Ygmm93Vo8zp+fhpcmUEMg==",
                       "Connection: keep-alive, Upgrade",
                       "Cache-Control: no-cache",
                       "Pragma: no-cache",
                       "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0",
                       "Accept: */*",
                       "Accept-Language: en-US,en;q=0.5",
                       "Accept-Encoding: gzip, deflate, br" ])


    web_sock.send("Hello world!")
    result = web_sock.recv()
    if RunCommand.trace_on:
        print(f"Received {result} type:  {str(type(result))}")
    web_sock.close()

    return result

#    import ssl
#
#    # non verifying ssl context (https://stackoverflow.com/questions/30461969/disable-default-certificate-verification-in-python-2-7-9)
#    ssl_ctx = ssl.create_default_context()
#    ssl_ctx.check_hostname = False
#    ssl_ctx.verify_mode = ssl.CERT_NONE
#
#    import asyncio
#    from websockets import connect
#
#    async def hello(uri):
#        async with connect(uri,ssl=ssl_ctx) as websocket:
#            await websocket.send("Hello world!")
#            resp = await websocket.recv()
#            print(resp)
#
#    asyncio.run(hello(ws_url))

def extract_build_id(build_log):
    match = re.search(r'OKRO_BUILD_ID=([^\\]*)\\', build_log)
    if match is None:
        print("Error: Can't find okro build id in log")
        sys.exit(1)
    build_id = match.groups()[0]
    print("okro build id:", build_id)
    return build_id

def deploy_build_okro(repo, commit_msg, repo_root_dir, build_id, okro_dir, org_name, repo_name, tabs):
    okro_file_name = os.path.join(repo_root_dir, "okro.yaml")
    if not os.path.exists( okro_file_name ):
        print("Error: file ", okro_file_name, "does not exist")
        sys.exit(1)

    file_changed = False
    with open(okro_file_name,'r') as yaml_file:
        detab_string = yaml_file.read().expandtabs(tabs)

        #obj = yaml.safe_load(yaml_file)
        obj = yaml.safe_load(io.StringIO(detab_string))
        print(str(type(obj)))
        #pprintex.dprint("obj:", obj)

        publications = []
        print("publication names:")
        for image in obj['actions'][0]['publications']['images']:
            print("name: ", image['name'])
            publications.append(image['name'])

        file_changed = deploy_to_okro(okro_dir, org_name, build_id, publications, repo_name, tabs)

    if file_changed:

        cmd = RunCommand()

        if cmd.run("git commit -a -m '" + commit_msg + "'")  != 0:
             print("Error: can't update master branch", cmd.make_error_message())
             sys.exit(1)

        #print("Creating okro pull request")
        #create_branch_and_pr(repo, "", commit_msg, "")

        if cmd.run("git branch -m '" + commit_msg + "'") != 0:
            print("Error: can't rename branch", cmd.make_error_message())
            sys.exit(1)

        if cmd.run("git push --set-upstream origin " + commit_msg + ":feature/" + commit_msg) != 0:
            print("Error: can't push to remote branch", cmd.make_error_message())
            sys.exit(1)

        print("**please visit url http://github.com/traiana/okro-lab and create okro pull request **")
        print(cmd.output)
        print("**deploy finished**")

def prepare_deploy(okro_dir):
    if not os.path.isdir(okro_dir):
        print("Error: okro directory: ", okro_dir, "does not exist")
        sys.exit(1)

    cmd = RunCommand()

    os.chdir(okro_dir)

    if cmd.run("git rev-parse --show-toplevel" ) != 0:
        print("Error: directory ", okro_dir, " is not part of git tree")
        sys.exit(1)

    remote_origin, repo_name = get_remote_origin()

    if repo_name != "okro-lab":
        print("Error: directory ", okro_dir, " is not in okro-lab repository, instead: ", repo_name)
        sys.exit(1)

    if cmd.run("git rev-parse --abbrev-ref HEAD") != 0:
        print("Error: can't get current branch name", cmd.make_error_message())
        sys.exit(1)
    local_branch_name = cmd.output.rstrip('\n')

    if local_branch_name != "master":
        # switch to master branch

        # check if local master branch exists
        cmd.run('git branch')

        has_master = False
        for line in cmd.output.rstrip('\n').splitlines():
            if re.search(r' master$', line) != 0:
                has_master = True
                break

        if has_master == 0:
            if cmd.run("git checkout origin/master -b master") != 0:
                print("Error: can't checkout master branch", cmd.make_error_message())
                sys.exit(1)
        else:
            if cmd.run("git checkout master") != 0:
                print("Error: can't switch to master branch", cmd.make_error_message())
                sys.exit(1)

    if cmd.run("git stash") != 0:
        print("Error: can' stash", cmd.make_error_message())
        sys.exit(1)

    if cmd.run("git pull --rebase") != 0:
        print("Error: can' pull from master branch", cmd.make_error_message())
        sys.exit(1)



def deploy_to_okro(okro_dir, org_name, build_id, publications, repo_name, tabs):

    prepare_deploy(okro_dir)
    file_changed = False

    for fname in glob.glob( okro_dir + '/**/*.yaml', recursive=True):
        if deploy_one_file(fname, org_name, build_id, publications, repo_name, tabs):
            file_changed = True
    print("repo-name:", repo_name)
    return file_changed


def deploy_one_file(fname, org_name, build_id, publications, repo_name, tabs):
    file_changed = False

    if RunCommand.trace_on:
        print("file:", fname)

    try:
        yaml_str = ''
        modified = False

        with open(fname,"r") as yaml_in:
            detab_string = yaml_in.read().expandtabs(tabs)
            docs = yaml.safe_load_all(io.StringIO(detab_string))

            docs_list = []
            for doc in docs:
                docs_list.append(doc)

            for doc in docs_list:
                if deploy_recurse_yaml(doc, org_name, build_id, publications, repo_name, 1):
                    modified = True

            if modified:
                for yaml_obj in docs_list:
                    if yaml_str != "":
                        yaml_str += "\n---\n"
                    pretty = yaml.round_trip_dump(yaml_obj)
                    yaml_str += pretty

        #result yaml
        if yaml_str != "":
            with open(fname,'w') as yaml_file:
                yaml_file.write(yaml_str)
                file_changed = True

    except:
        print(traceback.format_exc())
        print("**exception during yaml parsing!!!**")

    return file_changed

def deploy_recurse_yaml(obj, org_name, build_id, publications, repo_name, nesting):
    if RunCommand.trace_on:
        print((' ' * nesting) + "node:", str(obj))

    rval = False

    if isinstance(obj, list):
        for list_obj in obj:
            if deploy_recurse_yaml(list_obj, org_name, build_id, publications, repo_name, nesting+1):
                rval = True
    elif isinstance(obj, dict):
        if 'repo' in obj:
            repo_obj = obj['repo']
            if 'org' in repo_obj and repo_obj['org'] == org_name and \
                    'name' in repo_obj  and repo_obj['name'] == repo_name and \
                    'artifact' in obj:

                if RunCommand.trace_on:
                    print("repo tag found for", repo_name, "artifact", obj['artifact'])

                artifact = obj['artifact']
                if artifact in publications:
                    obj['version'] = build_id
                    print("set version for artifact", artifact)
                    rval = True
                else:
                    print("Warning: artifact", obj['artifact']," is not is publication list!")

        if not rval:
            for obj_value in obj.values():
                if deploy_recurse_yaml(obj_value, org_name, build_id, publications, repo_name, nesting+1):
                    rval = True

    return rval


def main():
    cmd_args, _ = parse_cmd_line()

    if cmd_args.verbose:
        RunCommand.trace_on = True

    repo_root_dir, top_commit, repo_name, local_branch_name, remote_branch_name, last_commit_sha_and_comment, last_commit_body, remote_origin_url = init()

    status = is_remote_ahead(remote_origin_url, local_branch_name, top_commit)
    if (cmd_args.new_pr or cmd_args.update_pr) and status == 0:
        print("Error: Can't update remote, both local and remote are in sync")
        sys.exit(1)

    if not "GITHUB_TOKEN" in os.environ:
        print("Error: GITHUB_TOKEN is no exported.")
        sys.exit(1)

    token = os.environ['GITHUB_TOKEN']
    github = Github(login_or_token="access_token", password=token)

    user_name = github.get_user().login
    print("github user-name:", user_name)

    org = cmd_args.org

    if org != '':
        org_obj = github.get_organization(org)
        repo = org_obj.get_repo(repo_name)
    else:
        repo = github.get_user().get_repo(repo_name)


    if cmd_args.new_pr:
        create_branch_and_pr(repo, local_branch_name, last_commit_sha_and_comment, last_commit_body)
    elif cmd_args.update_pr:
        push_state_to_branch(remote_branch_name)
    elif cmd_args.wait:
        pass
    elif cmd_args.use_last_tag:
        pass
    else:
        print("Error: action not specified")
        sys.exit(1)

    if not cmd_args.use_last_tag:
        status, url = wait_for_commit_to_build(repo, top_commit)
        if status:
            print("\nBuild succeeded! url: ", url)
            beep(True)
        else:
            print("\nBuild failed. url: ", url)
            beep(False)

        if cmd_args.showlog:
            show_build_log(url)

        build_log  = dump_build_log(url)
        if cmd_args.okrodir != "" and status:
            build_id = extract_build_id(build_log)
            deploy_build_okro(repo, repo_name + "-" + last_commit_sha_and_comment, repo_root_dir, build_id, cmd_args.okrodir, org, repo_name, cmd_args.tabs)
            print("*** deploy to okro completed successfully ***")
    else:
        build_id = get_last_tag()
        if cmd_args.okrodir != "" and build_id is not None:
            print("last remote tag: ", build_id)
            deploy_build_okro(repo, repo_name + "-deploy-tag-" + build_id, repo_root_dir, build_id, cmd_args.okrodir, org, repo_name, cmd_args.tabs)

if __name__ == '__main__':
    main()
