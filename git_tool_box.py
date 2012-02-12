#!/usr/bin/python -W ignore::DeprecationWarning
"""
Git-Tool - a utility set for easier use of git

Available services:
   gsv: Git SaVe, to 'save' your changes
   gld: Git LoaD, to 'load' new data as/into current working copy
   gdi: Git DIff, compare file/s between commits/branches
   gst: Git STatus, list modified/added/removed files between hashes/branches
   gls: Git List, shows basic information of the current hash
   ghelp: help info for GITUtil
Proposed services:
   ???gfl: Git File, to fetch a file from a hash
Dependencies (please install):
   git: Git-Tool is a wrapper of git
   graphviz and qiv: Git-Tool needs both to show graphical hash tree via glsg
"""
import os
import re
import sys
import subprocess
import git
import pdb
from optparse import OptionParser

"""
TODO: add index to the graphical commit tree.
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
              With 'gsv <filename>' gsv will allow the user to pick two hashes and
              generate the patch file based on user's selection.

        Do 'gsv ?' to show this help message.
    """
    _current_branch = _get_current_branch()
    if len(param) > 1: #user ask for generating a patch
        if len(param) == 3: #both hash string and the file name is given
            _hash_str, _patch_file = param[1], param[2]
        else: #only file name is given, help him to pick two hashes
            _patch_file = param[1]
            _file_list, _hash_str = _get_hash_change()
        _tmp = _invoke([git.patch(selection = _hash_str, patch_file = _patch_file)])
        _ans = _get_answer(prompt = 'where to store %s ?' % _patch_file)
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):#directory doesn't exist, try to make one
            os.makedirs(_target_dir)
        _invoke(['mv %s %s' % (_patch_file, _target_dir)])
        return '\npatch saved to %s/%s' % (_target_dir, _patch_file)
    else: #do a push or a commit
        if _num_uncommited_files(): #there are changed files to commit
            _ans=_get_answer(prompt = 'Back up in ' +\
                             color['red'] + _current_branch + _end_ + ' ? [Y/n]',
                             default = 'y')
            if _ans == 'n' or _ans == 'N':
                _branch_list, _selected_branch = _select_branch()
                _do_checkout_branch(_selected_branch, _branch_list)
            _msg = _get_answer(prompt = 'Any comment? [empty comment is not allowed]')
            _msg = '"' + _msg + '"'
            _invoke([git.commit(' -a -m %s' % _msg)])
            return "Done"
        else: # there is no changed files, try a push
            return _push_to_remote()

