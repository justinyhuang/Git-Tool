#!/projects/phx/tools/python/bin/python -W ignore::DeprecationWarning
"""
GitBox - a utility set for easier use of git

Available services:
   gst: Git STatus, list modified/added/removed files between versions/branches
   gsw: Git Switch, switch/create to a branch/tag, remotely or locally
   gif: Git InFo, shows basic information of the current version
Proposed services:
   gco: Git ClOne/CheckOut, to get a new sandbox
   gbu: Git BackUp, commit changes in the working copy to local repository
   grs: Git ReStore, go back to a previous backup version
   gpl: Git PulL, pull lastest version from the remote repository
   gsh: Git SHare, to share a branch with others
   gpp: Git Prepare, set up a new sandbox with all your changes inside
        *This is for preparing a clean sandbox to submit for integration
   gfl: Git File, to fetch a file from a version
   gdi: Git DIff, compare file/s between versions/branches
   ghelp: help info for GITUtil
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
TODO: instead of global settings in the python file, we need to build a section
in .git/config file such that git box can store necessary info for the repository
"""

#-------------------GLOBAL SETTINGS-------------------
# Edit the following settings to make GITTool fits your need
DEBUG = False
COLOR = True
#PROMPT_SIGN = unichr(0x263B)
PROMPT_SIGN = ':> '

#the services provided by the git tool box, used for creating the links
## {{{ http://code.activestate.com/recipes/577842/ (r1)
def allperm(inputstr):
    for i in range(len(inputstr)):
        yield(inputstr[i])
        for s in allperm(inputstr[:i] + inputstr[i+1:]):
            yield(inputstr[i] + s)
## end of http://code.activestate.com/recipes/577842/ }}}

SERVICES = [
               #'gco',
               'gst',
               ['gst' + x for x in allperm('drvb')], #combination of 'd', 'r', 'v', 'b'
               'gif',
               ['gif' + x for x in allperm('t')],
               'gbu',
               #'gsh',
               #['gsh' + x for x in allperm('i')],
               #'grs',
               'gsw',
               ['gsw' + x for x in allperm('rt')], #combination of 'r', 't'
               #'gpl',
               #'gfl',
               #'gdi',
               #[ 'gdi' + x for x in allperm('urvf')], # combination of 'u','r','v','f'
               #'gpp',
               'ghelp'
           ]

color = dict()
if COLOR:
    color['red'] = '\033[01;31m'
    color['green'] = '\033[01;32m'
    color['yellow'] = '\033[01;33m'
    color['blue'] = '\033[01;34m'
    color['magenta'] = '\033[01;35m'
    color['lightblue'] = '\033[01;36m'
    color['white'] = '\033[01;37m'
    color['gray'] = '\033[01;30m'
    color['end'] = '\033[00m'
else:
    color['red'] = ''
    color['green'] = ''
    color['yellow'] = ''
    color['blue'] = ''
    color['magenta'] = ''
    color['lightblue'] = ''
    color['white'] = ''
    color['gray'] = ''
    color['end'] = ''

class GITError(Exception):
    """base class of all GitTool error exceptions"""

class ConfigItemMissing(GITError):
    """The item/section in the git config file does not exist"""

class Ball(object):
    """
    A ball is a carrier that holds the output of the previous function, and
    goes to the next function call providing necessary inputs.
    """
    def __init__(self, **param):
        """
        init the ball
        """
        #holds the processed file list, if there is any
        self._file_list = None
        #holds the version string, if there is any
        self._version_str = None
        #for any future extended functionalities
        self._param = param
    def get_file_list(list):
        self._file_list = list


