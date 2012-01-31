#!/usr/bin/python -W ignore::DeprecationWarning
"""
Git-Tool - a utility set for easier use of git

Available services:
   gbu: Git BackUp, commit changes in the working copy to local repository
   gpt: Git PuT, to put the local changes to the remote repository
   gif: Git InFo, shows basic information of the current version
   gst: Git STatus, list modified/added/removed files between versions/branches
   gbr: Git Switch, switch/create to a branch/tag, remotely or locally
   gdi: Git DIff, compare file/s between versions/branches
   ggt: Git GeT, to get a copy of the target repository
   ghelp: help info for GITUtil
Proposed services:
   gfl: Git File, to fetch a file from a version
   gpa: Git PAtch
Dependencies (please install):
   git: Git-Tool is a wrapper of git
   graphviz and qiv: Git-Tool needs both to show graphical version tree via gifg
"""
import os
import re
import sys
import pexpect
import fnmatch
import subprocess
import pdb
from optparse import OptionParser

"""
TODO: think about a mechanism to handle unintensional interruption during, say, committing
TODO: check files in /usr/lib/git-core in workstation and see how to enable write permission when doing vimdiff
TODO: make use of easy install?
TODO: add write functionalities to gitconfig
"""

#-------------------GLOBAL SETTINGS-------------------
# Edit the following settings to make GITTool fits your need
DEBUG = False
COLOR = True
PROMPT_SIGN = ':> ' # unichr(0x263B) will show a smiling face.

color = dict()
color['none'] = ''
if COLOR:
    color['red'] = '\033[01;31m'
    color['green'] = '\033[01;32m'
    color['yellow'] = '\033[01;33m'
    color['blue'] = '\033[01;34m'
    color['magenta'] = '\033[01;35m'
    color['lightblue'] = '\033[01;36m'
    color['white'] = '\033[01;37m'
    color['gray'] = '\033[01;30m'
    _end_ = '\033[00m'
else:
    color['red'] = ''
    color['green'] = ''
    color['yellow'] = ''
    color['blue'] = ''
    color['magenta'] = ''
    color['lightblue'] = ''
    color['white'] = ''
    color['gray'] = ''
    _end_ = ''

#-------------------SERVICE FUNCTIONS-------------------
#All the service functions are linked directly to corresponding git-tool services.
#No git command will be invoked in these functions.

def GITBackup(srv = '', param = ''):
    """ gbu
        commit/backup the changes to the local repository
             Changes can be back-up to the current branch, or another branch you
             select from the given list
             you can also generate a patch of your changes to store the patch
             somewhere else.
    """
    _current_branch = _get_current_branch()
    if _current_branch == 'master':
        _ans=_get_answer(prompt = 'Are you sure to back up in ' +\
                                color['red'] + 'master ' + _end_ + 'branch? [y/N]',
                         help = 'In most cases what you need is to back up to\
                                 your own branch in order to merge or further\
                                 branch out later. So are you sure?')
        if _ans is not 'y' and _ans is not 'Y':
            if _switch_branch() == '':
                _exit()
    else: #this is a branch other than master
        _ans = _get_answer(prompt = 'back up in ' +
                           color['red'] + _current_branch + _end_ + '? [Y/n]')
        if _ans == 'n' or _ans == 'N':
            if _switch_branch() == '':
                _exit()
    _msg = ''
    while _msg is '':
        _msg = _get_answer(prompt = 'Any comment? [empty comment is not allowed]')
    _msg = '"' + _msg + '"'
    _result = _invoke(['git commit -a -m %s' % _msg])
    #to allow local backup in one's home directory
    _ans = _get_answer(prompt = 'Backup the changes to a patch also? [y/N]',
                       help = "say y or Y if you like to make a patch file for the change")
    if _ans == 'y' or _ans == 'Y':
        _file_list, _version_str = _get_version_change(with_previous_version = True)
        if _file_list is None or _version_str is None:
            _exit();
        _tmp = _invoke([_git_patch(selection = _version_str)])
        _ans = _get_answer(prompt = 'where to store the patch file?')
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):
            _ans=_get_answer(prompt = "The path doesn't exist. Try to make the directory? [Y/n]",
                            help = '')
            if _ans == 'n' or _ans == 'N':
                _exit()
            else:
                os.makedirs(_target_dir)
        _invoke(['mv /tmp/backup.patch %(target)s/backup.%(verstr)s.patch ' %\
                 {'target': _target_dir, 'verstr': _version_str}])
        return _result + '\nbackup saved as %(target)s/backup.%(verstr)s.patch ' %\
               {'target': _target_dir, 'verstr': _version_str}
    else:
        return _result

def GITBranch(srv, param):
    """ gbr
        Git BRanch, to perform list/switch to/create/delete on git branches
        gbr(rt): Without argument 'gbr' shows a list of local branches:
                    To switch to a branch, pick the branch by index.
                    To create a branch, type the branch name.
                    To delete a branch, do '/d <branch_index>'
                    To quit, do '/e' or return directly.
                 A 'gbr <branch_name>' will
                    switch to the branch if the branch exists, or
                    make and switch to the branch if it doesn't exist
                 with (r) to do similar operations but on remote branches.
                    Currently support operations are:
                        switch to a remote branch
                 with (t), 'gbrt <tag_name>' will switch to a branch has the tag on
    """
    _check_git_path()
    _hastag, _isremote = ('t' in srv), ('r' in srv)
    _num_args = len(param)
    _hasbranch = (_num_args == 2 and not _hastag)
    _bname = _tname = ''
    if _hasbranch is _hastag is False: #user doesn't give any arguments
        return _switch_branch(_isremote) #select a branch a list of local/remote branches
    else: #user gives either a branch name, or a tag
        _name = param[1]
        _cmd = _git_checkout()
        if _hasbranch is True: #checkout a branch with the given branch name
            _tmp, _branch_list = _get_branch_list()
            if _name in _branch_list: #switch to an existing branch
                _cmd += _name
            else: #branch doesn't exist, make it
                return _make_branch(_name)
        if _hastag is True: #checkout a branch with the given tag
            _branchname = _get_answer(prompt = 'branch name to keep the remote branch data: ',
                                      help = 'To get a remote branch, \n\
                                              it is required to create a local branch first')
            _tname = param[1]
            if _branchname.strip() == '':
                _exit_with_error("A branch name is required, the 'nobranch' is not recommended")
            else: #check out a new branch to hold the remote data with the given tag
                _cmd += '%(tag)s -b %(newbranch)s' %\
                        {'tag': _tname, 'newbranch': _branchname}
        return _invoke([_cmd])