def GITLoad(srv, param):
    """ gld
        To 'load' new data into/as your current copy. A 'load' could be:
            * a git clone - load a repository to local path
              When issued in a git path, with no parameter given
              'gld' will perform a git clone.

            * a git fetch/pull/rebase - load new changes from remote repo to local
                                        after that one can choose to do a merge/rebase
              When issued in a git path, with no parameter given
              'gld' will perform a git fetch (update the local repo),
              and allow to merge, rebase, or quit after fetch.

            * a git apply - load changes from a patch file
              When 'gld <patch_name>' in a git path
              'gld' will perform a git apply to take the patch into current working copy

            * a git checkout/merge - load data from a branch, or by a hash/tag
              When 'gld <ref_name>' in a git path, where a ref could be a branch/hash/tag
              'gld' will perform a git checkout or merge

        When not sure about the branch/hash/tag, use:
            * gldb - to pick a branch from a list and do a checkout or merge.
            * gldr - to fetch/merge a remote branch picked from list
            * gldh - to pick a hash (a.k.a commit/hash) from a list and do a checkout or merge
            * gldt - to pick a tag from list and do a checkout or merge [NOT IMPLEMENTED]

        Do 'gld ?' to show this help message.
    """
    _ifremote = 'r' in srv
    _ifbranch = 'b' in srv or _ifremote #when 'r' is given, 'b' automatically becomes True
    _ifhash = 'h' in srv
    _iftag = 't' in srv
    if not _root_path(): #in a non-git path, do a clone (nothing else we could do, right?)
        if _ifbranch or _ifremote or _ifhash or _iftag:
            _exit_with_error("You need to run the command in a git repo")
        _result = _do_clone()
    else: #in a git path
        _curbranch = _get_current_branch()
        """
        if _num_uncommited_files() > 0:
            print("There are still files unstaged/uncommited.\n" +
                  "Please use gsv to commit all your changes before" +
                  "further 'load' activities")
            _exit()
        """
        if _ifbranch: #this is a branch thing
            _branch_list, _selected_branch = _select_branch(_ifremote)
            if _ifremote or _merge_or_checkout() == 'c':# fetch from remote, or checkout locally
                _result = _do_checkout_branch(_selected_branch, _branch_list, _ifremote)
            else: #merge
                _result = _do_merge(_ans)
        elif _ifhash: #checkout a hash to a new branch
            _hash = _select_hash()
            if _merge_or_checkout() == 'c': #checkout
                _do_checkout_from_commit(_hash)
            else: #merge
                _result = _do_merge(_hash)
        elif _iftag: #checkout a tag to a new branch
            _exit_with_error("This feature is not yet supported")
        else: # no specific direction is given, we might just guess
            if len(param) == 2: #something is provided as the parameter
                if os.path.isfile(param[1]): #this is a patch file
                    _result = _do_apply(param[1])
                elif param[1] in _get_branch_list()[1]: #this is a local branch
                    if _merge_or_checkout() == 'c': #checkout
                        _result = _do_checkout_branch(param[1])
                    else: #merge
                        _result = _do_merge(param[1])
                elif _is_remote_branch(param[1]):#this is a remote branch
                    _result = _do_fetch(param[1])
                    #TODO: can we support merging from a remote branch?
                else: #the last possibility is...tag, try with fingers crossed...
                    _result = _do_checkout_from_commit(param[1])
            else: #no parameter is given. if i have to guess, i will try updating the repo
                _ans = _get_answer(prompt = "Update the current repository? [Y/n]", default = 'y',
                                   help = "after the update, you can choose to either" +
                                          "merge or rebase your local changes")
                if _ans != 'n' and _ans != 'N':
                    _update_local_branch()
                    return "done"
                else:
                    _exit_with_error("Please tell me more. You know I don't know what you know :(")
    return _result

def GITDiff(srv, param):
    """ gdi
        To show differences of file/s between:
            * working copy and the latest commit.
              'gdi' without parameter shows the file difference.
            * local copy and the linked/tracked remote one.
              'gdir' without parameter shows the file difference.
            * two hashes.
              'gdi <hash1>..<hash2>' shows file difference between hash1 and hash2.
              'gdi <hash>' shows file difference between working copy and hash.
              'gdih' without parameter allows to select two hashes to compare.

        'gdi' allows doing diff with different tools:
            * 'gdi' and its relatives will do diff with the default primary diff tool.
            * 'gdi2'/'gdi3' and its relatives will do diff with the secondary/third diff tool.

        'gdi <filename>' with or without other options shows only the difference in the given file.
    """
    _check_git_path()
    _isremote, _ishash = ('r' in srv), ('h' in srv)
    _difftool = _file = _hashes = _remote_branch = ''
    #look for the user preferred diff tool
    if '2' in srv:
        _difftool = _get_global('difftool.second')
    elif '3' in srv:
        _difftool = _get_global('difftool.third')
    if not _difftool: #try to get the default diff tool in this case
        _difftool = _get_global('difftool.first')
    if _isremote: #handle remote diff operation
        _remote_branch = _get_remote_branch()
    else: #handle non-remote diff
        for x in param[1:]: #looking for any hash info
            if re.search('^[0-9a-fA-F]+\.\.[0-9a-fA-F]+$', x) is not None:
                _hashes = x #this seems like a <hash>..<hash> string
                break
            if re.search('^[0-9a-fA-F]+$', x):
                if _if_hash_exist(x): #this seems like a <hash> string
                    _curhash = _get_hashes(1)[0]
                    _hashes = _curhash + '..' + x #make up the hash string
                    break
                else:
                    continue #cannot find the hash, keep checking the rest params
        if _ishash and not _hashes: #allow user to select hashes on the fly
            _hashes = _select_hash_range()
    for x in param[1:]:
        if os.path.isfile(x): #the file exist
            _file = x
            break
    _cmd = git.difftool(_difftool, _hashes, _remote_branch, _file)
    #if there are too many files, warn the user before doing diff
    _num = _number_of_changed_files(_hashes, _remote_branch, _file)
    if _num > 7: # i guess 7 is a good limit
        _ans = _get_answer(prompt = 'are you sure to diff about '
                                   + color['red'] + '%d' % _num + _end_
                                   + ' files?[y/N]', default = 'n')
        if _ans != 'y' and _ans != 'Y':
            _exit()
    #for vim it appears we need to invoke it via os.system to make it work correctly
    if _difftool == 'vimdiff':
        os.system(_cmd)
    else:
        _tmp = _invoke([_cmd])
    return ''