def GITStatus(srv, param):
    """
    gst
    show the status (what have been changed) of a working copy or a version
    gst(rvd): without (rvd), is equal to 'git status', showing the changed files
              between working copy and the HEAD of current local branch.

              with (r), show the changed files between the current branch (in
              local repository) with that of its remote branch (REMOTE_BRANCH
              by default)

              with (v), the tool will show you a list of files that are changed
              across different versions.
              you need to provide a parameter to specify the version(s).
              something like "<version sha1>..<version sha2>", or
                             "<version sha>", or other git valid version strings
              will work.

              with (d), the tool will only show you a list of changed files in the
              current directory

              possible combinations are: r, v, d, rd, vd
    """
    _check_git_path()
    _isbranch = ('b' in srv)
    _isremote = ('r' in srv)
    _isversion = ('v' in srv)
    _isdir = ('d' in srv)
    _version_str = param[1] if _isversion else None
    _branch_name = param[1] if _isbranch else None

    #initialize the ball
    _ball = Ball()

    if _isversion is True:
        #show diff between two given versions
        _cmd = status_version_cmd(_version_str)
    elif _isbranch is True or _isremote is True:
        #show diff between two branches's HEAD
        #the branch to be compared with could be local or remote
        _current_branch = _get_current_branch()
        if _branch_name is None:
            #we are now comparing with the merge branch
            try:
                _branch_name = _get_remote_branch()
            except ConfigItemMissing:
                print(_make_config_item_missing_msg())
                _exit_with_error()
        else:
            #we have a local branch, start comparing
            pass
        _cmd = status_branch_cmd(_branch_name)
    else:
        #we are asked to do a normal 'git status'
        _cmd = status_cmd(param)

    if _isdir is True:
        #only show the touched files in the current directory
        _cmd += ' -- ' + os.getcwd()

    #eventually invoke the command
    _tmp_result = _envoke([_cmd])

    #prettify the outcome
    _final_str = ''
    if _isversion or _isbranch or _isremote:
        if _isremote is True or _isbranch is True:
            _comp2, _comp1 = _branch_name, _current_branch
        elif _isversion is True:
            _comp2, _comp1 = _version_str.split('..')
        else:
            _comp2 = _comp1 = 'UNKNOWN'

        if _tmp_result is None or _tmp_result.strip(' ') is None:
            _tmp_result = ''
            _changes = 0
        else:
            _changes = len(_tmp_result.split('\n')) - 1

        _total = 'Different files: ' + color['red'] + str(_changes) + color['end']
        _final_str += _make_msg_bar(_make_status_header(_comp1, _comp2))
        _final_str += _tmp_result
        _final_str += _make_msg_bar(_total)
    else:
        _final_str = _tmp_result

    return _final_str

def GITSwitch(srv, param):
    """ gsw
        switch to another branch, remote or local or newly created.
        gsw(rt): to switch to another branch, do a 'gsw <branch-name>' or,
                    do a 'gsw', and then type in a branch name in the displyed list or,
                    do a 'gsw', and type in the name of a new branch, to create the new branch and
                                switch to the branch.
                 with (r) do a 'gswr <branch-name> you will be checking/switching to a remote branch or,
                    do a 'gswr', and then type in a branch name in the displyed list
                 with (t), you will switch to a branch has the tag on
    """
    _check_git_path()
    _num_args = len(param)
    _hasbranch = (_num_args == 2)
    _hastag = False
    _isremote = ('r' in srv)
    _bname = _tname = ''

    if _hasbranch is _hastag is False:
        #no hint about what the user is trying to do
        #give a list of local/remote branch to select
        return _switch_branch(_isremote)
    else:
        #either branch or tag is given
        try:
            _cmd = 'git checkout'
            if ( _hastag is True):
                #checkout a branch with the given tag
                _branchname = _get_answer(prompt = 'Enter a new branch name to keep the remote branch data',
                                          help = 'This command is for getting remote version, \n\
                                                  therefore it is required to create a branch here')
                _tname = args[1]
                if _branchname.strip() == '':
                    print("A branch name is required, the 'nobranch' is not recommended")
                    return
                else:
                    _cmd += '%(tag)s -b %(newbranch)s' %\
                            {'tag': _tname,
                             'newbranch': _branchname}
            return _envoke([_cmd])
        except IndexError:
            return "ERROR: the command and the argument don't match."

