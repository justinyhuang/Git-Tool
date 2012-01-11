#!/projects/phx/tools/python/bin/python -W ignore::DeprecationWarning
"""
GitBox - a utility set for easier use of git

Available services:
   gbu: Git BackUp, commit changes in the working copy to local repository
   gpt: Git PuT, to put the local changes to the remote repository
   gif: Git InFo, shows basic information of the current version
   gst: Git STatus, list modified/added/removed files between versions/branches
   gbr: Git Switch, switch/create to a branch/tag, remotely or locally
   gdi: Git DIff, compare file/s between versions/branches
   ghelp: help info for GITUtil
Proposed services:
   ggt: Git GeT, to get a copy of the target repository
   grs: Git ReStore, go back to a previous backup version
   gpl: Git PulL, pull lastest version from the remote repository
   gpp: Git Prepare, set up a new sandbox with all your changes inside
        *This is for preparing a clean sandbox to submit for integration
   gfl: Git File, to fetch a file from a version
   gpa: Git PAtch
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
TODO: implement the \d command of Prompt Mode
TODO: make it real that with the delete command one can delete a branch or a history entry.
TODO: implement the feature to revert a file change with the delete command based on a gst output. User should be able to invoke a gdi before determining to revert the file change.
TODO: to give user indexes when selecting something, instead of typing the real item
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
               'ggt',
               'gpt',
               'gst',
               'gcf',
               ['gst' + x for x in allperm('dr')], #combination of 'd', 'r'
               ['gst' + x for x in allperm('br')], #combination of 'b', 'r'
               ['gst' + x for x in allperm('vr')], #combination of 'v', 'r'
               'gif', 'gift', 'gifg',
               'gbu',
               #'grs',
               'gbr',
               ['gbr' + x for x in allperm('rt')], #combination of 'r', 't'
               #'gpl',
               #'gfl',
               'gdi',
               [ 'gdi' + x for x in allperm('rvf')], # combination of 'r','v','f'
               [ 'gdi' + x for x in allperm('1rvf')], # combination of 'r','v','f', '1'
               [ 'gdi' + x for x in allperm('2rvf')], # combination of 'r','v','f', '2'
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

class Ball(object):
    """
    A ball is a carrier that holds the output of a git-tool helper function
    the carrier is able to perform certain operations on the data it holds.
    """
    def __init__(self, list, **param):
        """
        init the ball
        """
        #all the data will be stored in a list
        self._list = list
        #for any future extended functionalities
        self._param = param
    def get_list(self):
        return self._list
    def set_list(self, list):
        self._list = list
    def delete(self, item_list):
        #only remove the item from the list,
        #specific delete will be done in children objects.
        item_list.sort(reverse=True) #remove the very last item in the list first
        for x in item_list:
            self._list.remove(self._list[x])

class BranchBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list, **param):
        super(BranchBall, self).__init__(list)
    def delete(self, item_list):
        for x in item_list:
            _delete_branch(self._list[x])
        super(BranchBall, self).delete(item_list)

class FileBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list, **param):
        super(FileBall, self).__init__(list)
    def delete(self, item_list):
        for x in item_list:
            _revert_file(self._list[x])
        super(FileBall, self).delete(item_list)

class SourceBall(Ball):
    """
    A ball that holds a list of sources
    """
    def __init(self, list, **param):
        super(FileBall, self).__init__(list)
    def delete(self, item_list):
        for x in item_list:
            _delete_source(self._list[x])
        super(FileBall, self).delete(item_list)

class GITError(Exception):
    """base class of all GitTool error exceptions"""

class ConfigItemMissing(GITError):
    """The item/section in the git config file does not exist"""

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
        if _has_uncommited_files() is True:
            print("There are still files unstaged/uncommited." +
                  "Please use gbu to commit all your changes before" +
                  "updating this repository")
            _exit()
        #prompt if only need to update the current branch
        _ans = _get_answer(prompt = "Update the current branch? [Y/n]",
                           help = "'n' or 'N' will lead you to a 'git clone', " +
                                  "with any other input will update the local branch")
        if _ans != 'n' and _ans != 'N':
            #update the current branch
            _update_local_branch()
            return "done"
    #2. get the source
    #print the list of known resources from the global config file
    _source_list = _get_source_list()
    _color = color.values()
    for r, _index in zip(_source_list, range(len(_source_list))):
        #use different colors to differentiate the lines
        print(_color[_index % len(_color)] + 
              "%d  -  %s" % (_index, r) + _end_)
    #ask for an input
    _tmp = _get_answer(prompt = 'What source would you like to clone from',
                       help = 'select the source by the index number' +
                              'or type in the repository/branch')
    #TODO: check if the local config merge and remote values are correct
    if re.match('^\d+$', _tmp) is not None:
        #seems like a know source is selected
        _ifnew = False
        _source = _source_list[int(_tmp)]
    else:
        #new source specified by the user?
        _ifnew = True
        _source = _tmp
    pdb.set_trace()
    #3. fetch or clone the source
    #with the given source, determine whether to clone or fetch the data
    if re.match('^git@.*:.*', _source) is not None:
        #this seems like a clone request
        #need to consider if the user like to update but accidentally comes here
        _ifclone = True
        _cmd = clone_cmd(_source)
    else:
        #i believe this is a fetch request
        if _root_path() is None:
            return "Seem like you are trying to fetch a branch, but in no git reporitory" +\
                  "You might consider issue the command in a repository..."
        _ifclone = False
        _branch_name = _source.split('/')[-1]
        #the local path is generated by replacing the 'refs/' at the front 
        #to 'refs/remotes/'
        _local_repo = _source.replace('refs/', 'refs/remotes/', 1)
        _cmd = fetch_origin_cmd(_source, _local_repo)
    _tmp = _invoke([_cmd])
    if _ifclone is False:
        #it is a fetch
        #make a local branch and switch to the new branch
        _make_branch_link_to_local_repo(_branch_name, _local_repo[5:]) #skip the 'refs/'
    #4.update the global config file with the checked out source path
    if _ifnew is True:
        _add_to_source_list(_source)
    return _tmp

def GITPut(srv, param):
    """ gpt
        put the local changes to a remote repository
        the 'put' could be a direct 'git push', or an interface pointed to a customized
        submit script
    """
    _url = _get_remote_url()
    if _url is None:
        _ans = _get_answer(prompt = "would you like to manually type in the url? [y/N]",
                           help = "the url of the remote repository is not set in the config file.\n" +
                                  "You have to tell where you'd like to push your changes, \n" +
                                  "or exit to fix it in other means.")
        if _ans == 'y' or _ans == 'Y':
            _url = _get_answer(prompt = "url = ", help ='')
        else:
            _exit()
    #do a push with the given url
    pass

def GITStatus(srv, param):
    """
    gst
    show the status (what have been changed) between repositories, branches or versions.
    gst(rvd): without (rvd), is equal to 'git status -s', showing the changed files
              between working copy and the HEAD of current local branch.

              with (r), show the changed files between the current branch (in
              local repository) with that of its remote branch (REMOTE_BRANCH
              by default)

              with (v), the tool will show a list of files that are changed
              across different versions.
              you need to provide a parameter to specify the version(s).
              something like "<version sha1>..<version sha2>", or
                             "<version sha>", or other git valid version strings
              will work.

              with (b), the tool will show a list of files that are changed 
              between the HEAD of two local branches.

              with (d), the tool will only show a list of changed files in the
              current directory

              possible combinations are: r, rd, v, vd, b, bd, d
    """
    _check_git_path()
    _isbranch = ('b' in srv)
    _isremote = ('r' in srv)
    _isversion = ('v' in srv)
    _isdir = ('d' in srv)
    _version_str = param[1] if _isversion else None
    _branch_name = param[1] if _isbranch else None
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
                _exit_with_error(_make_config_item_missing_msg())
        else:
            #we have a local branch, start comparing
            pass
        _cmd = status_branch_cmd(_branch_name)
    else:
        #we are asked to do a normal 'git status'
        _cmd = status_cmd('')
    if _isdir is True:
        #only show the touched files in the current directory
        _cmd += ' -- ' + os.getcwd()
    #eventually invoke the command
    _tmp_result = _invoke([_cmd])
    #prettify the outcome
    _final_str = ''
    if _isversion or _isbranch or _isremote:
        if _isremote is True or _isbranch is True:
            _comp2, _comp1 = _branch_name, _current_branch
        elif '..' in _version_str:
            _comp2, _comp1 = _version_str.split('..')
        elif re.search('^.[0-9a-fA-F]*$', _version_str) is not None:
            _comp2 = _version_str
            _changed_but_not_commited_sign = ' *' if _get_changed_uncommited_file_list() is not None\
                                                  else ''
            _comp1 = _get_current_version() + _changed_but_not_commited_sign
        else:
            #the tool is not able to get the compared versions
            _comp2 = _comp1 = 'UNKNOWN'
        if _tmp_result is None or _tmp_result.strip(' ') is None:
            _tmp_result = ''
            _changes = 0
        else:
            _changes = len(_tmp_result.split('\n')) - 1
        _total = 'Different files: ' + color['red'] + str(_changes) + _end_
        _final_str += _make_msg_bar(_make_status_header(_comp1, _comp2))
        _final_str += _tmp_result
        _final_str += _make_msg_bar(_total)
    else:
        #add indexes to the changed files
        _changed, _untracked= _get_changed_files(_tmp_result)
        _changed= ['%s>> %d%s\t%s' % (color['red'], index, _end_, x)
                   for (index, x) in zip(range(len(_changed)), _changed)]
        _untracked= ['%s>> %d%s\t%s' % (color['yellow'], index, _end_, x)
                     for (index, x) in zip(range(len(_changed), len(_changed) + len(_untracked)), _untracked)]
        _files = FileBall(_changed + _untracked)
        if _changed is None and _untracked is None:
            _final_str = 'None'
        else:
            _final_str = '\n'.join(_changed) + '\n' + '\n'.join(_untracked)
        print(_final_str)
    _ans = _get_answer(prompt = '',
                       help = 'use /e to revert a changed file, or Enter to quit',
                       ball = _files)
    _exit()
    return _final_str

def GITBranch(srv, param):
    """ gbr
        Git BRanch related operations
        gbr(rt): Without argument 'gbr' shows a list of local branches.
                 One can switch to a branch by picking the branch by index, or
                         delete a branch by '/d <branch_index>', or
                         enter directly to exit.
                 a 'gbr <branch_name>' will
                    switch to the branch if the branch exists, or
                    make and switch to the branch if it doesn't exist
                 with (r) to do similar operations but on remote branches.
                 with (t), 'gbr(r)t <tag_name>' will switch to a branch has the tag on
    """
    _check_git_path()
    _num_args = len(param)
    _hasbranch = (_num_args == 2)
    _hastag = False
    _isremote = ('r' in srv)
    _bname = _tname = ''
    if _hasbranch is _hastag is False:
        #give a list of local/remote branch to select
        return _switch_branch(_isremote)
    else:
        #either branch or tag is given
        _name = param[1]
        _cmd = 'git checkout '
        if _hasbranch is True:
            _cmd += _name
        if _hastag is True:
            #checkout a branch with the given tag
            _branchname = _get_answer(prompt = 'Enter a new branch name to keep the remote branch data',
                                      help = 'To get a remote branch, \n\
                                              it is required to create a local branch first')
            _tname = param[1]
            if _branchname.strip() == '':
                _exit_with_error("A branch name is required, the 'nobranch' is not recommended")
            else:
                _cmd += '%(tag)s -b %(newbranch)s' %\
                        {'tag': _tname,
                         'newbranch': _branchname}
        return _invoke([_cmd])

def GITInfo(srv, param):
    """gif
       to display the version/branch/tag info
       gif(tg): gif <number of versions to display>
                    when no parameter is given, only the current version info will be shown
                gif <since generation> <until generation>
                    display all the versions between the since_generation and the until_generation
                    e.g 'gif 3 0' will show you the versions from HEAD to the 3rd generation grand-parent of HEAD
                        'gif 7 4' will show you the versions from the 4th generation grand-parent of HEAD to
                        the 7th generation grand-parent of HEAD
                    * the tool is smart enough even you put the since and until version in the other order =)
                with (t) you will get the tag info if there is any.
                    Note that fetching tag info would take a bit more time
                with (g) you will get graphic version tree expression based on a dot file. *NOTE*: graphviz is required to enable the 'g' option
    """
    _check_git_path()
    _if_graphic = ('g' in srv)
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
    if _if_graphic is True:
        """
        TODO: i haven't figured out how to do this right, yet
        if _num != 0:
            _graph_since = _get_version_tree_nth_commit(0)
            _graph_until = _get_version_tree_nth_commit(_num)
        else:
            _graph_since = _get_version_tree_nth_commit(_since)
            _graph_until = _get_version_tree_nth_commit(_until)
        _range =  _graph_until + '..' + _graph_since
        """
        _range =  'HEAD'+100*'^'+'..HEAD'
        _format = '"%h" [label="<f0> %h|<f1> %an"]\n"%h":f0 -> {%p}'
    else:
        if _num != 0:
            _range = '-%(num)s' % {'num': str(_num)}
        else:
            _range = "-%(num_of_log)s --skip=%(num_to_skip)s" %\
                    {'num_of_log': str(abs(_since - _until)),
                     'num_to_skip': str(min(_since, _until))}
        _format='___%nID:       %h%nDate:     %cd%nComment:  %s'
    _result = _invoke(["git log %(range)s --format='%(format)s'" %
                    {'range': _range,
                     'format': _format}
                   ])
    #TODO: how to show the branch name in the graph???
    if _if_graphic is True:
        #further process the data and feed it to dotty
        _result = re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', _build_merge_arrows, _result)
        _result = 'digraph G{\nnode [shape=record]\n' + _result + '}'
        with open('/tmp/gittool.dotty.tmp', 'w') as f:
            f.write(_result)
        _cmd = ['dotty', '/tmp/gittool.dotty.tmp']
        return _invoke(_cmd, detached=True)
    elif _if_show_tag is True:
        #will show the tag info
        _cmd = "git log %(range)s " % {'range': _range}
        _cmd += "--pretty=format:'%ad|%h|%d' --abbrev-commit --date=short"
        _logs = _invoke([_cmd]).split('\n')
        _branch = _get_current_branch()
        _result = ''
        for _line in _logs:
            [_date, _hash, _tmp] = _line.split('|')
            _tmp = _tmp.strip(' ()').split(', ')
            if _if_show_tag is True:
                try:
                    _container_tags = _invoke(["git tag --contains %(hash)s" %
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
                               color['red'] + 'master ' + _end_ + 'branch? [y/N]',
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
                          color['red'] + _current_branch + _end_ + '? [Y/n]')
        if ans == 'n' or ans == 'N':
            if _switch_branch() == False:
                _exit()
    msg = _get_answer(prompt = 'Any comment? [enter for empty comment]')
    msg = '"' + msg + '"'
    result = _invoke(['git commit -a -m %s'%msg])
    print(result)
    #to allow local backup in one's home directory
    _ans = _get_answer(prompt = 'Backup the changes to a patch also? [y/N]',
                       help = "say y or Y if you like to make a patch file for the change")
    if _ans == 'y' or _ans == 'Y':
        _file_list, _version_str = _get_version_range(with_previous_version = True)
        if _file_list is None or _version_str is None:
            _exit_with_error();
        _tmp = _invoke([patch_cmd(_version_str)])
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
        _invoke(['mv /tmp/backup.patch ' + _target_dir +
                 '/backup.%(verstr)s.patch ' % {'verstr': _version_str}])
        return "back up has been saved as " + _target_dir +\
              '/backup.%(verstr)s.patch ' % {'verstr': _version_str}
    _exit()

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
    _isremote = ('r' in srv)
    _isversion = ('v' in srv)
    _isfile = ('f' in srv)
    #look for the user preferred diff tool
    _difftool = None
    if '1' in srv:
        _difftool = _get_diff_tool('second')
    elif '2' in srv:
        _difftool = _get_diff_tool('third')
    if _difftool is None:
        #try to get the default diff tool in this case
        _difftool = _get_diff_tool('first')
    #look for the version string
    if _isversion:
        _versions = None
        for x in param[1:]:
            if re.search('^[0-9a-fA-F]+\.\.[0-9a-fA-F]+$', x) is not None:
                #this seems like a <ver>..<ver> string
                _versions = x
                break
            if re.search('^[0-9a-fA-F]+$', x) is not None:
                #this seems like a <ver> string
                #check if the <ver> exist
                if _if_ver_exist(x) is True:
                    #make up the version string
                    _curversion = _get_current_version()
                    _versions = _curversion + '..' + x
                    break
                else:
                    #cannot find the version, keep checking the rest params
                    continue
        if _versions is None:
            #cannot find a valid version string
            _exit_with_error("cannot identify the two versions to compare\n" +
                             "please check your inputs")
    #look for a given file
    if _isfile:
        _file = None
        for x in param[1:]:
            #in this way the user doesn't have to remember the order of the
            #input parameters
            if os.path.isfile(x) is True:
                _file = x
                break
        if _file is None:
            #cannot find a valid file name in the param
            _exit_with_error("cannot identify a valid file name\n" +
                             "please check your inputs")
    _cmd = 'git difftool -y -t %s' % _difftool
    #handle remote/local diff operation
    if _isremote == False:
        # only support comparison between versions with local diff
        if _isversion == True:
            if '?' == _versions:
                #allow user to select versions on the fly
                _versions = _get_version()
            _cmd += ' %(versions)s' % {'versions': _versions}
    else:
        _cmd += ' %s' % _get_remote_branch()
    #handle when a file is given
    if _isfile == True:
        _cmd += ' %s' % _file
    #for vim it appears we need to invoke it via os.system to make it
    #work correctly
    if _difftool == 'vimdiff':
        os.system(_cmd)
    else:
        print([_cmd])
        _tmp = _invoke([_cmd])
    _exit()

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
    _current_branch_remote = _get_remote_value(_current_branch)
    _current_branch_merge = _get_merge_value(_current_branch)
    _remote_branch = _get_remote_branch()
    #global settings
    _first_diff_tool = _get_diff_tool('first')
    _second_diff_tool = _get_diff_tool('second')
    _third_diff_tool = _get_diff_tool('third')
    #make up the output
    _ret = ""
    _ret += color['yellow'] + "---Local Settings---\n" + _end_
    _ret += "current branch: %s\n" % _current_branch
    _ret += "remote value: %s\n" % _current_branch_remote
    _ret += "merge value: %s\n" % _current_branch_merge
    _ret += "remote branch: %s\n" % _remote_branch
    _ret += color['yellow'] + "---Global Settings---\n" + _end_
    _ret += "1st diff tool: %s\n" % _first_diff_tool
    _ret += "2nd diff tool: %s\n" % _second_diff_tool
    _ret += "3rd diff tool: %s\n" % _third_diff_tool
    return _ret

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
        print("back up the original .gitconfig file")
        print("if your system supports colored text, you shall see them below:")
        for c in color.keys():
            print(color[c] + c + _end_)
        _ans = _get_answer(prompt = 'do you see the colors?[Y/n]')
        if _ans == 'n' or _ans == 'N':
            _set_global('GitTool', 'ColorSupport', 'no')
        else:
            _set_global('GitTool', 'ColorSupport', 'yes')
        _invoke(['cp ~/.gitconfig ~/.gitconfig.gittool.backup'])
        #setup the difftools
        _available_tools_msg = "Valid merge tools are: araxis, bc3, diffuse, emerge, ecmerge, gvimdiff, kdiff3," +\
                               "kompare, meld, opendiff, p4merge, tkdiff, vimdiff and xxdiff."
        _ans = _get_answer(prompt = "Please specify your first choice of diff tool:",
                           help = "it will be used as the default tool when diff")
        _set_diff_tool('first', _ans)
        _ans = _get_answer(prompt = "and your second choice of diff tool?",
                           help = "it will be used as the secondary tool when diff.\
                                 \nleave it blank if you don't have a secondary diff tool")
        _set_diff_tool('second', _ans)
        _ans = _get_answer(prompt = "and your third choice of diff tool?",
                           help = "it will be used as the third tool when diff\
                                 \nleave it blank if you don't have a secondary diff tool")
        _set_diff_tool('third', _ans)
        #set the graphic info tool settings
        #setup the symbolic links
        print("Please specify where you would like to put the GITTool facilities")
        print("[eg. '~/bin/GTool', '/tools']")
        print("\nMake sure the path is in your PATH variable")
        _ans = _get_answer(help = "The GitUtilTool works based on" +
                                 color['red'] + " A LOT OF " + _end_ +
                                 "small link files\n" +
                                 "It's suggested to make a directory for the tool in your bin directory")
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):
            _ans=_get_answer(prompt = "The path doesn't seem to exist. Try to make the directory? [Y/n]",
                            help = "I will try my best to create the directory/ies.\
                                    \nWould you like me to do that for you?")
            if _ans == 'n' or _ans == 'N':
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
                   _invoke(["ln -s %(source)s %(link)s" %
                           {'source' : _source,
                            'link' : _target_dir + '/' + sub_service}])
           else:
               _invoke(["ln -s %(source)s %(link)s" %
                       {'source' : _source,
                        'link' : _target_dir+'/'+service}])

        print("done.\ntry ghelp for more info")

#-----internal helpper functions-----
#invoke bash commands
def _invoke(cmd, detached = False):
    #for debug only
    if DEBUG == True:
        print(color['yellow'] + ''.join(cmd) + _end_)
        return
    if detached is False:
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
    else:
        #invoke bash commands in separate process, no error return 
        subprocess.Popen(cmd, stderr=subprocess.PIPE)
        return ""

#helper function to prompt users information and receive answers
def _get_answer(prompt = '', help = 'No help available... ', ball = None):
    #TODO: add support to allow deleting an entry
    if 'No help available... ' != help:
        ps = color['lightblue'] + PROMPT_SIGN + _end_
    else:
        ps = PROMPT_SIGN
    ans = raw_input(prompt + ps)
    while ans == '/h':
        ans = raw_input(help + ps)
    if '/e' == ans:
        sys.exit()
    elif ans.startswith('/d '):
        if ball is None:
            _exit_with_error("no ball is passed while a delete is required")
        if re.search('^\/d \d+([\s,-]+\d+)*\s*$', ans): #space or ',' can be used to separate the indexes
            #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
            _tmp = re.sub('\d+[\s]*-[\s]*\d+', _expand_indexes_from_range, ans[3:])
            ball.delete([int(x.group()) for x in re.finditer('\d+', _tmp)]) #get all the indexes
        else:
            _exit_with_error("to delete an item, try '/d <index>'")
        pass
    else:
        return ans

#set the config for a new branch
def _set_branch_config(branch_from):
    #check if the config is already there
    _cur_branch = _get_current_branch()
    _read_remote = _invoke(['git config --get branch.%(curbranch)s.remote' %
                            {'curbranch': _cur_branch}])
    _read_merge = _invoke(['git config --get branch.%(curbranch)s.merge' %
                           {'curbranch': _cur_branch}])
    if _read_merge is None or _read_remote is None:
        #read the remote and merge values from the parent branch
        _parent_remote = _invoke(['git config --get branch.%(curbranch)s.remote' %
                                  {'curbranch': branch_from}])
        _parent_merge = _invoke(['git config --get branch.%(curbranch)s.merge' %
                                 {'curbranch': branch_from}])
        #set the remote and merge values of the current branch
        _invoke(['git config branch.%(curbranch)s.remote %(remote)s' %
                 {'curbranch': _cur_branch,
                     'remote': _parent_remote }])
        _invoke(['git config branch.%(curbranch)s.merge %(merge)s' %
                 {'curbranch': _cur_branch,
                     'merge': _parent_merge }])

#prompt the user a list of versions and ask for a selected version
def _get_version(since = '7', until = '0'):
    _since = since
    _until = until
    _record_number = since
    while True:
        _logs = GITInfo(srv = '', param = ['gif', _since, _until])
        print(_logs)
        ans = _get_answer(help = 'Type:\n' +
                                 '    ID of the version you want, or\n' +
                                 '    Enter directly for more versions, or\n' +
                                 '    ["more" ID] for further details of the version')
        if ans.startswith('more'):
            _tmp = _invoke(['git log -1 %s' % ans.split()[-1]])
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
        _result = GITInfo(srv = '', param = ['gif', '2'])
        #obtain the base version string from the output
        _base_version = _result.split('\n')[1].split(' ')[-1]
        #obtain the current version string from the output
        _current_version = _result.split('\n')[5].split(' ')[-1]
    else:
        #get the version before the very first change is made
        print("[+] Select the" + color['red'] + " initial " + _end_ +
                "version that your changes are based on")
        _base_version = _get_version(since = 4)
        print("[+] Select the" + color['red'] + " new " + _end_ +
                "version that your changes are based on")
        _current_version = _get_version(since = 4)
    _version_str = _current_version + '..' + _base_version
    #list all changed files
    _file_list = GITStatus('v', ['gst', _version_str])
    print(_file_list)
    _tmp = _get_answer(prompt = 'Are the files that you changed? [y/N]',
                       help = '')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _version_str

#show a lost of local/remote branches and do something
def _switch_branch(isremote = False):
    _curbranch, _tmp_list = _get_branch_list(isremote)
    _list = BranchBall(_tmp_list)
    #display a list of branches available
    _show_indexed_list(_list, _curbranch)
    _selected_index = _get_answer(help = "You can: \
                                       \n   Enter branch index or,\
                                       \n   Type the name for a new one or,\
                                       \n   Use '/d <branch_name>' to delete a branch\
                                       \n   Press Enter to quit")
    if _selected_index == '':
        #return if no branch is selected or created
        return ""
    elif _selected_index.startswith('-'):
        #delete a branch here??
        pass
    else:
        _selected_branch = _list[int(_selected_index)]

    _tmp = ''
    for line in _list:
        if line != '' and _selected_branch == line.split()[-1]:
            if True == isremote:
                _local_branch = _get_answer(prompt = "Give a name for the new local branch:",
                                            help = "if give no name you will be on " +
                                                   color['red'] + "NO " + _end_ +
                                                   "branch and we don't recommend a state of nobranch")
                if '' == _local_branch:
                    return False
                else:
                    _tmp = _invoke(['git checkout %(remote_name)s -b %(local_name)s' %
                                    {'remote_name': _selected_branch,
                                     'local_name':_local_branch}
                                   ])
            else:
                _tmp = _invoke(['git checkout %s' % _selected_branch])
            return _tmp
    #we are here because the selected branch is not in the list
    #create a new branch with the name given
    _previous_branch = _get_current_branch()
    _tmp = _invoke(['git branch %s' % _selected_branch])
    _tmp = _invoke(['git checkout %s' % _selected_branch])
    _set_branch_config(branch_from = _previous_branch)
    _result = 'branch ' +\
              color['red'] + _selected_branch + _end_ +\
              ' has been created and you have been switched to this branch'
    #this is a new branch, set the config properly
    _result += 'and its config is set based on ' +\
               color['red'] + _selected_branch + _end_
    return _result

def _make_branch_link_to_local_repo(bname, path):
    _cmd = "git checkout -b %(branch_name)s --track %(path)s" %\
          {'branch_name': bname, 'path': path}
    _invoke([_cmd])

def _update_local_branch():
    #1. fetch the updates from remote repo
    #check if the corresponding config items are set
    _remote = _get_remote_value(_get_current_branch())
    _merge = _get_merge_value(_get_current_branch())
    print("fetching from %s ..." % _remote)
    _cmd = 'git fetch'
    print(_invoke([_cmd]))
    #2. ask for option
    _ans = _get_answer(prompt = "fetch completes, shall we Merge or Rebase? (m/R)",
                       help = "Merge will keep the history of changes but mix the local " +\
                              "changes with the merged changes; while Rebase keeps all " +\
                              "local changes together but modifies the change history " +\
                              "and make it hard to trace back. You shall determine which " +\
                              "strategy you would like to use, carefully.")
    _remote_branch = _get_remote_branch()
    if _ans == 'm' or _ans == 'M':
        #3a. merge
        print("merging from %s ..." % _merge)
        _cmd = 'git merge ' + _remote_branch
        return _invoke([_cmd])
    else:
        #3b. rebase, which is recommended in many cases
        print("rebasing from %s ..." % _merge)
        _cmd = 'git rebase'
        return _invoke([_cmd])
    #TODO: there is yet another option, see the better (and more complicated) rebase at
    # http://softwareswirl.blogspot.com/2009/04/truce-in-merge-vs-rebase-war.html

#get the root path of the current repository
def _root_path():
    _cmd = 'git rev-parse --show-toplevel'
    _tmp = _invoke([_cmd])
    if 'Not a git repository' not in _cmd:
        return _tmp
    else:
        return None

#check if we are at a git repository
def _check_git_path():
    if _root_path() is None:
        print("It seems you are not in a git repository...")
        _exit()

#get the source list length
def _get_source_list_len():
    _command = 'git config --global sourcelist.length'
    _len = int(_invoke([_command]))
    if _len is None:
        raise ConfigItemMissing
    return _len

#create a branch with track to the local repository
def _create_branch_link_to_local_repo(bname, rname):
    _cmd = 'git checkout -b %(branch)s --track %(localrepo)s' %\
           {'branch': bname, 'localrepo': rname}
    return _invoke([_cmd])

#set the source list length
def _set_source_list_len(len):
    _command = 'git config --global sourcelist.length %d' % len
    _invoke([_command])

#read the remembered source list
def _get_source_list():
    _len = _get_source_list_len()
    _list = list()
    for i in range(_len):
        _command = 'git config --global sourcelist.item%d' % (i + 1)
        _tmp = _invoke([_command])
        if _tmp is None:
            raise ConfigItemMissing
        _list.append(_invoke([_command])[:-1])
    return _list

#add a new source into the source list
def _add_to_source_list(item):
    _len = _get_source_list_len()
    _command = 'git config --global sourcelist.item%(index)d %(item)s' %\
              {'index': _len + 1, 'item':item}
    _tmp = _invoke([_command])
    _set_source_list_len(_len + 1)

#show a list of items with index and one of the item highlighted
def _show_indexed_list(list, hightlight = -1):
    _index = 0
    for line in list:
        if _index == hightlight:
            #highlight the current branch
            print(' '*4 +
                  color['red'] + '%d >> ' % _index + _end_ +
                  line) #get the branch name
        else:
            print(' '*4 +
                  '%d >> ' % _index +
                  line) #get the branch name
        _index += 1

#get a branch list
#returns <master branch index>, <branch list>
def _get_branch_list(isremote = False):
    if isremote is False:
        _branches = _invoke(['git branch --no-color 2> /dev/null']).split('\n')
    else:
        _branches = _invoke(['git branch -r --no-color 2> /dev/null']).split('\n')
    if _branches is None:
        _exit_with_error("seems like there is no branch available...")
    _index = 0
    _current = None
    for line in _branches:
        if line != '':
            if '*' in line:
                _current = _index
        _index += 1
    return _current, [x.split()[-1] for x in _branches if x != '']

#based on git branch, to get the current git branch
def _get_current_branch():
    #_branches = _invoke(['git branch --no-color 2> /dev/null']).split('\n')
    #_current_branch = [branch for branch in _branches if branch.startswith('*')][0]
    #_current_branch = _current_branch.split()[1]
    _current_branch = _invoke(['git status']).split('\n')[0].split()[-1]
    return _current_branch

#get changed but not yet commited files
def _get_changed_uncommited_file_list():
    _command = "git diff --name-only"
    return _invoke([_command])

#get the current version string
def _get_current_version():
    _command = "git log -1 --format='%h'"
    return _invoke([_command])[:-1]

#get the url of the corresponding remote repository
def _get_remote_url():
    _current_branch = _get_current_branch()
    _remote = _get_remote_value(_current_branch)
    if _remote is None:
        raise ConfigItemMissing
    _command = 'git config --get remote.%(name)s.url' %\
              {'name': name}
    _url = _invoke([_command])
    return _url

#based on git config, to get the local path in the repository where remote branch 
#is stored.
def _get_remote_branch():
    #show diff between the local branch's HEAD and the remote branch's HEAD
    #get the remote repository from the config file
    #1. get the current branch
    _current_branch = _get_current_branch()
    #2. read the remote and merge value from the current branch section
    _remote = _get_remote_value(_current_branch)
    _merge = _get_merge_value(_current_branch)
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

#this function will expand strings like '1-3' to '1 2 3'
def _expand_indexes_from_range(obj):
    _tmp = ''
    _line = obj.group()
    _range = _line.split('-')
    for x in range(int(_range[0]), int(_range[1]) + 1):
        _tmp += ' %d ' % x
    return _tmp

def _build_merge_arrows(obj):
    _tmp = ''
    _line = obj.group()
    _from = _line[1:8]
    _list = re.findall('[a-f0-9]{7}', _line[7:])
    for x in _list:
        _tmp += '"%(from)s":f0 -> "%(ver)s":f0 [color=blue style=bold arrowhead=none arrowtail=vee]\n' %\
                {'from':_from, 'ver':x}
    return _tmp

#return list of changed files and a list of untracked files
#from the output of 'git status -s'
def _get_changed_files(str):
    _changed_file_pattern = ' M.*'
    _untracked_file_pattern = '\?\?.*'
    return [x.group() for x in re.finditer(_changed_file_pattern, str)],\
           [x.group() for x in re.finditer(_untracked_file_pattern, str)]

#exit with error
def _exit_with_error(msg = ''):
    print("Exit with error :")
    print(msg)
    sys.exit()

#exit with error
def _exit():
    sys.exit()

#return message for the config item missing error
def _make_config_item_missing_msg():
    return "There are item or section missing in the config file"

#print the header of status result
def _make_status_header(ver1, ver2):
    return '[' + color['red'] + ver1 + _end_ + ']' +\
           ' v.s ' +\
           '[' + color['red'] + ver2 + _end_ + ']'

#print message with a fixed length bar
def _make_msg_bar(msg):
    _colorless_msg = msg
    #remove the color code
    _colorless_msg = re.sub('\033[^m]*m', '', _colorless_msg)
    _msg_len = len(_colorless_msg)
    _pre = '_' * ((80 - _msg_len) / 2)
    _post = '_' * ((80 - _msg_len) / 2 + (80 - _msg_len) % 2)
    return _pre+msg+_post+'\n'

#check if there is still any file that is not yet commited
def _has_uncommited_files():
    #to be implemented
    return False

#from a version tree perspective, return a commit that is
#the nth commit from HEAD down along a branch
#like:            d1--f
#               /
#        a--b--c--d2--e
#               \
#                 d3--g--h
# the 5th commit could be either f, e, or g
def _get_version_tree_nth_commit(num):
    _cmd = 'git log HEAD' + (num + 1) * '^' +\
           '..HEAD' + num * '^' +\
           ' --ancestry-path --oneline'
    return _invoke([_cmd]).split()[0]

#get the remote refspec and the local refspec
def _get_remote_refspec(name):
    _command = 'git config --get remote.%(name)s.fetch' %\
            {'name': name}
    _tmp = _invoke([_command])
    if _tmp is None:
        raise ValueError
    _tmp = _tmp[:-1]
    _remote, _local = _tmp.split(':')
    #in case there is no * in _remote or _local.
    _remote = _remote.strip('+')
    return _remote, _local

#revert a file
def _revert_file(file):
    #get the real file name
    _file = file[file.rfind(' ') + 1:]
    #might use 'git status <file>' to obtain the status
    _cmd = status_cmd(_file)
    _tmp = _invoke(_cmd)
    if _tmp.strip().startswith('M'):
        #the file has uncommited changes
        print('reverting file [%s]' % _file)
    elif _tmp.strip().startswith('??'):
        #the file is out of version control
        print('deleting file [%s]' % _file)
    #what to do if file is commited, but need to delete from a diff list
    #   this means we need to copy a specified version to overwrite

#delete a branch
def _delete_branch(branch):
    _cmd = "git branch -d %s" % branch
    print(_cmd)
    #_invoke([_cmd])
    #of course there should be some exception handling here

def _delete_source(source):
    pass

#command to get the merge branch from config file, based on the given current branch name
def _get_merge_value(curbranch):
    _command = 'git config --get branch.%(cur_branch)s.merge' %\
                           {'cur_branch':curbranch}
    _tmp = _invoke([_command])
    if _tmp is None:
        raise ConfigItemMissing
    return _tmp[:-1]

def _saved_file_exist(file):
    _root = _root_path()
    if _root is None:
        _exit_with_error("You are not in a git repository")
    if _make_dir(_root+'/.git/savedfiles'):
        pass

#command to get the remote branch from config file, based on the given current branch name
def _get_remote_value(curbranch):
    _command = 'git config --get branch.%(cur_branch)s.remote' %\
                        {'cur_branch':curbranch}
    _tmp = _invoke([_command])
    if _tmp is None:
        raise ConfigItemMissing
    return _tmp[:-1]

#command to get the diff tool value
def _get_diff_tool(selection):
    _command = 'git config --global difftool.%s' % selection
    _tmp = _invoke([_command])
    return _tmp[:-1] if _tmp is not None else None

#command to set the diff tool value
def _set_diff_tool(selection, tool):
    _command = 'git config --global difftool.%(selection)s %(tool)s' %\
            {'selection':selection, 'tool':tool}
    _tmp = _invoke([_command])

#check if a version exists
def _if_ver_exist(ver):
    _command = 'git rev-parse ' + ver
    _tmp = _invoke([_command])
    if re.match('unknown revision', _tmp) is not None:
        return False
    else:
        return True

def _remove_link_file(x):
    _fullpath = sys.argv[0]
    _dir = _fullpath[:_fullpath.rfind('/') + 1]
    _invoke(['rm %s' % (_dir + x)])

#do something by traversing the given nested list
def _traverse_nested_list_with_action(lst, action):
    for x in lst:
        if isinstance(x, list):
            _traverse_nested_list_with_action(x, action)
        else:
            action(x)

#command to do git diff between two versions
def status_version_cmd(verstr):
    return "git diff %(version_str)s --name-only" %\
               {'version_str': verstr}

#command to do git diff between the local branch HEAD and the remote branch HEAD
def status_branch_cmd(remotebranch):
    return 'git diff %(remote_branch)s --name-only' %\
               {'remote_branch': remotebranch}

#command to do git status
def status_cmd(param):
    return 'git status -s ' + param

# command to generate a patch with given version string
def patch_cmd(param):
    return 'git format-patch -k --stdout %(ver_string)s > /tmp/backup.patch' %\
               {'ver_string': param}
# command to clone a copy of a repository
def clone_cmd(param):
    return 'git clone' + param
#command to fetch a remote branch
def fetch_origin_cmd(src, dst):
    return'git fetch origin %(source)s:%(local)s' %\
            {'source':src, 'local':dst}

CALL_TABLE = { 'gst': GITStatus,
               'gbr': GITBranch,
               'gif': GITInfo,
               'gbu': GITBackup,
               'gdi': GITDiff,
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
        except KeyError:
            GITSetup(sys.argv)
        #enable the error hiding for released version
        #except Exception:
        #    print("unhandled error, please check your inputs")