def GITStatus(srv, param):
    """
    gst
    To show the status (what have been changed) between:
       * working copy and the latest commit.
         'gst' shows the changed files
       * two commits/branch HEADs
         'gst <hash1>..<hash2>' or 'gst <branch1>..<branch2>' shows the changed files
         'gsth' allows to select two hashes to show the changed files between them
       * working copy and the given commit/branch HEAD
         'gst <hash>' or 'gst <branch>' shows the changed files
       * working copy and its tracked/linked remote
         'gstr' shows the changed files

    To only show changed files in current directory:
         'gstd' will do the job.
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

        When comparing between hashes/branches, the status codes are a bit different:
            A = Added         C = Copied    D = Deleted  M = Modified  R = Renamed
            T = Type changed  U = Unmerged  X = Unkown   B = pairing Bloken

        * http://progit.org/book/ch2-2.html has more details
    """
    _check_git_path()
    _isdir, _isremote, _ishash = ('d' in srv), ('r' in srv), ('h' in srv)
    _compare_str = param[1] if len(param) > 1 else ''
    _cmds, _status = list(), ''
    if _isremote: #comparing with the remote branch
        _compare_str = _get_remote_branch()
    elif _ishash:
        _compare_str = _select_hash_range()
    if _compare_str:#with comparison objects specified, use 'git diff'
        for t in 'ACDMRTUXB':#diff with different diff filter to get the change's type
            _cmds.append(git.diff(selection = _compare_str, name_only = True, type = t))
    else:# without comparison objects specified, use 'git status'
        _cmds.append(git.status(param = '-s'))
    for c in _cmds:
        if _isdir: #only show the touched files in the current directory
            c += ' -- ' + os.getcwd()
        _tmp = _invoke([c])
        _tmp = _translate_status_code(c, _tmp)
        _status += _tmp[:_tmp.rfind('\n')] + '\n' if _tmp else ''
    _final_str = '' # prepare for a prettified outcome
    if _compare_str:#show changed files between two commits
        if '..' in _compare_str: #two compare candidates are given
            _comp1, _comp2 = _split(_compare_str, '..')
        else:
            if _if_branch_exist(_compare_str): #only one candidate given, which is a branch
                _comp2, _comp1 = _compare_str, _get_current_branch()
            elif 'unknown revision' in _status: #something wrong with the given candidate
                _exit_with_error('unknown hash/branch, please check')
            else:#assume this is comparison between hashes
                _comp1, _comp2 = _compare_str, _get_hashes(1)[0]
            if _num_uncommited_files(): #show 'working copy' if there is any local change
                _comp2 = 'working copy'
        if not _status or not _status.strip(' '):
            _status = '' #there is no changes found
            _changes = 0
        else:
            _changes = len(_split(_status, '\n')) - 1
        _changed = _split(_status, '\n')[:-1]
        _untracked= []
    else: #show changed but not yet commited files, with indexes added
        _changed, _untracked= _get_changed_files(_status)
        _changes = len(_changed)
        _comp1, _comp2 = _get_current_branch(), 'working copy'
    _total = 'Changed files: ' + color['red'] + str(_changes) + _end_
    _files = FileBall(_changed + _untracked)
    _ans = _get_answer(prefix = _make_msg_bar(_make_status_header(_comp1, _comp2)), prompt = '',
                       default = '/e',
                       help = _git_status_code,
                       ball = _files)
    return ''