def GITInfo(srv, param):
    """gif
       to display the version/branch/tag info
       gif(t): gif <number of versions to display>
                   when no parameter is given, only the current version info will be shown
               gif <since generation> <until generation>
                   display all the versions between the since_generation and the until_generation
                   e.g 'gif 3 0' will show you the versions from HEAD to the 3rd generation grand-parent of HEAD
                       'gif 7 4' will show you the versions from the 4th generation grand-parent of HEAD to
                       the 7th generation grand-parent of HEAD
                   * the tool is smart enough even you put the since and until version in the other order =)
               with (t) you will get the tag info if there is any.
                   Note that fetching tag info would take a bit more time
    """
    _check_git_path()
    _format='___%nID:       %h%nDate:     %cd%nComment:  %s'
    _if_show_tag = ('t' in srv)
    _since = _until = _num = 0
    if len(param) == 3:
        #start and end of a version segment is given.
        _since = int(param[1])
        _until = int(param[2])
    elif len(param) == 2:
        #the number of versions is given.
        _num = int(param[1])
    else:
        #default, show the latest version info
        _num = 1

    if _num != 0:
        _range = '-%(num)s' % {'num': str(_num)}
    else:
        _range = "-%(num_of_log)s --skip=%(num_to_skip)s" %\
                {'num_of_log': str(abs(_since - _until)),
                 'num_to_skip': str(min(_since, _until))}
    _result = _envoke(["git log %(range)s --format='%(format)s'" %
                    {'range': _range,
                     'format': _format}
                   ])

    _result_list = _result.split('___\n')[1:]

    if _if_show_tag is True:
        #will show the tag info
        _cmd = "git log %(range)s " % {'range': _range}
        _cmd += "--pretty=format:'%ad|%h|%d' --abbrev-commit --date=short"
        _logs = _envoke([_cmd]).split('\n')

        _branch = _get_current_branch()
        _result = ''
        for _line in _logs:
            [_date, _hash, _tmp] = _line.split('|')
            _tmp = _tmp.strip(' ()').split(', ')
            if _if_show_tag is True:
                try:
                    _container_tags = _envoke(["git tag --contains %(hash)s" %
                                               {'hash':_hash}
                                              ]).split('\n')
                    #get the tags on this specific version
                    _tags = list(set(_tmp) & set(_container_tags))
                    _result += '___\n'
                    _result += 'Branch: %(branch)s\nDate: %(date)s\nRev: %(rev)s\nTags: %(tags)s\n' %\
                               {'branch':_branch,
                                'date': _date,
                                'rev':_hash,
                                'tags':_tags}
                    _result += _result
                except AttributeError:
                    #we might just see a version without any tag
                    _result += '___\n'
                    _result += 'Branch: %(branch)s\nDate: %(date)s\nRev: %(rev)s\n' %\
                               {'branch':_branch,
                                'date': _date,
                                'rev':_hash}
                    _result += _result
            else:
                #getting tags takes too much time, skip it by default
                _result += '___\n'
                _result += 'Branch: %(branch)s\nDate: %(date)s\nRev: %(rev)s\n' %\
                           {'branch':_branch,
                            'date': _date,
                            'rev':_hash}
                _result += _result
    return _result