def GITConfig(srv, param):
    """ gcf
        show the configuration of the current repository and the global settings.
        it is also possible to modify the values interatively with this tool.
        available items:
            branch name
            remote value
            merge value
    """
    _check_git_path()
    #local settings
    _current_branch = _get_current_branch()
    _current_branch_remote = _get_local('branch.%s.remote' % _current_branch)
    _current_branch_merge = _get_local('branch.%s.merge' % _current_branch)
    _remote_branch = _get_remote_branch()
    #global settings
    _email = _get_global('user.email')
    _username = _get_global('user.name')
    _first_diff_tool = _get_global('difftool.first')
    _second_diff_tool = _get_global('difftool.second')
    _third_diff_tool = _get_global('difftool.third')
    #make up the output
    _ret = ""
    _ret += color['yellow'] + "---Local Settings---\n" + _end_
    _ret += "current branch: %s\n" % _current_branch
    _ret += "remote value: %s\n" % _current_branch_remote
    _ret += "merge value: %s\n" % _current_branch_merge
    _ret += "remote branch: %s\n" % _remote_branch
    _ret += color['yellow'] + "---Global Settings---\n" + _end_
    _ret += "user name: %s\n" % _username
    _ret += "user email: %s\n" % _email
    _ret += "1st diff tool: %s\n" % _first_diff_tool
    _ret += "2nd diff tool: %s\n" % _second_diff_tool
    _ret += "3rd diff tool: %s\n" % _third_diff_tool
    return _ret

def GITDiff(srv, param):
    """ gdi
        gdi(r)(v)(f)(1/2): show the files' differences in many ways
                with(r) to show the diff between the working copy and the remote
                   master
                without (r) to show the diff between local versions/branches
                   branch HEAD(configurable)
                with (v) to show the diff between local versions/branches
                   do 'gdiv <version1>..<version2>' to compare between two versions
                   do 'gdiv <version>' to compare between the working copy with
                   'version'
                   do 'gdiv ?' to pick a version from the version list and compare
                   with the local copy.
                   NOTE: comparing can only be between local versions
                with (f) to compare the difference of a file between two versions
                   combined with 'v', do 'gdivf <version1>..<version2> <filename>' or
                   do 'gdivf <version1> <filename>'
                   to compare between the local copy and the local HEAD:
                   do 'gdif <filename>'
                with (1/2/3) to diff with a difftool that is configured when you setup
                   this tool. this is useful to switch between ascii tool like vimdiff
                   and gui tools like meld, beyondcompare
                   do a 'gdi' to use the default difftool
                   do a 'gdi1' to use the secondary difftool
                   do a 'gdi2' to use another difftool

    """
    _check_git_path()
    _isremote, _isversion, _isfile = ('r' in srv), ('v' in srv), ('f' in srv)
    _difftool = _file = _versions = _remote_branch = ''
    #look for the user preferred diff tool
    if '1' in srv:
        _difftool = _get_global('difftool.second')
    elif '2' in srv:
        _difftool = _get_global('difftool.third')
    if not _difftool: #try to get the default diff tool in this case
        _difftool = _get_global('difftool.first')
    if _isversion: #look for the version string
        for x in param[1:]:
            if re.search('^[0-9a-fA-F]+\.\.[0-9a-fA-F]+$', x) is not None:
                _versions = x #this seems like a <ver>..<ver> string
                break
            if re.search('^[0-9a-fA-F]+$', x) is not None:
                if _if_ver_exist(x) is True: #this seems like a <ver> string
                    _curversion = _get_versions(1)[0]
                    _versions = _curversion + '..' + x #make up the version string
                    break
                else:
                    continue #cannot find the version, keep checking the rest params
        if _versions is None: #cannot find a valid version string
            _exit_with_error("cannot identify two versions to compare\n")
    if _isfile: #look for a given file
        for x in param[1:]:
            if os.path.isfile(x) is True:
                _file = x
                break
        if _file is None: #cannot find a valid file name in the param
            _exit_with_error("cannot identify a valid file name\n")
    if _isremote == False: #handle local diff operation.
        if _isversion == True: # version diff is only supported locally
            if '?' == _versions: #allow user to select versions on the fly
                _versions = _select_version()
    else: #handle remote diff operation
        _remote_branch = _get_remote_branch()
    _cmd = 'git difftool -y -t %(t)s %(v)s %(r)s %(f)s' %\
           {'t': _difftool, 'v': _versions, 'r': _remote_branch, 'f': _file}
    #if there are too many files, warn the user before doing diff
    if _number_of_changed_files(_versions, _remote_branch, _file) > 7: # i guess 7 is a good limit
        _ans = _get_answer(prompt = 'seems like there are too many to compare, continue?[y/N]')
        if _ans != 'y' and _ans != 'Y':
            _exit()
    #for vim it appears we need to invoke it via os.system to make it work correctly
    if _difftool == 'vimdiff':
        os.system(_cmd)
    else:
        print(_cmd)
        _tmp = _invoke([_cmd])
    return ''

def GITGet(srv, param):
    """ ggt
        get a latest copy of the specified repository/branch
        the 'get' could be a 'git clone', or a 'git fetch' followed by
        a 'git merge' or a 'git rebase'
        once a new source is checked out, the tool will remember the path.
        next time when checking out from the same source, the user can pick
        the source from a list
    """
    #1. check if only update the local is requested
    if _root_path() is not None:
        if _num_uncommited_files() > 0:
            print("There are still files unstaged/uncommited." +
                  "Please use gbu to commit all your changes before" +
                  "updating this repository")
            _exit()
        _ans = _get_answer(prompt = "Update the current branch? [Y/n]",
                           help = "'n' or 'N' will lead you to a 'git clone', " +
                                  "with any other input will update the local branch")
        if _ans != 'n' and _ans != 'N':
            _update_local_branch()
            return "done"
    #2. get the source
    _source_list = _get_source_list() #the list of known resources from the global config file
    _color = color.values()
    for r, _index in zip(_source_list, range(len(_source_list))):
        print("%d  -  %s" % (_index, r))
    _tmp = _get_answer(prompt = 'What source would you like to clone from',
                       help = 'select the source by the index number, if available.\n' +
                              'or type in the repository/branch')
    #TODO: check if the local config merge and remote values are correct
    if re.match('^\d+$', _tmp) is not None:
        _ifnew = False #seems like a know source is selected
        _source = _source_list[int(_tmp)]
    else:
        _ifnew = True #new source specified by the user?
        _source = _tmp
    #3. fetch or clone the source
    if re.match('^git@.*:.*', _source) is not None:
        #TODO:need to consider if the user like to update but accidentally comes here
        _ifclone = True #this seems like a clone request
        _cmd = _git_clone(_source)
    else:
        _ifclone = False #this could be a fetch request
        if _root_path() is None:
            return "Seem like you are trying to fetch a branch, but in no git reporitory" +\
                   "You might consider issue the command in a repository..."
        _branch_name = _source.split('/')[-1]
        #the local path is generated by replacing the 'refs/' at the front to 'refs/remotes/'
        _local_repo = _source.replace('refs/', 'refs/remotes/', 1)
        _cmd = _git_fetch(src = _source, dst = _local_repo)
    _tmp = _invoke([_cmd])
    if _ifclone is False:
        #it is a fetch, make a local branch and switch to the new branch
        _make_branch_link_to_local_repo(_branch_name, _local_repo[5:]) #skip the 'refs/'
    #4.update the global config file with the checked out source path
    if _ifnew is True:
        _add_to_source_list(_source)
    return _tmp