def GITList(srv, param):
    """
    gls
    To show a list of commits with the information of:
        * hash, date and comment.
          'gls <n>' shows n latest commits' info.
          When no parameter is given, shows that of the latest commit.
          'gls <since index> <until index>' shows all the commits
          between the two indexes.
          e.g 'gls 3 0' shows the commits from HEAD to the 3rd parent of HEAD
              'gls 7 4' shows the commits from the 4th parent to the 7th parent of HEAD
        * hash, date, comment, branch and tag.
          'glst' shows more information including branches and tags, if there is any.
          However, fetching the tag info would take a bit more time.
        * hash, committer and date in graphics.
          'glsg' shows a graphical commit tree.
          *NOTE*: graphviz and qiv is required to enable the 'g' option
    """
    _check_git_path()
    _if_graphic, _if_show_tag = ('g' in srv), ('t' in srv)
    _since = _until = _num = 0
    if len(param) == 3: #start and end of a hash segment is given.
        _since, _until  = int(param[1]), int(param[2])
    elif len(param) == 2: #the number of hashes is given.
        _num = int(param[1])
    else: #default, show the latest hash info
        _num = 1
    if _if_graphic:
        _do_log_graphic(_num, _since, _until)
        return ''
    else:
        if _num != 0:
            _range = '-%d' % _num
        else:
            _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                    {'num_of_log': abs(_since - _until) + 1,
                     'num_to_skip': min(_since, _until) - 1}
        if _if_show_tag is True: #show the tag info
            print("this will take a while...")
            _result = _do_log_tag(_range)
        else:
            _format='___\nRev:       %h%nDate:     %cd%nComment:  %s'
            _result = _do_log(_range, _format)
        return _result

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

#setup the environment for first use
def GITSetup(param):
    if len(param) == 2 and param[1] == 'clean':
        print("removing all the link files...")
        _traverse_nested_list_with_action(SERVICES, _remove_link_file)
        print("restore the .gitconfig file")
        _invoke(['cp ~/.gitconfig ~/.gitconfig.gittool'])
        _invoke(['mv ~/.gitconfig.gittool.backup ~/.gitconfig'])
        _exit()
    _ans = _get_answer(prompt = 'Would you like to setup GITTool? [y/N]', default = 'n',
                       help = 'This will simply create a bunch of symbol links for you.' +
                              '\nSo would you like to setup GITTool? [y/N]')
    if 'y' == _ans or 'Y' == _ans:
        _invoke(['cp ~/.gitconfig ~/.gitconfig.gittool.backup'])
        print("back up the original .gitconfig file")
        print("if your system supports colored text, you shall see them below:")
        for c in color.keys():
            print(color[c] + c + _end_)
        _ans = _get_answer(prompt = 'do you see the colors?[Y/n]', default = 'y')
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
                           help = "it will be used as the secondary tool when diff." +
                                  "\nleave it blank if you don't have a secondary diff tool")
        _set_global('difftool.second', _ans)
        _ans = _get_answer(prompt = "and your third choice of diff tool?",
                           help = "it will be used as the third tool when diff" +
                                  "\nleave it blank if you don't have a secondary diff tool")
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