def GITBackup(srv, param):
    """ gbu
        commit/backup the changes to the local repository
             Changes can be back-up to the current branch, or another branch you
             select from the give list
             you can also generate a patch of your changes to store the patch
             somewhere else.
    """
    _current_branch = _get_current_branch()
    if _current_branch == 'master':
        ans=_get_answer(prompt = 'Are you sure to back up in ' +\
                               color['red'] + 'master ' + color['end'] + 'branch? [y/N]',
                        help = 'In most cases what you need is to back up to\
                                your own branch in order to merge or further\
                                branch out later. So are you sure?')
        if ans is not 'y' and ans is not 'Y':
            if _switch_branch() == False:
                _exit()
    #elif line == '* (no branch)':
    #    # we are on 'no' branch
    #    if _switch_branch(_branches) == False:
    #        return
    #    break
    else:
        #this is a normal branch
        ans = _get_answer(prompt = 'back up in ' +
                          color['red'] + _current_branch + color['end'] + '? [Y/n]')
        if ans == 'n' or ans == 'N':
            if _switch_branch() == False:
                _exit()

    msg = _get_answer(prompt = 'Any comment? [enter for empty comment]')
    msg = '"' + msg + '"'
    result = _envoke(['git commit -a -m %s'%msg])
    print(result)

    #to allow local backup in one's home directory
    _ans = _get_answer(prompt = 'Backup the changes to a patch also? [y/N]',
                       help = "say y or Y if you like to make a patch file for the change")
    if _ans == 'y' or _ans == 'Y':
        _file_list, _version_str = _get_version_range(with_previous_version = True)
        if _file_list is None or _version_str is None:
            _exit_with_error();
        _tmp = _envoke([patch_cmd(_version_str)])
        _ans = _get_answer(prompt = 'where to store the patch file?')
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):
            ans=_get_answer(prompt = 'The path doesn\'t seem to exist. Try to make the directory? [Y/n]',
                            help = 'I will try my best to create the directory/ies.\
                                    \nWould you like me to do that for you?')
            if ans == 'n' or ans == 'N':
                _exit()
            else:
                os.makedirs(_target_dir)
        _envoke(['mv /tmp/backup.patch ' + _target_dir +
                 '/backup.%(verstr)s.patch ' % {'verstr': _version_str}])
        return "back up has been saved as " + _target_dir +\
              '/backup.%(verstr)s.patch ' % {'verstr': _version_str}
    _exit()

#setup the environment for first use
def GITSetup():
    ans=_get_answer(prompt = 'Would you like to setup GITTool? [y/N]',
                    help = 'This will simply create a bunch of symbol links for you.\
                            \nSo would you like to setup GITTool? [y/N]')
    if 'y' == ans or 'Y' == ans:
       print("Please specify where you would like to put the GITTool facilities")
       print("[eg. '~/bin/GTool', '/tools']")
       print("\nMake sure the path is in your PATH variable")
       ans = _get_answer(help = "The GitUtilTool works based on" +
                                color['red'] + " A LOT OF " + color['end'] +
                                "small link files\n" +
                                "It's suggested to make a directory for the tool in your bin directory")
       _target_dir=os.path.expanduser(ans)
       if not os.path.isdir(_target_dir):
           ans=_get_answer(prompt = "The path doesn't seem to exist. Try to make the directory? [Y/n]",
                           help = "I will try my best to create the directory/ies.\
                                   \nWould you like me to do that for you?")
           if ans == 'n' or ans == 'N':
               print("OK, see you later")
               return
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
                  _envoke(["ln -s %(source)s %(link)s" %
                          {'source' : _source,
                           'link' : _target_dir + '/' + sub_service}])
          else:
              _envoke(["ln -s %(source)s %(link)s" %
                      {'source' : _source,
                       'link' : _target_dir+'/'+service}])

       print("done.")
       print("try ghelp for more info")

#-----internal helpper functions-----
#helper function to invoke bash commands
def _envoke(cmd):
    #for debug only
    if DEBUG == True:
        print(color['yellow'] + ''.join(cmd) + color['end'])
        return

    execution=subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    o=execution.communicate()

    if o[1]:
        return o[1]
    #only return the std result, when there is no error
    if o[0]:
        return o[0]

#helper function to prompt users information and receive answers
def _get_answer(prompt = '', help = 'No help available... '):
    if 'No help available... ' != help:
        ps = color['lightblue'] + PROMPT_SIGN + color['end']
    else:
        ps = PROMPT_SIGN

    ans = raw_input(prompt + ps)
    while ans == '/h':
        ans = raw_input(help + ps)

    if '/e' == ans:
        sys.exit()
    else:
        return ans