_dot_file = '/tmp/gittool.dotty.tmp'
_svg_file = '/tmp/gittool.dotty.svg'
def GITInfo(srv, param):
    """gif
       to display the version/branch/tag info
       gif(tg): gif <n> shows n latest versions' info
                    when no parameter is given, only the current version info will be shown
                gif <since version> <until version>
                    display all the versions between the since_version and the until_version
                    e.g 'gif 3 0' shows the versions from HEAD to the 3rd parent of HEAD
                        'gif 7 4' shows the versions from the 4th parent to the 7th parent of HEAD
                    * the tool is smart enough even you put the two versions in the other order =)
                with (t) you will get the tag info if there is any.
                    * fetching tag info would take a bit more time
                with (g) you will get graphic version tree expression based on a dot file.
                    *NOTE*: graphviz is required to enable the 'g' option
    """
    _check_git_path()
    _if_graphic, _if_show_tag = ('g' in srv), ('t' in srv)
    _since = _until = _num = 0
    if len(param) == 3: #start and end of a version segment is given.
        _since, _until  = int(param[1]), int(param[2])
    elif len(param) == 2: #the number of versions is given.
        _num = int(param[1])
    else: #default, show the latest version info
        _num = 1
    if _if_graphic is True:
        if _num != 0:
            _range = 'HEAD' + _num * '^' + '...HEAD'
        _format = '"%h" [label="<f0> %h|<f1> %an"]\n"%h":f0 -> {%p}'
    else:
        if _num != 0:
            _range = '-%d' % _num
        else:
            _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                    {'num_of_log': abs(_since - _until) + 1,
                     'num_to_skip': min(_since, _until) - 1}
        _format='___%nRev:       %h%nDate:     %cd%nComment:  %s' #TODO: add branch here
    if _if_show_tag is True: #show the tag info
        print("this will take a while...")
        _cmd = _git_log(version = _range, format = '%ad|%h|%s|%d',
                        param = '--abbrev-commit --date=short')
        _logs = _invoke([_cmd]).split('\n')
        _result = ''
        for _line in _logs:
            [_date, _hash, _comment, _tmp] = _line.split('|')
            _tmp = _tmp.strip(' ()').split(', ')
            _branch = _get_branches_with_commit(_hash)
            try: #check if the hash has tags attached
                _container_tags = _invoke(["git tag --contains %(hash)s" %
                                           {'hash':_hash}
                                          ]).split('\n')
                #get the tags on this specific version
                _tags = list(set(_tmp) & set(_container_tags))
                _result += '___\n'
                _result += 'Rev: %s\nDate: %s\nBranch: %s\nComment: %s\nTags: %s\n' %\
                           (_hash, _date, _branch, _comment, _tags)
            except AttributeError: #a version without any tag
                _result += '___\n'
                _result += 'Rev: %s\nDate: %s\nBranch: %s\nComment: %s\n' %\
                           (_hash, _date, _branch, _comment)
        return _result
    _result = _invoke([_git_log(version = _range, format = _format)])
    #TODO: how to show the branch name in the graph???
    if _if_graphic is True:
        _result = 'digraph G{\nnode [shape=record]\n'\
                + re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', _build_merge_arrows, _result)\
                + '}' #get data ready for dotty
        with open(_dot_file, 'w') as f:
            f.write(_result)
        _tmp = _invoke(['dot -Tsvg %s > %s' % (_dot_file, _svg_file)])
        _cmd = ['qiv', _svg_file]
        return _invoke(_cmd, detached=True) #feed the data to dotty
    return _result

def GITMerge(srv, param):
    """ gmg
        Git MerGe changes in a branch to another.
    """
    _check_git_path()
    #get local/remote branch list
    _cur_branch_index, _branch_list = _get_branch_list(False)
    _branch_list += _get_branch_list(True)[1]
    _ball = BranchBall(_branch_list)
    #ask for the 'from' branch
    _from = _get_answer(prompt = 'Select the branch to merge ' + color['red'] + 'from' + _end_,
                        hl = _cur_branch_index, ball = _ball)
    #ask for the 'to' branch
    _to = _get_answer(prompt = 'Select the branch to merge ' + color['red'] + 'to' + _end_,
                      hl = _cur_branch_index, ball = _ball)
    #do the merge
    return _merge_branch(_branch_list[int(_from)], _branch_list[int(_to)])

def GITPut(srv, param):
    """ gpt
        Git PuT the local changes to a remote repository
        A 'gpt' will try to push the changes to a previously used branch.
        [not implemented yet] Do 'gpt <branch-path>' to push the changes to a new branch.
    """
    _check_git_path()
    _url = _get_remote_url()
    if _url is None:
        _ans = _get_answer(prompt = "would you like to manually type in the url? [y/N]",
                           help = "the url of the remote repository has not yet been set.\n" +
                                  "You have to tell where you'd like to push your changes, \n" +
                                  "or exit to fix it in other means.")
        if _ans == 'y' or _ans == 'Y':
            #TODO: need to add function for adding a remote section
            #_url = _get_answer(prompt = "url = ", help ='')
            _exit_with_error('not implemented yet')
        else:
            _exit()
    else:
        _ans = _get_answer(prompt = "push to %s ?[Y/n]" % _url,
                           help = "")
        if _ans == 'n' or _ans == 'N':
            _exit()
    return _push_to_remote() #do a push with the given url