#-------------------INTERNAL CLASSES-------------------
class Ball(object):
    """
    A ball is a carrier that holds the output of a git-tool helper function
    the carrier is able to perform certain operations on the data it holds.
    """
    def __init__(self, list, name = 'item'):
        self.list = list     #all the data will be stored in a list
        self.name = name
        self.help = "You can: \
          \n   Type the index of the %s or,\
          \n   Type the name for a new %s or,\
          \n   Use '/d <item_index>' to delete an %s or,\
          \n   Use '/e' to quit" % (self.name, self.name, self.name)
    def __getitem__(self, k):
        return self.list[k]
    def get_list(self):
        return self.list
    def get_indexed_list(self, highlight):
        return _index_list(self.list, highlight = highlight)
    def delete(self, item_list, func):
        item_list.sort(reverse=True) #remove the very last item in the list first
        for x in item_list:
            _result, _msg = func(self.list[x])
            if _result is True: #user might choose not to delete
                self.list.remove(self.list[x])
            print _msg

class BranchBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init(self, list):
        super(BranchBall, 'branch', self).__init__(list)
    def delete(self, item_list):
        super(BranchBall, self).delete(item_list, _delete_branch)

class HashBall(Ball):
    """
    A ball that holds a list of hash
    """
    def __init(self, list):
        super(HashBall, 'hash', self).__init__(list)
    def __getitem__(self, k): #return the hash only
        _firstline = self.list[k].split('\n')[0]
        return _firstline.split()[-1]
    def delete(self, item_list):
        _exit_with_error("Deleting a hash is not allowed")

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
            if _delete_source(self.list[x]) is True: #user might choose not to delete
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
def _get_answer(prefix = '', prompt = '', postfix = '', default = None,
                help = '', ball = None, hl = -1):
    if (ball and ball.help): # take the help if it is provided by the ball
        help += ball.help
    if not help: #no help is available
        help = 'No help available... '
        _ps = PROMPT_SIGN
    else: #show colored prompt if help is available
        _ps = color['lightblue'] + PROMPT_SIGN + _end_
    while True: #loop until we have an acceptable answer
        if ball: # when a ball is given, show the item list in the ball.
            _prompt = (prefix + '\n' if prefix else '') +\
                      '\n'.join(ball.get_indexed_list(highlight = hl)) + '\n' +\
                      (postfix + '\n' if postfix else '') + prompt
        else:
            _prompt = prompt
        _ans = raw_input(_prompt + _ps).strip(' ')
        if _ans == '/h':
            print(help)
        elif '/e' == _ans:
            _exit()
        elif _ans.startswith('/d '):
            if ball is None:
                _exit_with_error("no ball is passed while a delete is required")
            if re.search('^\/d\s+\d+([\s,-]+\d+)*\s*$', _ans): #space or ',' is used as separator
                #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
                _tmp = re.sub('\d+[\s]*-[\s]*\d+', _expand_indexes_from_range, _ans[3:])
                ball.delete([int(x.group()) for x in re.finditer('\d+', _tmp)]) #get all indexes
            else:
                _exit_with_error("to delete an item, try '/d <index>'")
        elif re.search('^\s*\d+\s*', _ans) and ball: #return the selected ball item
            return ball[int(_ans)]
        elif _ans or default: #this is a non-empty input, or default is set to allow direct Enter
            return _ans if _ans else default

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

#to fill the commit index in graphical commit tree
def _fill_commit_index(obj):
    global _commit_index
    _commit_index += 1
    return obj.group() + ' [' + str(_commit_index) + '] '

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
    return '[' + color['red'] + ver1 + _end_ + ']' + ' ==> ' +\
           '[' + color['red'] + ver2 + _end_ + ']'

