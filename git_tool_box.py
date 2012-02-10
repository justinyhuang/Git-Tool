#!/usr/bin/python -W ignore::DeprecationWarning
"""
Git-Tool - a utility set for easier use of git

Available services:
   gif: Git InFo, shows basic information of the current version
   gst: Git STatus, list modified/added/removed files between versions/branches
   gbr: Git Switch, switch/create to a branch/tag, remotely or locally
   gdi: Git DIff, compare file/s between versions/branches
   ggt: Git GeT, to get a copy of the target repository
   ghelp: help info for GITUtil
Proposed services:
   gfl: Git File, to fetch a file from a version
Dependencies (please install):
   git: Git-Tool is a wrapper of git
   graphviz and qiv: Git-Tool needs both to show graphical version tree via gifg
"""
import os
import re
import sys
import subprocess
import git
import pdb
from optparse import OptionParser

"""
TODO: redesign the services into: gsv, gld, gdi, gst, gcf, gls
TODO: check files in /usr/lib/git-core in workstation and see how to enable write permission when doing vimdiff
TODO: add remove resource and remote-branch feature
TODO: the file is growing into a monster, divide it into different library files
TODO: add the path of git-tool bin directory to PATH and the path of git-tool python files to PYTHONPATH, in gitsetup
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

def GITSave(srv = '', param = ''):
    """ gsv
        To 'save' your changes. A 'save' could be:
            * a git commit - save to local repository
              When no parameter is given and there are changed files to commit,
              gsv will perform a git commit.

            * a git push - save to remote repository
              When no parameter is given and there is no changed files to commit,
              gsv will perform a git push.

            * a git format-patch - save to a patch file
              With 'gsv <hash1>..<hash2> <filename>' gsv will generate a patch into
              the patch file with the given name.
              With 'gsv <filename>' gsv will allow the user to pick two versions and
              generate the patch file based on user's selection.
    """
    _current_branch = _get_current_branch()
    if len(param) > 1: #user ask for generating a patch
        if len(param) == 3: #both hash string and the file name is given
            _version_str, _patch_file = param[1], param[2]
        else: #only file name is given, help him to pick two hashes
            _patch_file = param[1]
            _file_list, _version_str = _get_version_change()
        _tmp = _invoke([git.patch(selection = _version_str, patch_file = _patch_file)])
        _ans = _get_answer(prompt = 'where to store %s ?' % _patch_file)
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):#directory doesn't exist, try to make one
            os.makedirs(_target_dir)
        _invoke(['mv %s %s' % (_patch_file, _target_dir)])
        return '\npatch saved to %s/%s' % (_target_dir, _patch_file)
    else: #do a push or a commit
        if _get_uncommited_changed_files(): #there are changed files to commit
            _ans=_get_answer(prompt = 'Back up in ' +\
                             color['red'] + _current_branch + _end_ + ' ? [Y/n]')
            if _ans == 'n' or _ans == 'N':
                if _switch_branch() == '': #user decides to quit without commiting
                    _exit()
            _msg = ''
            while _msg is '':
                _msg = _get_answer(prompt = 'Any comment? [empty comment is not allowed]')
            _msg = '"' + _msg + '"'
            _invoke([git.commit(' -a -m %s' % _msg)])
            return "Done"
        else: # there is no changed files, try a push
            return _push_to_remote()

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
        if _num_args is not 2:
            _exit_with_error("missing parameters...")
        _name = param[1]
        _cmd = git.checkout()
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
        to set a config value, do:
            gcf <local/global> <section> <value>
    """
    if len(param) == 4: #set config value
        if param[1] == 'local': #set local value
            _set_local(section = param[2], value = param[3])
        elif param[1] == 'global': #set global value
            _set_global(section = param[2], value = param[3])
    #local settings
    if _root_path():
        _current_branch = _get_current_branch()
        _current_branch_remote = _get_local('branch.%s.remote' % _current_branch)
        _current_branch_merge = _get_local('branch.%s.merge' % _current_branch)
        _remote_branch = _get_remote_branch()
        _repo_url = _get_remote_url()
    else:
        _current_branch = _current_branch_remote = \
        _current_branch_merge = _remote_branch = None
    #global settings
    _email = _get_global('user.email')
    _username = _get_global('user.name')
    _first_diff_tool = _get_global('difftool.first')
    _second_diff_tool = _get_global('difftool.second')
    _third_diff_tool = _get_global('difftool.third')
    #make up the output
    _ret = ""
    _ret += "current branch is %s\n" % _current_branch
    _ret += "remote branch is %s\n" % _remote_branch
    _ret += "remote repository url is %s\n" %  _repo_url
    _ret += color['yellow'] + "---Local Settings---\n" + _end_
    _ret += "branch.%s.remote: %s\n" % (_current_branch, _current_branch_remote)
    _ret += "branch.%s.merge: %s\n" % (_current_branch, _current_branch_merge)
    _ret += color['yellow'] + "---Global Settings---\n" + _end_
    _ret += "user.name: %s\n" % _username
    _ret += "user.email: %s\n" % _email
    _ret += "difftool.first: %s\n" % _first_diff_tool
    _ret += "difftool.second: %s\n" % _second_diff_tool
    _ret += "difftool.third: %s\n" % _third_diff_tool
    return _ret