#set the config for a new branch
def _set_branch_config(branch_from):
    #check if the config is already there
    _cur_branch = _get_current_branch()
    _read_remote = _envoke(['git config --get branch.%(curbranch)s.remote' %
                            {'curbranch': _cur_branch}
                           ])
    _read_merge = _envoke(['git config --get branch.%(curbranch)s.merge' %
                           {'curbranch': _cur_branch}
                          ])
    if _read_merge is None or _read_remote is None:
        #read the remote and merge values from the parent branch
        _parent_remote = _envoke(['git config --get branch.%(curbranch)s.remote' %
                                  {'curbranch': branch_from}
                                 ])
        _parent_merge = _envoke(['git config --get branch.%(curbranch)s.merge' %
                                 {'curbranch': branch_from}
                                ])
        #set the remote and merge values of the current branch
        _envoke(['git config branch.%(curbranch)s.remote %(remote)s' %
                 {'curbranch': _cur_branch,
                     'remote': _parent_remote }
                ])
        _envoke(['git config branch.%(curbranch)s.merge %(merge)s' %
                 {'curbranch': _cur_branch,
                     'merge': _parent_merge }
                ])

#prompt the user a list of versions and ask for a selected version
def _get_version(since = '7', until = '0'):
    _since = since
    _until = until
    _record_number = since
    while True:
        _logs = GITInfo(srv = 'gif', param = ['gif', _since, _until])
        print(_logs)
        ans = _get_answer(help = 'Type:\n' +
                                 '    ID of the version you want, or\n' +
                                 '    Enter directly for more versions, or\n' +
                                 '    ["more" ID] for further details of the version')
        if ans.startswith('more'):
            _tmp = _envoke(['git log -1 %s' % ans.split()[-1]])
            print _tmp
            raw_input('Any key to continue...')
            continue
        elif '' == ans:
            _until = _since
            _since += _record_number
            continue
        else:
            return ans
#get file differences between two versions
def _get_version_range(with_previous_version = False):
    if with_previous_version is True:
        _result = GITInfo(srv = 'gif', param = ['gif', '2'])
        #obtain the base version string from the output
        _base_version = _result.split('\n')[1].split(' ')[-1]
        #obtain the current version string from the output
        _current_version = _result.split('\n')[5].split(' ')[-1]
    else:
        #get the version before the very first change is made
        print("[+] Select the" + color['red'] + " initial " + color['end'] + "version that your changes are based on")
        _base_version = _get_version(since = 4)
        print("[+] Select the" + color['red'] + " new " + color['end'] + "version that your changes are based on")
        _current_version = _get_version(since = 4)
    #_version_str = _base_version + '..' +_current_version
    _version_str = _current_version + '..' + _base_version
    #list all changed files
    _file_list = GITStatus('gstv', ['gst', _version_str])
    print(_file_list)
    _tmp = _get_answer(prompt = 'Are the files that you changed? [y/N]',
                       help = '')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _version_str

#change to a local branch
def _switch_branch(isremote = False):
    _cmd = 'git branch'
    if isremote is True:
        _cmd += ' -r'
    _tmp = _envoke([_cmd])
    if _tmp is None:
        _exit_with_error()

    #display a list of branches available
    _list = _tmp.split('\n')
    for line in _list:
        if line != '' and line != '* (no branch)':
            if '*' in line:
                #highlight the current branch
                print(' '*4 +
                      color['red'] + '>> ' + color['end'] +
                      line.split()[-1]) #get the branch name
            else:
                print(' '*4 +
                      '>> ' +
                      line.split()[-1]) #get the branch name

    _selected_branch=_get_answer(help = 'You can: \
                                       \n   Enter an existing branch above or,\
                                       \n   Type the name for an existing branch not in the list or,\
                                       \n   Type the name for a new one or,\
                                       \n   Press Enter to quit')
    if _selected_branch == '':
        #return if no branch is selected or created
        return False
    _tmp = ''
    for line in _list:
        if line != '' and _selected_branch == line.split()[-1]:
            if True == isremote:
                _local_branch = _get_answer(prompt = "Give a name for the new local branch:",
                                            help = "if give no name you will be on " +
                                                   color['red'] + "NO " + color['end'] +
                                                   "branch and we don't recommend a state of nobranch")
                if '' == _local_branch:
                    return False
                else:
                    _tmp = _envoke(['git checkout %(remote_name)s -b %(local_name)s' %
                                    {'remote_name': _selected_branch,
                                     'local_name':_local_branch}
                                   ])
            else:
                _tmp = _envoke(['git checkout %s' % _selected_branch])

            return _tmp
    #we are here because the selected branch is not in the list
    #create a new branch with the name given
    _previous_branch = _get_current_branch()
    _tmp = _envoke(['git branch %s' % _selected_branch])
    _tmp = _envoke(['git checkout %s' % _selected_branch])
    _set_branch_config(branch_from = _previous_branch)
    _result = 'branch ' +\
              color['red'] + _selected_branch + color['end'] +\
              ' has been created and you have been switched to this branch'
    #this is a new branch, set the config properly
    _result += 'and its config is set based on ' +\
               color['red'] + _selected_branch + color['end']
    return _result