def _merge_or_checkout():
    _ans = _get_answer(prompt = "Merge or Checkout? [m/C]", default = 'c')
    return 'm' if _ans == 'm' or _ans == 'M' else 'c'

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
    if ori:
        if cmd.startswith('git status'): #status code is given by git status
            return re.sub('^[MADRC ]{2}|\n[MADRC ]{2}', #replace space status code to '_'
                          lambda x : x.group().replace(' ', '_'),
                          ori)
        else: #status code is that diff-filter value when using git diff
            _pos = cmd.find('--diff-filter=') + len('--diff-filter=')
            _status = cmd[_pos]
            return re.sub('^|\n', #match the beginning of every line
                          lambda x: x.group() + _status + '  ',
                          ori)
    else:
        return ''

#-------------------branch helppers
#to find if a ref has a local storage
def _find_local_refs(ref):
    ref = ref[5:] #skip the 'refs/'
    _current_branch, _branch_list = _get_branch_list(isremote = True)
    for b in _branch_list:
        if ref == b:
            return b
    return None

#select a branch from list
def _select_branch(isremote = False):
    _curbranch, _branch_list = _get_branch_list(isremote)
    _listball = BranchBall(_branch_list)
    _ans = _get_answer(prefix = '--- Branch List ---', default = '/e',
                       ball = _listball, hl = _curbranch)
    if _ans == '/e': #user enters nothing, might think of quit
        _exit()
    return _branch_list, _ans

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
                       default = 'r',
                       help = "Merge will keep the history of changes but mix the local " +\
                              "changes with the merged changes; while Rebase keeps all " +\
                              "local changes together but modifies the change history " +\
                              "and make it hard to trace back. You shall determine which " +\
                              "strategy you would like to use, carefully.")
    _remote_branch = _get_remote_branch()
    if _ans == 'm' or _ans == 'M': #3a. merge
        return _do_remote(_remote_branch)
    else: #3b. rebase, which is recommended in many cases
        return _do_rebase(_remote_branch)
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

def _is_remote_branch(b):
    _url = _get_remote_url()
    return _invoke([git.lsremote(_url, b)])

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
                           default = 'n',
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

#-------------------functional blocks
def _do_log(range, format):
    return _invoke([git.log(hash = range, format = format, param = '--date=short')])

def _do_log_tag(range):
    _cmd = git.log(hash = range, format = '%ad|%h|%s|%d',
                   param = '--abbrev-commit --date=short')
    _logs = _split(_invoke([_cmd]), '\n')[:-1]
    _result = ''
    for _line in _logs:
        [_date, _hash, _comment, _tmp] = _line.split('|') if _line else ['', '', '', '']
        _tmp = _split(_tmp.strip(' ()'), ', ')
        _branch = _get_branches_with_commit(_hash)
        _container_tags = _invoke(["git tag --contains %s" % _hash])
        _container_tags = _split(_container_tags, '\n')
        if _container_tags:
            #the hash has tags attached, get the tags on this specific hash
            _tags = list(set(_tmp) & set(_container_tags))
            _result += '___\nRev: %s\nDate: %s\nBranch: %s\nComment: %s\nTags: %s\n' %\
                       (_hash, _date, _branch, _comment, _tags)
        else: #a hash without any tag
            _result += '___\nRev: %s\nDate: %s\nBranch: %s\nComment: %s\n' %\
                       (_hash, _date, _branch, _comment)
    return _result

_dot_file = '/tmp/gittool.dotty.tmp'
_svg_file = '/tmp/gittool.dotty.svg'
_commit_index = 0
def _do_log_graphic(num, hash_from, hash_to):
    if num != 0:
        _range = 'HEAD' + num * '^' + '..HEAD' + ' --ancestry-path'
    else:
        _range = 'HEAD'+ hash_to  * '^' + '..HEAD' + hash_from * '^' + ' --ancestry-path'
    #_format = '"%h" [label="<f0> %h|{<f1> %an|<f2> %cd}"]\n"%h":f0 -> {%p}'
    _format = """"%h" [label=<<TABLE>
                            <TR><TD ROWSPAN="2" PORT="f0" BGCOLOR="bisque"> %h</TD>
                                <TD>%an</TD></TR>
                            <TR><TD>%cd</TD></TR>
                            </TABLE>>]\n"%h":f0 -> {%p}
              """
    _result = _invoke([git.log(hash = _range, format = _format, param = '--date=short')])
    #link hashes with arrows
    _result = re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', _build_merge_arrows, _result)
    _result = 'digraph G{\nnode [shape=plaintext]\n'\
            + _result\
            + '}' #get data ready for dotty
    global _commit_index
    _commit_index = 0
    _result = re.sub('BGCOLOR="bisque">', _fill_commit_index, _result)
    with open(_dot_file, 'w') as f:
        f.write(_result)
    _tmp = _invoke(['dot -Tsvg %s > %s' % (_dot_file, _svg_file)])
    _cmd = ['qiv', _svg_file]
    return _invoke(_cmd, detached=True) #feed the data to dotty