#setup the environment for first use
def GITSetup(param):
    if len(param) == 2 and param[1] == 'clean':
        print("removing all the link files...")
        _traverse_nested_list_with_action(SERVICES, _remove_link_file)
        print("restore the .gitconfig file")
        _invoke(['cp ~/.gitconfig ~/.gitconfig.gittool'])
        _invoke(['mv ~/.gitconfig.gittool.backup ~/.gitconfig'])
        _exit()
    _ans = _get_answer(prompt = 'Would you like to setup GITTool? [y/N]',
                    help = 'This will simply create a bunch of symbol links for you.\
                          \nSo would you like to setup GITTool? [y/N]')
    if 'y' == _ans or 'Y' == _ans:
        _invoke(['cp ~/.gitconfig ~/.gitconfig.gittool.backup'])
        print("back up the original .gitconfig file")
        print("if your system supports colored text, you shall see them below:")
        for c in color.keys():
            print(color[c] + c + _end_)
        _ans = _get_answer(prompt = 'do you see the colors?[Y/n]')
        if _ans == 'n' or _ans == 'N':
            _set_global('GitTool.ColorSupport', 'no')
        else:
            _set_global('GitTool.ColorSupport', 'yes')
        #setup the difftools
        print("Valid merge tools are: araxis, bc3, diffuse, emerge, ecmerge, gvimdiff, kdiff3," +
              "kompare, meld, opendiff, p4merge, tkdiff, vimdiff and xxdiff.")
        _ans = _get_answer(prompt = "Please specify your first choice of diff tool:",
                           help = "it will be used as the default tool when diff")
        _set_global('difftool.first', _ans)
        _ans = _get_answer(prompt = "and your second choice of diff tool?",
                           help = "it will be used as the secondary tool when diff.\
                                 \nleave it blank if you don't have a secondary diff tool")
        _set_global('difftool.second', _ans)
        _ans = _get_answer(prompt = "and your third choice of diff tool?",
                           help = "it will be used as the third tool when diff\
                                 \nleave it blank if you don't have a secondary diff tool")
        _set_global('difftool.third', _ans)
        #set the graphic info tool settings
        #setup the symbolic links
        print("Please specify where you would like to put the GITTool facilities")
        print("[eg. '~/bin/GTool', '/tools']")
        print("\nMake sure the path is in your PATH variable")
        _ans = _get_answer(help = "The GitUtilTool works based on" +
                                 color['red'] + " A LOT OF " + _end_ + "small link files\n" +
                                 "It's suggested to make a dedicated directory for the tool")
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):
            _ans=_get_answer(prompt = "The path doesn't seem to exist. Make the directory? [Y/n]",
                            help = "I will try my best to create the directory/ies.\
                                    \nWould you like me to do that for you?")
            if _ans == 'n' or _ans == 'N':
                _exit()
            else:
                os.makedirs(_target_dir)
        _source_path = os.path.dirname(__file__)
        for service in SERVICES:
           _source = os.path.relpath(_source_path, _target_dir) +\
                     "/" +\
                     os.path.basename(__file__)
           if type(service) == list:
               #this is a nested list, right now we support 2-level nested list
               for sub_service in service:
                   _invoke(["ln -s %(source)s %(link)s" %
                           {'source' : _source, 'link' : _target_dir + '/' + sub_service}])
           else:
               _invoke(["ln -s %(source)s %(link)s" %
                       {'source' : _source,
                        'link' : _target_dir+'/'+service}])

        print("done.\ntry ghelp for more info")

def GITStatus(srv, param):
    """
    gst
    show the status (what have been changed) between repositories, branches or versions.
    gst(rd): without (rd) and any parameters, is equal to 'git status -s', showing the changed
             files between working copy and the HEAD of current local branch.

             when followed by a version/branch string, 'gst' will show the changed files between
             two versions or branches' HEAD
             examples are "<branch1>..<branch2>", changes between branch1 HEAD and branch2 HEAD
                          "<branch>": changes between current working copy and branch
                          "<version sha1>..<version sha2>": changes between sha1 and sha2
                          "<version sha>": changes between current working copy and sha
                          other git valid version strings

             with (r), show the changed files between the current branch (in local repository)
             with that of its remote branch (REMOTE_BRANCH by default)

             with (d), the tool will only show a list of changed files in the
             current directory
    """
    _git_status_code =\
    """
        XY PATH1 -> PATH2 maps to
        [Stage Status][Worktree Status] [Path in HEAD] -> [Path in Stage/Worktree]
            _ = unmodified
            M = modified
            A = added
            D = deleted
            R = renamed
            C = copied
            U = updated but unmerged

            Ignored files are not listed, unless --ignored option is in effect,
            in which case XY are !!.

            X        Y    Meaning
            ----------------------------------------------
            _       [MD]  not updated
            M      [_MD]  updated in index
            A      [_MD]  added to index
            D       [_M]  deleted from index
            R      [_MD]  renamed in index
            C      [_MD]  copied in index
            [MARC]    _   index and work tree matches
            [_MARC]   M   work tree changed since index
            [_MARC]   D   deleted in work tree
            ----------------------------------------------
            D         D   unmerged, both deleted
            A         U   unmerged, added by us
            U         D   unmerged, deleted by them
            U         A   unmerged, added by them
            D         U   unmerged, deleted by us
            A         A   unmerged, both added
            U         U   unmerged, both modified
            ----------------------------------------------
            ?         ?   untracked
            !         !   ignored
            ----------------------------------------------

        When comparing between versions/branches, there will be no detailed status code.
        In Git-Tool a '*' is used in this case instead.

        * http://progit.org/book/ch2-2.html has more details
    """
    _check_git_path()
    _isdir, _isremote = ('d' in srv), ('r' in srv)
    _compare_str = param[1] if len(param) > 1 else ''
    if _isremote is True:   #comparing with the remote branch
        try:
            _compare_str = _get_remote_branch()
        except ConfigItemMissing:
            _exit_with_error("There are item or section missing in the config file")
    #depends on the compare_str, this could be a'git status' or a 'git diff''
    _cmd = _git_diff(selection = _compare_str, name_only = True) if _compare_str\
            else _git_status(param = '-s')
    if _isdir is True: #only show the touched files in the current directory
        _cmd += ' -- ' + os.getcwd()
    _tmp = _invoke([_cmd])
    _status = _translate_status_code(_cmd, _tmp)
    _final_str = '' # prepare for a prettified outcome
    if _compare_str:#show changed files between two commits
        if '..' in _compare_str: #two compare candidates are given
            _comp2, _comp1 = _compare_str.split('..')
        else:
            if _if_branch_exist(_compare_str) is True: #only one candidate given, which is a branch
                _comp2, _comp1 = _compare_str, _get_current_branch()
            elif 'unknown revision' in _status: #something wrong with the given candidate
                _exit_with_error('unknown version/branch, please check')
            else:#assume this is comparison between versions
                _comp2, _comp1 = _compare_str, _get_versions(1)[0]
            _changed_not_commited_sign = 'MODIFIED ' if _get_changed_uncommited_file_list()\
                                              else ''
            _comp1 = _changed_not_commited_sign + _comp1
        if _status is None or _status.strip(' ') is None:
            _status = '' #there is no changes found
            _changes = 0
        else:
            _changes = len(_status.split('\n')) - 1
        _changed = _status.split('\n')[:-1]
        _untracked= []
    else: #show changed but not yet commited files, with indexes added
        _changed, _untracked= _get_changed_files(_status)
        _changes = len(_changed)
        _comp2, _comp1 = _get_current_branch(), 'working copy'
    _total = 'Changed files: ' + color['red'] + str(_changes) + _end_
    _files = FileBall(_changed + _untracked)
    _ans = _get_answer(prefix = _make_msg_bar(_make_status_header(_comp1, _comp2)), prompt = '',
                       ball = _files,
                       help = _git_status_code + '/d to revert a changed file, or Enter to quit')
    return ''