#check if we are at a git repository
def _check_git_path():
    _tmp = _envoke(['git rev-parse --git-dir'])
    if 'fatal: Not a git repository' in _tmp:
        print("It seems you are not in a git repository...")
        _exit()

#get a branch list
def _get_branch_list():
    _branches = _envoke(['git branch --no-color 2> /dev/null']).split('\n')
    return [x.split()[-1] for x in _branches if x != '']

#based on git branch, to get the current git branch
def _get_current_branch():
    _branches = _envoke(['git branch --no-color 2> /dev/null']).split('\n')
    _current_branch = [branch for branch in _branches if branch.startswith('*')][0]
    _current_branch = _current_branch.split()[1]
    return _current_branch

#based on git config, to get the local path in the repository where remote branch 
#is stored.
def _get_path_to_remote_branch():
    #1. get the current branch
    _current_branch = _get_current_branch()
    #2. read the remote and merge value from the current branch section
    _remote = _get_remote_value(_current_branch)
    _merge = _get_merge_value(_current_branch)
    #3. check if the remote value references any remote section, e.g. origin
    try:
        _r_refspec, _l_refspec = _get_remote_refspec(_remote)
    except ValueError:
        #3.a this branch doesn't reference any remote section,
        #in this case the merge value is the local path to the copy of remote branch
        return _merge
    #4. now that the _l_refspec contains most part of the path,
    #get the remote branch name from the merge value 
    return _l_refspec + _merge.split('/')[-1]

#exit with error
def _exit_with_error():
    print("Exit with error")
    sys.exit()

#exit with error
def _exit():
    sys.exit()

#return message for the config item missing error
def _make_config_item_missing_msg():
    return "There are item or section missing in the config file"

#print the header of status result
def _make_status_header(ver1, ver2):
    return '[' + color['red'] + ver1 + color['end'] + ']' +\
           ' v.s ' +\
           '[' + color['red'] + ver2 + color['end'] + ']'

#print message with a fixed length bar
def _make_msg_bar(msg):
    _colorless_msg = msg
    #remove the color code
    _colorless_msg = re.sub('\033.[^m]*m', '', _colorless_msg)
    _msg_len = len(_colorless_msg)
    _pre = '_' * ((80 - _msg_len) / 2)
    _post = '_' * ((80 - _msg_len) / 2 + (80 - _msg_len) % 2)
    return _pre+msg+_post+'\n'

#get the remote refspec and the local refspec
def _get_remote_refspec(name):
    _command = 'git config --get remote.%(name)s.fetch' %\
            {'name': name}
    _tmp = _envoke([_command])
    if _tmp is None:
        raise ValueError
    _tmp = _tmp[:-1]
    _remote, _local = _tmp.split(':')
    #in case there is no * in _remote or _local.
    _remote = _remote.strip('*+')
    _local = _local.strip('*')
    _remote = _remote[5:] #remove the 'refs/'
    _local = _local[5:] #remove the 'refs/'
    return _remote, _local

#command to get the merge branch from config file, based on the given current branch name
def _get_merge_value(curbranch):
    _command = 'git config --get branch.%(cur_branch)s.merge' %\
                           {'cur_branch':curbranch}
    _tmp = _envoke([_command])
    if _tmp is None:
        raise ConfigItemMissing
    return _tmp[:-1]