def _do_rebase(from_ref):
    print("rebasing from %s ..." % from_ref)
    return _invoke([git.rebase()])

#merge branch, assuming frombr and tobr are valid branches
def _do_merge(from_ref, to_ref = None):
    if not to_ref:
        to_ref = _get_current_branch()
    #first check if the from ref is on the same branch of to_ref
    _refs = _invoke([git.branch(contains = from_ref)]).split('\n')
    for r in _refs:
        if to_ref == r.strip(' *'):
            _exit_with_error("I cannot merge %s to %s" % (from_ref, to_ref))
    print("merging from %s ..." % from_ref)
    if to_ref:#we need to first switch to the to ref
        _invoke([git.checkout(target = to_ref)]) #switch to the target branch
    _tmp = _invoke([git.merge(from_ref)]) #try auto merge
    if 'Automatic merge failed' in _tmp: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _tmp

#checkout a branch, or make a new branch and then check it out
def _do_checkout_branch(selected_branch, branch_list = None, isremote = False):
    if isremote: #to 'checkout' a remote branch is to fetch and make the branch local
        _do_fetch(selected_branch)
    if branch_list is None or selected_branch in branch_list: #this is an existing branch
        _tmp = _invoke([git.checkout(target = selected_branch)])
    else: #selected branch is not in the list
        _tmp = _make_branch(selected_branch)
    return _tmp

def _do_checkout_from_commit(ref):
    _new_branch = ''
    while not _new_branch: #force to input a name
        _new_branch = _get_answer(prompt = "Give a name to the new branch")
    return _invoke([git.checkout(target = ref, new_branch = _new_branch)])

def _do_apply(file):
    _tmp = _invoke([git.apply(file, check = True)])
    for line in _tmp.split('\n'):
        if 'does not apply' in line:
            _exit_with_error("Loading the patch failed. Check the patch file")
    return _invoke([git.apply(file)])

def _do_fetch(ref):
    _bname = ref[ ref.rfind('/') + 1: ] #get the branch name
    _local_ref = ref.replace('refs/', 'refs/remotes/', 1)
    _url = _get_local(section = 'branch.%s.remote' % _get_current_branch()) #assume the same url
    _result = _invoke([git.fetch(url = _url, src = ref, dst = _local_ref)])
    #make a branch tracking the ref, forcing the branch name to be the same as the remote
    _result += _make_branch_linked_to_ref(_bname, ref)
    return _result

def _do_clone():
    _source_list = _get_source_list('repo')
    _ball = SourceBall(_source_list, 'repo')
    _url = _get_answer(prompt = 'Pick a source to clone from', ball = _ball)
    return  _invoke([git.clone(_url)])

def _push_to_remote():
    _url = _get_remote_url()
    _ref = _get_remote_branch()
    if _url is None:
        _exit_with_error('config values are missing, you will need to manually fix this issue')
    else:
        _msg = 'push to ' + color['red'] + 'URL' + _end_ + ': ' + _url + '\n' +\
               '        ' + color['red'] + 'REF' + _end_ + ': ' + _ref + '\nOK? [Y/n]'
        _ans = _get_answer(prompt = _msg, default = 'y')
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