#-------------------INTERNAL CLASSES-------------------
class Ball(object):
    """
    A ball is a carrier that holds the output of a git-tool helper function
    the carrier is able to perform certain operations on the data it holds.
    """
    def __init__(self, list, **param):
        self._list = list     #all the data will be stored in a list
        self._param = param   #for any future extended functionalities
    def __getitem__(self, k):
        return self._list[k]
    def get_list(self):
        return self._list
    def get_indexed_list(self, highlight):
        return _index_list(self._list, highlight = highlight)
    def delete(self, item_list, func):
        item_list.sort(reverse=True) #remove the very last item in the list first
        for x in item_list:
            _result, _msg = func(self._list[x])
            if _result is True: #user might choose not to delete
                self._list.remove(self._list[x])
            print _msg

class BranchBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list, **param):
        super(BranchBall, self).__init__(list)
    def delete(self, item_list):
        super(BranchBall, self).delete(item_list, _delete_branch)

class FileBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list, **param):
        super(FileBall, self).__init__(list)
    def delete(self, item_list):
        super(FileBall, self).delete(item_list, _revert_file_item)

class SourceBall(Ball):
    """
    A ball that holds a list of sources
    """
    def __init(self, list, **param):
        super(FileBall, self).__init__(list)
    def delete(self, item_list):
        for x in item_list:
            if _delete_source(self._list[x]) is True: #user might choose not to delete
                super(FileBall, self).delete_item(x)

class GITError(Exception):
    """base class of all GitTool error exceptions"""

class ConfigItemMissing(GITError):
    """The item/section in the git config file does not exist"""

#-------------------INTERNAL HELPPER FUNCTIONS-------------------
#The internal helpper functions are used by the service functions.
#Based on git direct call functions, the helpper functions fulfill certain git-tool sub features.
#No direct git command calls will be made in these functions.

#-------------------basic and misc helppers
#the services provided by the git tool box, used for creating the links
## {{{ http://code.activestate.com/recipes/577842/ (r1)
def allperm(inputstr):
    for i in range(len(inputstr)):
        yield(inputstr[i])
        for s in allperm(inputstr[:i] + inputstr[i+1:]):
            yield(inputstr[i] + s)
## end of http://code.activestate.com/recipes/577842/ }}}