#command to get the remote branch from config file, based on the given current branch name
def _get_remote_value(curbranch):
    _command = 'git config --get branch.%(cur_branch)s.remote' %\
                        {'cur_branch':curbranch}
    _tmp = _envoke([_command])
    if _tmp is None:
        raise ConfigItemMissing
    return _tmp[:-1]

#command to do git diff between two versions
def status_version_cmd(verstr):
    return "git diff %(version_str)s --name-only" %\
               {'version_str': verstr}

def _get_remote_branch():
    #show diff between the local branch's HEAD and the remote branch's HEAD
    #get the remote repository from the config file
    _current_branch = _get_current_branch()
    _merge = _get_merge_value(_current_branch)
    if _merge is None:
        raise ConfigItemMissing
    else:
        _remote = _get_remote_value(_current_branch)
        if _remote is None:
            raise ConfigItemMissing
        else:
            if _remote == '.':
                _remote = ''
            else:
                _remote = '/' + _remote
            return _get_path_to_remote_branch()

#command to do git diff between the local branch HEAD and the remote branch HEAD
def status_branch_cmd(remotebranch):
    return 'git diff %(remote_branch)s --name-only' %\
               {'remote_branch': remotebranch}

#command to do git status
def status_cmd(param):
    return 'git status ' % param

# command to generate a patch with given version string
def patch_cmd(param):
    return 'git format-patch -k --stdout %(ver_string)s > /tmp/backup.patch' %\
               {'ver_string': param}

CALL_TABLE = { 'gst': GITStatus,
               'gsw': GITSwitch,
               'gif': GITInfo,
               'gbu': GITBackup
             }

if __name__ == '__main__':
    """
    the main function
    this tool works like busybox: all the symbolic links to the same file.
    depending on what command name is invoked, we provide corresponding services.
    """
    _envoke(['export','LANG=en_US.UTF-8'])

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
        except KeyError:
            GITSetup()
        #except Exception:
        #    print("unhandled error, please check your inputs")

    """
    elif real_cmd == 'gco':
        GITClone(real_cmd, sys.argv[1:])
    elif real_cmd.startswith('gdi'):
        #check if we are in a valid git repository
        _check_git_path()
        try:
            GITDiff(isremote = ('r' in real_cmd),
                    isgui = ('u' in real_cmd),
                    isversion = ('v' in real_cmd),
                    isfile = ('f' in real_cmd),
                    versions = sys.argv[1] if ('v' in real_cmd) else '',
                    file = sys.argv[2] if ('f' in real_cmd and 'v' in real_cmd)
                                       else (sys.argv[1] if ('f' in real_cmd) else ''))
        except IndexError:
            print("ERROR: unmatched command and input parameters")
    elif real_cmd.startswith('gsw'):
        #check if we are in a valid git repository
        _check_git_path()
        GITSwitch(real_cmd, sys.argv[1:])
    elif real_cmd == 'gbu':
        #check if we are in a valid git repository
        _check_git_path()
        GITBackup()
    elif real_cmd == 'grs':
        #check if we are in a valid git repository
        _check_git_path()
        GITRestore()
    elif real_cmd == 'gpl':
        #check if we are in a valid git repository
        _check_git_path()
        GITPull(branch = sys.argv[1] if (len(sys.argv) == 2) else None)
    elif real_cmd.startswith('gsh'):
        #check if we are in a valid git repository
        _check_git_path()
        if len(sys.argv) == 3:
            GITShare( cmd = real_cmd, his_email = sys.argv[1], his_branch = sys.argv[2] )
        else:
            GITShare( cmd = real_cmd )
    elif real_cmd == 'gpp':
        #check if we are in a valid git repository
        _check_git_path()
        GITPrepare()
    elif real_cmd == 'gfl':
        _check_git_path()
        GITFile(real_cmd, sys.argv[1:])
    elif real_cmd == 'ghelp':
        hm = HelpMaker(sys.argv[0])
        if len(sys.argv) == 2:
            hm.show_help(sys.argv[1])
        else:
            hm.show_help()
    else:
        GITSetup()
    """