#-------------------hash helppers
#prompt the user a list of hashes and ask for a selected hash
def _select_hash(since = 7, until = 0):
    _group_size = since
    while True:
        #TODO: get rid of using the service function here.
        _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                {'num_of_log': abs(since - until) + 1,
                 'num_to_skip': min(since, until) - 1}
        _format='Rev:       %h%n\tDate:     %cd%n\tComment:  %s|'
        _tmp = _do_log(_range, _format)
        _ball = HashBall(_tmp.split('|\n')[:-1])
        _ans = _get_answer(default = 'more', ball = _ball,
                           help = '   Enter directly or "more" for more hashes, or\n' +
                                  '   "more <ID>" for further details of the hash, or\n')
        if _ans == 'more':
            until = since
            since += _group_size
        elif _ans.startswith('more'):
            _index = int(_split(_ans)[-1])
            print(_invoke([git.log(hash = _ball[_index], num = 1)]))
            raw_input('Press Enter to continue...')
        else:
            return _ans
        continue

def _select_hash_range(with_previous_hash = False):
    if with_previous_hash is True: #obtain the current and its previous hash
        _current_hash, _base_hash = _get_hashes(2)
    else: #get the hashes given by the user
        print("[+] Select the" + color['red'] + " start " + _end_ + 'hash')
        _base_hash = _select_hash(since = 4)
        print("[+] Select the" + color['red'] + " end " + _end_ + 'hash')
        _current_hash = _select_hash(since = 4)
    return _base_hash + '..' + _current_hash

#get file differences between two hashes
def _get_hash_change(with_previous_hash = False):
    _hash_str = _select_hash_range(with_previous_hash)
    #list all changed files
    _file_list = _invoke([git.diff(selection = _hash_str, name_only = True)])
    print(_file_list)
    _tmp = _get_answer(prompt = 'Are the files that you changed? [y/N]', default = 'n')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _hash_str

#get the current hash string
def _get_hashes(num):
    _hash_str = _invoke([git.log(num = num, format = '%h')])
    return _split(_hash_str, '\n')[:-1] #get rid of the last empty line

#check if a hash exists
def _if_hash_exist(ver):
    _tmp = _invoke([git.revparse(hash = ver)])
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

def _number_of_changed_files(_hashes = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = _invoke([git.diff(selection = _hashes if _hashes else _remote_branch, name_only = True)])
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
    elif item.strip().startswith('??'): #the file is out of hash control
        _invoke(['rm ' + _file])
    elif item.strip().startswith('*'): #the file status is unknown other than 'changed'
        _exit_with_error("don't know how to revert %s" % _file)
    else:
        _exit_with_error('oops, error when reverting file: %s' % item)
    return True, '%s reverted' % _file
    #TODO: what to do if file is commited, but need to delete from a diff list
    #   this means we need to copy a specified hash to overwrite

def _remove_link_file(x):
    _fullpath = sys.argv[0]
    _dir = _fullpath[:_fullpath.rfind('/') + 1]
    _invoke(['rm %s' % (_dir + x)])

#a list of services provided to the user, via symbolic links
SERVICES = [ 'gsv',
             'gld', 'gldr', 'gldb', 'gldh', 'gldt',
             'gst',
             ['gst' + x for x in allperm('dr')], #combination of 'd', 'r'
             ['gst' + x for x in allperm('br')], #combination of 'b', 'r'
             'gcf',
             'gls', 'glst', 'glsg',
             'gdi',
             [ 'gdi' + x for x in allperm('2rh')], # combination of 'r','h','2'
             [ 'gdi' + x for x in allperm('3rh')], # combination of 'r','h','3'
             'ghelp' ]

CALL_TABLE = { 'gst': GITStatus,
               'gls': GITList,
               'gsv': GITSave,
               'gld': GITLoad,
               'gdi': GITDiff,
               'gcf': GITConfig}

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
    try:
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
    except ConfigItemMissing:
        _exit_with_error("There are item or section missing in the config file")