def GITDiff(srv, param):
    """ gdi
        gdi(r)(v)(f)(2/3): show the files' differences in many ways
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
                with (2/3) to diff with a difftool that is configured when you setup
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
    if '2' in srv:
        _difftool = _get_global('difftool.second')
    elif '3' in srv:
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
    _num = _number_of_changed_files(_versions, _remote_branch, _file)
    if _num > 7: # i guess 7 is a good limit
        _ans = _get_answer(prompt = 'are you sure to diff about '
                                   + color['red'] + '%d' % _num + _end_
                                   + ' files?[y/N]')
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
        _current_branch = _get_current_branch()
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
        else: #current path has git data, if not update then we do git fetch from a ref
            _source_type = 'ref'
    else: #current path has no git data, do git clone from a repo
        _source_type = 'repo'
    #2. get the source
    _source_list = _get_source_list(_source_type)
    for r, _index in zip(_source_list, range(len(_source_list))):
        print("%d  -  %s" % (_index, r))
    _tmp = _get_answer(prompt = 'Pick a source from above',
                       help = 'select the source by the index number, if available.\n' +
                              'or type in the repository/branch')
    #TODO: check if the local config merge and remote values are correct
    if re.match('^\d+$', _tmp) is not None:
        _ifnew = False #seems like a know source is selected
        _source = _source_list[int(_tmp)]
    else:
        _ifnew = True #new source specified by the user
        _source = _tmp
    #3. fetch or clone the source
    if _source_type == 'repo':
        #TODO:need to consider if the user like to update but accidentally comes here
        _tmp = _invoke([git.clone(_source)])
    else: #a fetch request
        if _root_path() is None:
            return "Seem like you are trying to fetch a branch, but in no git reporitory" +\
                   "You might consider issue the command in a repository..."
        #is there a branch tracking the local repo?
        _branch_name = _source[ _source.rfind('/') + 1: ]
        if _find_local_refs(_source): #the ref has been fetched to local repository
            _tmp = _make_branch_linked_to_ref(_branch_name, _source)
        else: #there is no branch currently tracking the ref
            _local_ref = _source.replace('refs/', 'refs/remotes/', 1)
            _repo = _get_local(section = 'branch.%s.remote' % _current_branch)
            _cmd = git.fetch(repo = _repo, src = _source, dst = _local_ref)
            _tmp = _invoke([_cmd])
            #make a branch tracking the ref
            _tmp += _make_branch_linked_to_ref(_branch_name, _source)
    #4.update the global config file with the checked out source path
    if _ifnew is True:
        _add_to_source_list(_source_type, _source)
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
                    *NOTE*: graphviz and qiv is required to enable the 'g' option
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
            _range = 'HEAD' + _num * '^' + '...HEAD' + ' --ancestry-path'
        #_format = '"%h" [label="<f0> %h|{<f1> %an|<f2> %cd}"]\n"%h":f0 -> {%p}'
        _format = """"%h" [label=<<TABLE>
                                <TR><TD ROWSPAN="2" PORT="f0" BGCOLOR="bisque">%h</TD>
                                    <TD>%an</TD></TR>
                                <TR><TD>%cd</TD></TR>
                                </TABLE>>]\n"%h":f0 -> {%p}
                  """
    else:
        if _num != 0:
            _range = '-%d' % _num
        else:
            _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                    {'num_of_log': abs(_since - _until) + 1,
                     'num_to_skip': min(_since, _until) - 1}
        _format='___%nRev:       %h%nDate:     %cd%nComment:  %s'
    if _if_show_tag is True: #show the tag info
        print("this will take a while...")
        _cmd = git.log(version = _range, format = '%ad|%h|%s|%d',
                        param = '--abbrev-commit --date=short')
        _logs = _split(_invoke([_cmd]), '\n')
        _result = ''
        for _line in _logs:
            [_date, _hash, _comment, _tmp] = _line.split('|') if _line else ['', '', '', '']
            _tmp = _split(_tmp.strip(' ()'), ', ')
            _branch = _get_branches_with_commit(_hash)
            _container_tags = _invoke(["git tag --contains %s" % _hash])
            _container_tags = _split(_container_tags, '\n')
            if _container_tags:
                #the hash has tags attached, get the tags on this specific version
                _tags = list(set(_tmp) & set(_container_tags))
                _result += '___\n'
                _result += 'Rev: %s\nDate: %s\nBranch: %s\nComment: %s\nTags: %s\n' %\
                           (_hash, _date, _branch, _comment, _tags)
            else: #a version without any tag
                _result += '___\n'
                _result += 'Rev: %s\nDate: %s\nBranch: %s\nComment: %s\n' %\
                           (_hash, _date, _branch, _comment)
        return _result
    else:
        _result = _invoke([git.log(version = _range, format = _format,
                                    param = '--date=short')])
    if _if_graphic is True:
        #link versions with arrows
        _result = re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', _build_merge_arrows, _result)
        _result = 'digraph G{\nnode [shape=plaintext]\n'\
                + _result\
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
    _cmd = git.diff(selection = _compare_str, name_only = True) if _compare_str\
            else git.status(param = '-s')
    if _isdir is True: #only show the touched files in the current directory
        _cmd += ' -- ' + os.getcwd()
    _tmp = _invoke([_cmd])
    _status = _translate_status_code(_cmd, _tmp)
    _final_str = '' # prepare for a prettified outcome
    if _compare_str:#show changed files between two commits
        if '..' in _compare_str: #two compare candidates are given
            _comp2, _comp1 = _split(_compare_str, '..')
        else:
            if _if_branch_exist(_compare_str) is True: #only one candidate given, which is a branch
                _comp2, _comp1 = _compare_str, _get_current_branch()
            elif 'unknown revision' in _status: #something wrong with the given candidate
                _exit_with_error('unknown version/branch, please check')
            else:#assume this is comparison between versions
                _comp2, _comp1 = _compare_str, _get_versions(1)[0]
            _changed_not_commited_sign = 'MODIFIED ' if _get_uncommited_changed_files()\
                                              else ''
            _comp1 = _changed_not_commited_sign + _comp1
        if _status is None or _status.strip(' ') is None:
            _status = '' #there is no changes found
            _changes = 0
        else:
            _changes = len(_split(_status, '\n')) - 1
        _changed = _split(_status, '\n')[:-1]
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
    def __init__(self, list, name = 'item'):
        self._list = list     #all the data will be stored in a list
        self.name = name
        self.help = "You can: \
          \n   Type the index of the %s or,\
          \n   Type the name for a new %s or,\
          \n   Use '/d <item_index>' to delete an %s or,\
          \n   Use '/e' to quit" % (self.name, self.name, self.name)
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
    def __init(self, list):
        super(BranchBall, 'branch', self).__init__(list)
    def delete(self, item_list):
        super(BranchBall, self).delete(item_list, _delete_branch)

class FileBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list):
        super(FileBall, 'file', self).__init__(list)
    def delete(self, item_list):
        super(FileBall, self).delete(item_list, _revert_file_item)

class SourceBall(Ball):
    """
    A ball that holds a list of sources
    """
    def __init(self, list, name = 'source'):
        super(FileBall, self.name, self).__init__(list)
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

def _split(str, sep = None):
    return str.split(sep) if str else []

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
    if 'No help available... ' != help or\
       (ball and ball.help): # show colored prompt if help is available
        _ps = color['lightblue'] + PROMPT_SIGN + _end_
        if ball and ball.help:
            help = ball.help
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
    elif re.search('^\s*\d+\s*', _ans) and ball: #return the selected ball item
        return ball[int(_ans)]
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
    _range = _split(_line, '-')
    for x in range(int(_range[0]), int(_range[1]) + 1):
        _tmp += ' %d ' % x
    return _tmp

#used in re.sub to modify the matching string and link nodes with arrows
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
#to find if a ref has a local storage
def _find_local_refs(ref):
    ref = ref[5:] #skip the 'refs/'
    _current_branch, _branch_list = _get_branch_list(isremote = True)
    for b in _branch_list:
        if ref == b:
            return b
    return None

#merge branch, assuming frombr and tobr are valid branches
def _merge_branch(frombr, tobr):
    _cur = _get_current_branch()
    _invoke([git.checkout(target = tobr)]) #switch to the target branch
    _tmp = _invoke([git.merge(frombr)]) #try auto merge
    if 'Automatic merge failed' in _tmp: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _tmp

#show a lost of local/remote branches and do something
def _switch_branch(isremote = False):
    _curbranch, _branch_list = _get_branch_list(isremote)
    _listball = BranchBall(_branch_list)
    _selected = _get_answer(prefix = '--- Branch List ---', ball = _listball, hl = _curbranch)
    if _selected == '':
        return "" #return if no branch is selected or created
    elif re.search('^\d+$', _selected): #a selected index
        _selected_branch = _listball[int(_selected)]
    else: # probably a new branch name
        _selected_branch = _selected
    _tmp = ''
    for line in _branch_list:
        if line != '' and _selected_branch == _split(line)[-1]:
            if isremote is True:
                _local_branch = _get_answer(prompt = "Give a name for the new local branch:",
                                            help = "if give no name you will be on " +
                                                   color['red'] + "NO " + _end_ +
                                                   "branch and we don't recommend that")
                if '' == _local_branch:
                    return ''
                else:
                    _tmp = _invoke([git.checkout(target = _selected_branch,
                                                  new_branch = _local_branch)])
            else:
                _tmp = _invoke([git.checkout(target = _selected_branch)])
            return _tmp
    #we are here because the selected branch is not in the list
    return _make_branch(_selected_branch)

def _make_branch(branch):
    _previous_branch = _get_current_branch()
    _tmp = _invoke([git.branch(branch = branch)]) #create branch with the name given
    _tmp = _invoke([git.checkout(target = branch)])
    _set_branch_config(branch_from = _previous_branch) #new branch, set the config properly
    _result = 'created and switched to new branch: ' + color['red'] + branch + _end_ + '\n'
    _result += 'config is set based on ' + color['red'] + _previous_branch + _end_
    return _result

#based on the remote and fetch values of the parent, set up the values for the new branch
def _make_branch_linked_to_ref(bname, ref, repo = ''):
    _ref = ref[5:] #skip the 'refs/'
    _remote = _get_local(section = 'branch.%s.remote' % _get_current_branch())
    _repo = repo if repo\
                 else _get_local(section = 'remote.%s.url' % _remote)
    _cmd = git.checkout(target = _ref, new_branch = bname)
    _tmp = _invoke([_cmd])
    _fetch = '+refs/' + _ref + ':refs/remotes/' + _ref
    #set up a new remote section and a new branch section for this new branch
    _set_local(section = 'remote.%s.url' % bname, value = _repo)
    _set_local(section = 'remote.%s.fetch' % bname, value = _fetch)
    _set_local(section = 'branch.%s.remote' % bname, value = bname)
    _set_local(section = 'branch.%s.merge' % bname, value = ref)
    return _tmp

def _get_branches_with_commit(hash):
    _cmd = git.branch(contains = hash)
    return [x.strip(' *') for x in _split(_invoke([_cmd]), '\n') if x]

def _update_local_branch():
    #1. fetch the updates from remote repo
    _current_branch = _get_current_branch()
    _remote = _get_local('branch.%s.remote' % _current_branch)
    _merge = _get_local('branch.%s.merge' % _current_branch)
    if _remote and _merge: #only initiate fetch when the config values are correct
        print("fetching from %s ..." % _remote)
        print(_invoke([git.fetch()]))
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
        return _invoke([git.merge(_remote_branch)])
    else: #3b. rebase, which is recommended in many cases
        print("rebasing from %s ..." % _merge)
        return _invoke([git.rebase()])
    #TODO: there is yet another option, see the better (and more complicated) rebase at
    # http://softwareswirl.blogspot.com/2009/04/truce-in-merge-vs-rebase-war.html

#get a branch list. returns <master branch index>, <branch list>
def _get_branch_list(isremote = False):
    _cmd = git.branch(lsoption = '-r' if isremote else '')
    _branches = _split(_invoke([_cmd]), '\n')
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
    _first_line = _split(_invoke([git.status()]), '\n')[0]
    return _split(_first_line)[-1] #last word of the first line is the branch name

#delete a branch
def _delete_branch(branch):
    if branch == _get_current_branch():
        return False, 'current branch %s cannot be deleted' % branch
    _cmd = git.branch(del_branch = branch)
    _tmp = _invoke([_cmd])
    if _tmp.startswith('Deleted'):
        return True, _tmp
    elif 'is not fully merged' in _tmp: #check if we should try with -D
        _ans = _get_answer(prompt = "%s is not fully merged. Delete it anyway? [y/N]" % branch,
                           help = "it is likely you have changes in the branch.\n" +
                                  "you can force deleting the branch, or quit.")
        if _ans == 'y' or _ans == 'Y':
            return True, _invoke([git.branch(force_del_branch = branch)])
        else:
            return False, 'branch %s is not deleted' % branch
    else: # what else is missing?
        _exit_with_error(_tmp)

#my way to figure out if a branch exist, returns False when a hash is given
def _if_branch_exist(branch):
    _tmp = _invoke([git.showref(branch = branch)])
    return _tmp is not None

#-------------------config helppers
#set the config for a new branch
def _set_branch_config(branch_from):
    #check if the config is already there
    _cur_branch = _get_current_branch()
    _read_remote = _get_local('branch.%s.remote' % _cur_branch)
    _read_merge = _get_local('branch.%s.merge' % _cur_branch)
    if _read_merge is None or _read_remote is None:
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

#set the url of the corresponding remote repository
def _set_remote_url(url):
    _remote = _get_local('branch.%s.remote' % _get_current_branch())
    if _remote is None:
        raise ConfigItemMissing
    _set_local('remote.%s.url' % _remote, url)

#get the remote branch, the merge value in the branch section
def _get_remote_branch():
    #get the name of the corresponding remote branch
    _current_branch = _get_current_branch()
    _remote_branch = _get_local(section = 'branch.%s.merge' % _current_branch)
    return _remote_branch if _remote_branch else ''

#set the remote branch, the merge value in the branch section
def _set_remote_branch(branch):
    _set_local('branch.%s.remote' % _get_current_branch(), branch)

#get the remote refspec and the local refspec
def _get_remote_refspec(name):
    _tmp = _get_local('remote.%s.fetch' % name)
    if _tmp is None:
        raise ValueError
    _remote, _local = _split(_tmp, ':')
    #in case there is no * in _remote or _local.
    _remote = _remote.strip('+')
    return _remote, _local

def _push_to_remote():
    _url = _get_remote_url()
    _ref = _get_remote_branch()
    if _url is None:
        _exit_with_error('config values are missing, you will need to manually fix this issue')
    else:
        _msg = 'push to ' + color['red'] + 'URL' + _end_ + ': ' + _url + '\n' +\
               '        ' + color['red'] + 'REF' + _end_ + ': ' + _ref + '\nOK? [Y/n]'
        _ans = _get_answer(prompt = _msg)
        if _ans == 'n' or _ans == 'N':
            #choose or specify a URL
            _urls = _get_source_list('repo')
            _ball = SourceBall(_urls, 'repo')
            _url = _get_answer(prompt = 'Select a URL to push', ball = _ball)
            if _url not in _urls: #user type in a new item that is not in the ball list
                _add_to_source_list('repo', _url)
            _set_remote_url(_url)
            #choose or specify a REF
            _refs = _get_source_list('ref')
            _ball = SourceBall(_refs, 'ref')
            _ref = _get_answer(prompt = 'Select a REF to push', ball = _ball)
            if _ref not in _refs: #user type in a new item that is not in the ball list
                _add_to_source_list('ref', _ref)
            _set_remote_branch(_ref)
    _cmd = git.push(repo = _url, branch = _get_current_branch(), ref = _ref)
    return _invoke([_cmd])

#command to get local git config value
def _get_local(section):
    _tmp = _invoke([git.config(config = 'local', section = section)])
    return None if _tmp is None else _tmp[:-1]

def _set_local(section, value):
    _tmp = _invoke([git.config(config = 'local', section = section, value = value)])

#command to get global git config value
def _get_global(section):
    _tmp = _invoke([git.config(config = 'global', section = section)])
    return None if _tmp is None else _tmp[:-1]

#command to set global git config value
def _set_global(section, value):
    _tmp = _invoke([git.config(config = 'global', section = section, value = value)])

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
            print(_invoke([git.log(version = _split(_ans)[-1], num = 1)]))
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
    _file_list = _invoke([git.diff(selection = _version_str, name_only = True)]) #list all changed files
    print(_file_list)
    _tmp = _get_answer(prompt = 'Are the files that you changed? [y/N]', help = '')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _version_str

#get the current version string
def _get_versions(num):
    _version_str = _invoke([git.log(num = num, format = '%h')])
    return _split(_version_str, '\n')[:-1] #get rid of the last empty line

#check if a version exists
def _if_ver_exist(ver):
    _tmp = _invoke([git.revparse(version = ver)])
    return not re.search('unknown revision', _tmp)

#-------------------path helppers
#get the root path of the current repository
def _root_path():
    _tmp = _invoke([git.revparse(param = '--show-toplevel')])
    return None if 'Not a git repository' in _tmp else _tmp

#check if we are at a git repository
def _check_git_path():
    if _root_path() is None:
        _exit_with_error("It seems you are not in a git repository...")

#-------------------source helppers
#get the source list length
def _get_source_list_len(source):
    _len = _get_global('sourcelist.%s.length' % source)
    if _len is None:
        return 0
    return int(_len)

#read the remembered source list
def _get_source_list(source):
    _list = list()
    for i in range(_get_source_list_len(source)):
        _tmp = _get_global('sourcelist.%s.item%d' % (source, (i + 1)))
        if _tmp is None:
            raise ConfigItemMissing
        _list.append(_tmp)
    return _list

#add a new source into the source list
def _add_to_source_list(type, item):
    _len = _get_source_list_len(type)
    _set_global('sourcelist.%s.item%d' % (type, (_len + 1)), item)
    _set_global('sourcelist.%s.length' % type, str(_len + 1))

def _delete_source(source):
    pass

#-------------------file helppers
#get changed but not yet commited files
def _get_uncommited_changed_files():
    return _invoke([git.diff(name_only = True)])

def _number_of_changed_files(_versions = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = _invoke([git.diff(selection = _versions if _versions else _remote_branch, name_only = True)])
    return len(_split(_tmp, '\n')) - 1

#return list of changed files and a list of untracked files from the output of 'git status -s'
def _get_changed_files(str):
    _changed_files, _untracked_files = [], []
    if str is not None:
        _changed_pattern = '^[_MDACU]{1,2}' #modifed/deleted/added/copied/unmerged files
        _untracked_pattern = '^\?\?.*' #untracked files
        _file_list = _split(str, '\n')[:-1]
        for x in _file_list:
            _changed_files += [x] if re.search(_changed_pattern, x) else []
            _untracked_files += [x] if re.search(_untracked_pattern, x) else []
    return _changed_files, _untracked_files

#return the number of changed but not commited files
def _num_uncommited_files():
    _tmp = _invoke([git.status(param = '-s -uno')])
    _tmp = _split(_tmp, '\n')
    return len(_tmp)

#revert a file given in a file item
def _revert_file_item(item):
    _file = item[item.rfind(' ') + 1:] #get the real file name
    if re.search('^_[MD]', item):    #not updated
        _invoke([git.checkout(target = _file)])
    elif re.search('^[MARCD]_', item): #index and worktree are the same, need to reset first
        _invoke([git.reset(file = _file)])
        _invoke([git.checkout(target = _file)])
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

#a list of services provided to the user, via symbolic links
SERVICES = [ 'ggt',
             'gst',
             'gcf',
             ['gst' + x for x in allperm('dr')], #combination of 'd', 'r'
             ['gst' + x for x in allperm('br')], #combination of 'b', 'r'
             'gif', 'gift', 'gifg',
             'gsv',
             'gmg',
             'gbr',
             ['gbr' + x for x in allperm('rt')], #combination of 'r', 't'
             'gdi',
             [ 'gdi' + x for x in allperm('rvf')], # combination of 'r','v','f'
             [ 'gdi' + x for x in allperm('2rvf')], # combination of 'r','v','f', '2'
             [ 'gdi' + x for x in allperm('3rvf')], # combination of 'r','v','f', '3'
             'ghelp' ]

CALL_TABLE = { 'gst': GITStatus,
               'gbr': GITBranch,
               'gif': GITInfo,
               'gsv': GITSave,
               'gdi': GITDiff,
               'gmg': GITMerge,
               'gcf': GITConfig,
               'ggt': GITGet}

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