#invoke bash commands
def _invoke(cmd, detached = False):
    if DEBUG == True: #for debug only
        print(color['yellow'] + ''.join(cmd) + _end_)
        return
    if detached is False:
        execution=subprocess.Popen(cmd,
                                   shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        o=execution.communicate()
        if o[1]: #return error if there is any
            return o[1]
        if o[0]: #only return the std result, when there is no error
            return o[0]
    else: #invoke bash commands in separate process, no error return
        subprocess.Popen(cmd, stderr=subprocess.PIPE)
        return ""

#helper function to prompt users information and receive answers
def _get_answer(prefix = '', prompt = '', postfix = '',
                help = 'No help available... ', ball = None, hl = -1):
    if 'No help available... ' != help: # show prompt in a different color if help is available
        _ps = color['lightblue'] + PROMPT_SIGN + _end_
    else:
        _ps = PROMPT_SIGN
    if ball: # when a ball is given, show the item list in the ball.
        _prompt = (prefix + '\n' if prefix else '') +\
                  '\n'.join(ball.get_indexed_list(highlight = hl)) + '\n' +\
                  (postfix + '\n' if postfix else '') + prompt
    else:
        _prompt = prompt
    _ans = raw_input(_prompt + _ps).strip(' ')
    while _ans == '/h':
        _ans = raw_input(help + _ps)
    if '/e' == _ans:
        _exit()
    elif _ans.startswith('/d '):
        if ball is None:
            _exit_with_error("no ball is passed while a delete is required")
        if re.search('^\/d\s+\d+([\s,-]+\d+)*\s*$', _ans): #space or ',' can be used as separator
            #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
            _tmp = re.sub('\d+[\s]*-[\s]*\d+', _expand_indexes_from_range, _ans[3:])
            ball.delete([int(x.group()) for x in re.finditer('\d+', _tmp)]) #get all indexes
        else:
            _exit_with_error("to delete an item, try '/d <index>'")
        #show the prompt and item list after deletion
        return _get_answer(prefix = prefix, prompt = prompt, postfix = postfix,
                           help = help, ball = ball, hl = hl)
    else:
        return _ans

#show a list of items with index and one of the item highlighted
def _index_list(list, index_color = 'none', highlight = -1, hl_color = 'red'):
    return ['%s%d >> %s\t%s' %
            (color[hl_color if index == highlight else index_color],
             index, _end_, x)
            for (index, x) in zip(range(0, len(list)), list)]

#this function will expand strings like '1-3' to '1 2 3'
def _expand_indexes_from_range(obj):
    _tmp = ''
    _line = obj.group()
    _range = _line.split('-')
    for x in range(int(_range[0]), int(_range[1]) + 1):
        _tmp += ' %d ' % x
    return _tmp

#used in re.sub to modify the matching string
def _build_merge_arrows(obj):
    _tmp = ''
    _line = obj.group()
    _from = _line[1:8]
    _list = re.findall('[a-f0-9]{7}', _line[7:])
    for x in _list:
        _tmp += '"%(v)s":f0 -> "%(f)s":f0 [color=blue style=bold arrowhead=vee]\n' %\
                {'f':_from, 'v':x}
    return _tmp

#print the header of status result
def _make_status_header(ver1, ver2):
    return '[' + color['red'] + ver1 + _end_ + ']' + ' v.s ' +\
           '[' + color['red'] + ver2 + _end_ + ']'

#print message with a fixed length bar
def _make_msg_bar(msg):
    _colorless_msg = msg
    _colorless_msg = re.sub('\033[^m]*m', '', _colorless_msg) #remove the color code
    _msg_len = len(_colorless_msg)
    _pre = '_' * ((80 - _msg_len) / 2)
    _post = '_' * ((80 - _msg_len) / 2 + (80 - _msg_len) % 2)
    return _pre+msg+_post+'\n'

#exit with error
def _exit_with_error(msg = ''):
    print("Exit with error :\n" + msg)
    sys.exit()

def _exit():
    sys.exit()

#do something by traversing the given nested list
def _traverse_nested_list_with_action(lst, action):
    for x in lst:
        if isinstance(x, list):
            _traverse_nested_list_with_action(x, action)
        else:
            action(x)

# translate the output of git status -s into git-tool's format
def _translate_status_code(cmd, ori):
    if ori is None:
        return ''
    else:
        if cmd.startswith('git status'): #status code is given by git status
            return re.sub('^[MADRC ]{2}|\n[MADRC ]{2}', #replace space status code to '_'
                          lambda x : x.group().replace(' ', '_'),
                          ori)
        else: #status code is not available when command is git diff
            return re.sub('^|\n', #no status code is available when using git diff
                          lambda x: x.group() + '*  ',
                          ori)

#-------------------branch helppers
#merge branch, assuming frombr and tobr are valid branches
def _merge_branch(frombr, tobr):
    _cur = _get_current_branch()
    _invoke([_git_checkout(target = tobr)]) #switch to the target branch
    _tmp = _invoke([_git_merge(frombr)]) #try auto merge
    if 'Automatic merge failed' in _tmp: #need manual merge
        os.system(_git_mergetool())
        _tmp = 'Done'
    _ans = _get_answer(prompt = 'merge complete. back up the merge now?[y/N]')
    if _ans == 'y' or _ans == 'Y':
        GITBackup()
    return _tmp

#show a lost of local/remote branches and do something
def _switch_branch(isremote = False):
    _curbranch, _branch_list = _get_branch_list(isremote)
    _listball = BranchBall(_branch_list)
    _selected = _get_answer(prefix = '---Branch List ---',
                            help = "You can: \
                                       \n   Enter branch index or,\
                                       \n   Type the name for a new one or,\
                                       \n   Use '/d <branch_name>' to delete a branch\
                                       \n   Press Enter to quit",
                                    ball = _listball,
                                    hl = _curbranch)
    if _selected == '':
        return "" #return if no branch is selected or created
    elif re.search('^\d+$', _selected): #a selected index
        _selected_branch = _listball[int(_selected)]
    else: # probably a new branch name
        _selected_branch = _selected
    _tmp = ''
    for line in _branch_list:
        if line != '' and _selected_branch == line.split()[-1]:
            if isremote is True:
                _local_branch = _get_answer(prompt = "Give a name for the new local branch:",
                                            help = "if give no name you will be on " +
                                                   color['red'] + "NO " + _end_ +
                                                   "branch and we don't recommend that")
                if '' == _local_branch:
                    return ''
                else:
                    _tmp = _invoke([_git_checkout(target = _selected_branch,
                                                  new_branch = _local_branch)])
            else:
                _tmp = _invoke([_git_checkout(target = _selected_branch)])
            return _tmp
    #we are here because the selected branch is not in the list
    return _make_branch(_selected_branch)

def _make_branch(branch):
    _previous_branch = _get_current_branch()
    _tmp = _invoke([_git_branch(branch = branch)]) #create branch with the name given
    _tmp = _invoke([_git_checkout(target = branch)])
    _set_branch_config(branch_from = _previous_branch) #new branch, set the config properly
    _result = 'created and switched to new branch: ' + color['red'] + branch + _end_ + '\n'
    _result += 'config is set based on ' + color['red'] + _previous_branch + _end_
    return _result

def _make_branch_link_to_local_repo(bname, path):
    _cmd = _git_checkout(target = bname, track = path)
    _invoke([_cmd])

def _get_branches_with_commit(hash):
    _cmd = _git_branch(contains = hash)
    return [x.strip(' *') for x in _invoke([_cmd]).split('\n') if x is not '']

def _update_local_branch():
    #1. fetch the updates from remote repo
    _current_branch = _get_current_branch()
    _remote = _get_local('branch.%s.remote' % _current_branch)
    _merge = _get_local('branch.%s.merge' % _current_branch)
    if _remote and _merge: #only initiate fetch when the config values are correct
        print("fetching from %s ..." % _remote)
        print(_invoke([_git_fetch()]))
    else: #quit if the corresponding config items are not set
        _exit_with_error('There are item or section missing in the config file')
    #2. ask for option
    _ans = _get_answer(prompt = "fetch completes, shall we Merge or Rebase? (m/R)",
                       help = "Merge will keep the history of changes but mix the local " +\
                              "changes with the merged changes; while Rebase keeps all " +\
                              "local changes together but modifies the change history " +\
                              "and make it hard to trace back. You shall determine which " +\
                              "strategy you would like to use, carefully.")
    _remote_branch = _get_remote_branch()
    if _ans == 'm' or _ans == 'M': #3a. merge
        print("merging from %s ..." % _merge)
        return _invoke([_git_merge(_remote_branch)])
    else: #3b. rebase, which is recommended in many cases
        print("rebasing from %s ..." % _merge)
        return _invoke([_git_rebase()])
    #TODO: there is yet another option, see the better (and more complicated) rebase at
    # http://softwareswirl.blogspot.com/2009/04/truce-in-merge-vs-rebase-war.html

#get a branch list. returns <master branch index>, <branch list>
def _get_branch_list(isremote = False):
    _cmd = _git_branch(lsoption = '-r' if isremote else '')
    _branches = _invoke([_cmd]).split('\n')
    if _branches is None:
        _exit_with_error("seems like there is no branch available...")
    _index = 0
    _current = None
    for line in _branches:
        if '*' in line:
            _current = _index
        _index += 1
    return _current, [x.strip('* ') for x in _branches if x != '']

#based on git branch, to get the current git branch
def _get_current_branch():
    _current_branch = _invoke([_git_status()]).split('\n')[0].split()[-1]
    return _current_branch

#delete a branch
def _delete_branch(branch):
    if branch == _get_current_branch():
        return False, 'current branch %s cannot be deleted' % branch
    _cmd = _git_branch(del_branch = branch)
    _tmp = _invoke([_cmd])
    if _tmp.startswith('Deleted'):
        return True, _tmp
    elif 'is not fully merged' in _tmp: #check if we should try with -D
        _ans = _get_answer(prompt = "%s is not fully merged. Delete it anyway? [y/N]" % branch,
                           help = "it is likely you have changes in the branch.\n" +
                                  "you can force deleting the branch, or quit.")
        if _ans == 'y' or _ans == 'Y':
            return True, _invoke([_git_branch(force_del_branch = branch)])
        else:
            return False, 'branch %s is not deleted' % branch
    else: # what else is missing?
        _exit_with_error(_tmp)

#my way to figure out if a branch exist, returns False when a hash is given
def _if_branch_exist(branch):
    _tmp = _invoke([_git_showref(branch = branch)])
    return _tmp is not None

#-------------------config helppers
#set the config for a new branch
def _set_branch_config(branch_from):
    #check if the config is already there
    _cur_branch = _get_current_branch()
    _read_remote = _get_local('branch.%s.remote' % _cur_branch)
    _read_merge = _get_local('branch.%s.merge' % _cur_branch)
    if _read_merge is '' or _read_remote is '':
        #read the values from the parent branch
        _parent_remote = _get_local('branch.%s.remote' % branch_from)
        _parent_merge = _get_local('branch.%s.merge' % branch_from)
        #set the values of the current branch
        _set_local('branch.%s.remote' % _cur_branch, _parent_remote)
        _set_local('branch.%s.merge' % _cur_branch, _parent_merge)

#get the url of the corresponding remote repository
def _get_remote_url():
    _remote = _get_local('branch.%s.remote' % _get_current_branch())
    if _remote is None:
        raise ConfigItemMissing
    _url = _get_local('remote.%s.url' % _remote)
    return _url

#based on git config, get the local path in the repository where remote branch is stored.
def _get_remote_branch():
    #1. get the current branch
    _current_branch = _get_current_branch()
    #2. read the remote and merge value from the current branch section
    _remote = _get_local('branch.%s.remote' % _current_branch)
    _merge = _get_local('branch.%s.merge' % _current_branch)
    if _remote is None or _merge is None:
        raise ConfigItemMissing
    #3. check if the remote value references any remote section, e.g. origin
    try:
        _r_refspec, _l_refspec = _get_remote_refspec(_remote)
    except ValueError:
        #3.a this branch doesn't reference any remote section,
        #in this case the merge value is the local path to the copy of remote branch
        return _merge
    #4. now that the _l_refspec contains most part of the path,
    #get the remote branch name from the merge value
    if _l_refspec.endswith('*'):
        _path_to_remote = _l_refspec[:-1] + _merge.split('/')[-1]
    else:
        _path_to_remote = _l_refspec
    return _path_to_remote

#get the remote refspec and the local refspec
def _get_remote_refspec(name):
    _tmp = _get_local('remote.%s.fetch' % name)
    if _tmp is None:
        raise ValueError
    _remote, _local = _tmp.split(':')
    #in case there is no * in _remote or _local.
    _remote = _remote.strip('+')
    return _remote, _local

def _push_to_remote():
    remote = _get_local('branch.%s.remote' % _get_current_branch())
    _cmd = _git_push(branch = _get_current_branch(), remote = remote)
    #TODO: need to update the local config file (perhaps supporting multiple branches to push?)
    #TODO: there is a bug when i try to push to github, fix it~
    return _invoke([_cmd])

#command to get local git config value
def _get_local(section):
    _tmp = _invoke([_git_config(config = 'local', section = section)])
    return None if _tmp is None else _tmp[:-1]

def _set_local(section, value):
    _tmp = _invoke([_git_config(config = 'local', section = section, value = value)])

#command to get global git config value
def _get_global(section):
    _tmp = _invoke([_git_config(config = 'global', section = section)])
    return None if _tmp is None else _tmp[:-1]

#command to set global git config value
def _set_global(section, value):
    _tmp = _invoke([_git_config(config = 'global', section = section, value = value)])

#-------------------version helppers
#prompt the user a list of versions and ask for a selected version
def _select_version(since = '7', until = '0'):
    _group_size = since
    while True:
        print(GITInfo(srv = '', param = ['gif', since, until]))
        _ans = _get_answer(help = 'Type:\n' +
                                  '    ID of the version you want, or\n' +
                                  '    Enter directly for more versions, or\n' +
                                  '    ["more" ID] for further details of the version')
        if _ans.startswith('more'):
            print(_invoke([_git_log(version = _ans.split()[-1], num = 1)]))
            raw_input('Any key to continue...')
        elif '' == _ans:
            until = since
            since += _group_size
        else:
            return _ans
        continue

#get file differences between two versions
def _get_version_change(with_previous_version = False):
    if with_previous_version is True: #obtain the current and its previous version
        _current_version, _base_version = _get_versions(2)
    else: #get the versions given by the user
        print("[+] Select the" + color['red'] + " initial " + _end_ +
                "version that your changes are based on")
        _base_version = _select_version(since = 4)
        print("[+] Select the" + color['red'] + " new " + _end_ +
                "version that your changes are based on")
        _current_version = _select_version(since = 4)
    _version_str = _base_version + '..' + _current_version
    _file_list = _invoke([_git_diff(selection = _version_str, name_only = True)]) #list all changed files
    print(_file_list)
    _tmp = _get_answer(prompt = 'Are the files that you changed? [y/N]', help = '')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _version_str

#get the current version string
def _get_versions(num):
    return _invoke([_git_log(num = num, format = '%h')]).split('\n')[:-1]

#check if a version exists
def _if_ver_exist(ver):
    _tmp = _invoke([_git_revparse(version = ver)])
    return not re.search('unknown revision', _tmp)

#-------------------path helppers
#get the root path of the current repository
def _root_path():
    _tmp = _invoke([_git_revparse(param = '--show-toplevel')])
    return None if 'Not a git repository' in _tmp else _tmp

#check if we are at a git repository
def _check_git_path():
    if _root_path() is None:
        _exit_with_error("It seems you are not in a git repository...")

#-------------------source helppers
#get the source list length
def _get_source_list_len():
    _len = _get_global('sourcelist.length')
    if _len is None:
        return 0
    return int(_len)

#read the remembered source list
def _get_source_list():
    _list = list()
    for i in range(_get_source_list_len()):
        _tmp = _get_global('sourcelist.item%d' %(i + 1))
        if _tmp is None:
            raise ConfigItemMissing
        _list.append(_tmp)
    return _list

#add a new source into the source list
def _add_to_source_list(item):
    _len = _get_source_list_len()
    _set_global('sourcelist.item%d' % (_len + 1), item)
    _set_global('sourcelist.length', str(_len + 1))

def _delete_source(source):
    pass

#-------------------file helppers
#get changed but not yet commited files
def _get_changed_uncommited_file_list():
    return _invoke([_git_diff(name_only = True)])

def _number_of_changed_files(_versions = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = _invoke([_git_diff(selection = _versions if _versions else _remote_branch, name_only = True)])
    return len(_tmp.split('\n')) - 1

#return list of changed files and a list of untracked files from the output of 'git status -s'
def _get_changed_files(str):
    _changed_files, _untracked_files = [], []
    if str is not None:
        _changed_pattern = '^[_MDACU]{1,2}' #modifed/deleted/added/copied/unmerged files
        _untracked_pattern = '^\?\?.*' #untracked files
        _file_list = str.split('\n')[:-1]
        for x in _file_list:
            _changed_files += [x] if re.search(_changed_pattern, x) else []
            _untracked_files += [x] if re.search(_untracked_pattern, x) else []
    return _changed_files, _untracked_files

#return the number of changed but not commited files
def _num_uncommited_files():
    _tmp = _invoke([_git_status(param = '-s -uno')])
    _tmp = _tmp.split('\n') if _tmp else []
    return len(_tmp)

#revert a file given in a file item
def _revert_file_item(item):
    _file = item[item.rfind(' ') + 1:] #get the real file name
    if re.search('^_[MD]', item):    #not updated
        _invoke([_git_checkout(target = _file)])
    elif re.search('^[MARCD]_', item): #index and worktree are the same, need to reset first
        _invoke([_git_reset(file = _file)])
        _invoke([_git_checkout(target = _file)])
    elif item.strip().startswith('??'): #the file is out of version control
        _invoke(['rm ' + _file])
    else:
        _exit_with_error('oops, some exceptions occur')
    return True, '%s reverted' % _file
    #TODO: what to do if file is commited, but need to delete from a diff list
    #   this means we need to copy a specified version to overwrite

def _remove_link_file(x):
    _fullpath = sys.argv[0]
    _dir = _fullpath[:_fullpath.rfind('/') + 1]
    _invoke(['rm %s' % (_dir + x)])

#-------------------GIT DIRECT CALL FUNCTIONS-------------------
#These are git function wrappers

def _git_diff(selection = '', name_only = True):
    return 'git diff %s %s' % (selection, '--name-only' if name_only else '')

def _git_log(version = '', num = 0, format = '', param = ''):
    return 'git log %(num)s %(version)s %(format)s %(other)s' %\
          {'num': ('-%d' % num) if num > 0 else '',
           'version': version if version else '',
           'format': ("--format='%s'" % format) if format else '',
           'other': param if param else ''}

def _git_patch(selection, patch_file = '/tmp/backup.patch'):
    _param = selection
    _param += (' > %s' % patch_file) if patch_file else ''
    return 'git format-patch -k --stdout %s' % _param

def _git_clone(param):
    return 'git clone ' + param

def _git_fetch(src = '', dst = ''):
    _param = ('%(source)s:%(local)s' % {'source':src, 'local':dst})\
             if src and dst else ''
    return 'git fetch origin %s' % _param

def _git_checkout(target = '', new_branch = '', track = ''):
    _param = target
    _param += (' -b %s' % new_branch) if new_branch else ''
    _param += (' -t %s' % track) if track else ''
    return 'git checkout %s' % _param

def _git_merge(param = ''):
    return 'git merge %s' % param

def _git_mergetool(param = ''):
    return 'git mergetool %s' % param

def _git_branch(lsoption = None, del_branch = '', force_del_branch = '',
                branch = '', contains = ''):
    if lsoption:
        return 'git branch -l %s' % lsoption
    if del_branch:
        return 'git branch -d %s' % del_branch
    if force_del_branch:
        return 'git branch -D %s' % force_del_branch
    if contains:
        return 'git branch --contains %s' % contains
    return 'git branch %s' % branch

def _git_push(branch, remote):
    return 'git push %s %s' % (remote, branch)

def _git_rebase(param = ''):
    return 'git rebase %s' % param

def _git_status(param = ''):
    return 'git status %s' % param

def _git_showref(branch = ''):
    return 'git show-ref -s %s' % branch

def _git_config(config = '', section = '', value = ''):
    return 'git config --local %s %s' %(section, value) if config == 'local'\
      else 'git config --global %s %s' %(section, value)

def _git_revparse(version = '', param = ''):
    return 'git rev-parse %s %s' % (version, param)

def _git_reset(file):
    return 'git reset %s' % file

#a list of services provided to the user, via symbolic links
SERVICES = [ 'ggt',
             'gpt',
             'gst',
             'gcf',
             ['gst' + x for x in allperm('dr')], #combination of 'd', 'r'
             ['gst' + x for x in allperm('br')], #combination of 'b', 'r'
             'gif', 'gift', 'gifg',
             'gbu',
             'gmg',
             'gbr',
             ['gbr' + x for x in allperm('rt')], #combination of 'r', 't'
             'gdi',
             [ 'gdi' + x for x in allperm('rvf')], # combination of 'r','v','f'
             [ 'gdi' + x for x in allperm('1rvf')], # combination of 'r','v','f', '1'
             [ 'gdi' + x for x in allperm('2rvf')], # combination of 'r','v','f', '2'
             'ghelp' ]

CALL_TABLE = { 'gst': GITStatus,
               'gbr': GITBranch,
               'gif': GITInfo,
               'gbu': GITBackup,
               'gdi': GITDiff,
               'gmg': GITMerge,
               'gcf': GITConfig,
               'ggt': GITGet,
               'gpt': GITPut }

if __name__ == '__main__':
    """
    the main function
    this tool works like busybox: all the symbolic links to the same file.
    depending on what command name is invoked, we provide corresponding services.
    """
    _invoke(['export','LANG=en_US.UTF-8'])
    #get the service requested by the user
    parser = OptionParser()
    service = parser.get_prog_name()
    #a major service will always be a 3-character key word
    if service == 'ghelp':
        try:
            print(CALL_TABLE[sys.argv[1][:3]].__doc__)
        except Exception:
            print(__doc__)
    else:
        if len(sys.argv) == 2 and sys.argv[1] == '?':
            print(CALL_TABLE[service[:3]].__doc__)
            _exit()
        try:
            result = CALL_TABLE[service[:3]](service[3:], sys.argv)
            print(result)
        except KeyError: #if no available service is found, try to install git-tool
            GITSetup(sys.argv)
