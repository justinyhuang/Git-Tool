#!/usr/bin/python -W ignore::DeprecationWarning
"""
Git-Tool - a utility set for easier use of git

Available services:
   gsv: Git SaVe, to 'save' your changes
   gld: Git LoaD, to 'load' new data as/into current working copy
   gdi: Git DIff, compare file/s between commits/branches
   gst: Git STatus, list modified/added/removed files between hashes/branches
   gls: Git List, shows basic information of the current hash
   gcf: Git ConFig, shows the global settings and configuration of the working copy.
   ghelp: help info for GITUtil
Dependencies (please install):
   git: Git-Tool is a wrapper of git
   graphviz and qiv: Git-Tool needs both to show graphical hash tree via glsg
"""
import os
import re
import sys
import pdb
import subprocess
import gitcommand as git
from githelper import *
from optparse import OptionParser

"""
TODO: when a branch name is origin, we should not name the linked 'remote' section to 'origin'!!
TODO: we need a solid config file to make sure git-tool is correctly working. fix potential issues.
TODO: add functionality to support 'save' some files and keep other files uncommitted.
TODO: need to consider the situation when the tool is used without a network connection: we will need to skip the checking of remote branches/repo's
TODO: add the path of git-tool bin directory to PATH and the path of git-tool python files to PYTHONPATH, in gitsetup
TODO: when there are a long list of remote branches, how would a user pick one easily?
TODO: check files in /usr/lib/git-core in workstation and see how to enable write permission when doing vimdiff
"""

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
    _current_branch = get_current_branch()
    if len(param) > 1 and os.path.isfile(param[1]): #user ask for generating a patch
        if len(param) == 3: #both hash string and the file name is given
            _hash_str, _patch_file = param[1], param[2]
        else: #only file name is given, help him to pick two hashes
            _patch_file = param[1]
            _file_list, _hash_str = get_hash_change()
            print(_file_list)
            _ans = get_answer(prompt = 'Patch the change in these files? [y/N]', default = 'n')
            if _ans is 'N' or _ans is 'n':
                exit()
        _tmp = invoke([git.patch(selection = _hash_str, patch_file = _patch_file)])
        _ans = get_answer(prompt = 'where to store %s ?' % _patch_file)
        _target_dir=os.path.expanduser(_ans)
        if not os.path.isdir(_target_dir):#directory doesn't exist, try to make one
            os.makedirs(_target_dir)
        invoke(['mv %s %s' % (_patch_file, _target_dir)])
        return '\npatch saved to %s/%s' % (_target_dir, _patch_file)
    else: #do a push or a commit
        if num_uncommited_files(): #there are changed files to commit
            _msg = get_answer(prompt = 'Any comment? [empty comment is not allowed]')
            _msg = '"' + _msg + '"'
            _ans=get_answer(prompt = 'Save to ' +\
                            paint('red', _current_branch) + ' ? [Y/n]',
                            default = 'y')
            if _ans == 'n' or _ans == 'N':
                _branch_list, _branch = select_branch()
                do_checkout_branch(selected_branch = _branch, in_list = False)
            invoke([git.commit(' -a -m %s' % _msg)])
            return "Done"
        else: # there is no changed files, try a push
            return push_to_remote()

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
              When 'gld <file_name> <hash_name>' in a git path, 'gld' will load the file
              from the given hash.

        When not sure about the branch/hash/tag/file, use:
            * gldb - to pick a branch from a list and do a checkout or merge.
            * gldr - to fetch/merge a remote branch picked from list
            * gldh - to pick a hash (a.k.a commit/hash) from a list and do a checkout or merge
            * gldt - to pick a tag from list and do a checkout or merge [NOT IMPLEMENTED]
            * gldf - to load a file/files from a given hash

        Do 'gld ?' to show this help message.
    """
    _ifremote = 'r' in srv
    _ifbranch = 'b' in srv or _ifremote #when 'r' is given, 'b' automatically becomes True
    _ifhash = 'h' in srv
    _iftag = 't' in srv
    _iffile = 'f' in srv
    if not root_path(): #in a non-git path, do a clone (nothing else we could do, right?)
        if _ifbranch or _ifremote or _ifhash or _iftag:
            exit_with_error("You need to run the command in a git repo")
        _result = do_clone()
    else: #in a git path
        _curbranch = get_current_branch()
        if len(param) == 2: #something is provided as the parameter
            _in_branch_list = param[1] in get_branch_list()[1]
            if _ifbranch or _in_branch_list: #this is a local branch, or the user says so
                _result = merge_or_checkout(param[1], _in_branch_list)
            if _iftag: #user says it is a tag
                _result = do_checkout_from_commit(param[1])
            if _ifremote: #user says it is a remote branch
                _result = do_fetch(ref = param[1])
            #is this a remote branch?
            _remote_branch = is_remote_branch(param[1])
            if _remote_branch: #yes we find it
                _result = do_fetch(ref = param[1])
            #TODO: can we support merging from a remote branch?
            if os.path.isfile(param[1]): #this is a patch file
                _result = do_apply(param[1])
            else: #the last possibility is...tag, try with fingers crossed...
                _ans = get_answer(prompt = "Is %s a tag? [y/N]" % param[1])
                if _ans == 'y' or _ans == 'Y':
                    _result = do_checkout_from_commit(param[1])
                else:
                    exit_with_error("Don't know how to load [%s]" % param[1])
        elif len(param) == 3: #to load a file from a hash
            if os.path.isfile(param[1]):
                _checkout_file, _checkout_hash = param[1], param[2]
            else:
                _checkout_file, _checkout_hash = param[2], param[1]
            do_checkout_file_from_commit([_checkout_file], _checkout_hash)
            _result = 'done'
        else: #no parameter is given.
            if _ifbranch: #this is a branch thing
                _branch_list, _branch = select_branch(_ifremote)
                if _ifremote:# fetch from remote
                    _result = do_checkout_branch(selected_branch = _branch,
                                              in_list = _branch in _branch_list,
                                              isremote = _ifremote)
                else: #it is a local branch
                    _result = merge_or_checkout(target = _branch,
                                             in_list = _branch in _branch_list)
            elif _ifhash: #checkout a hash to a new branch
                _hash = select_hash()
                _result = merge_or_checkout(target = _hash, in_list = False)
            elif _iftag: #checkout a tag to a new branch
                exit_with_error("This feature is not supported, yet")
            elif _iffile: #checkout file/s from a hash
                #promp to pick a hash
                _changed_files, _hash_str = get_hash_change(with_previous_hash = True)
                _load_hash = _hash_str.split('..')[0]
                #prompt to pick files
                _ball = FileBall(_changed_files.split('\n'))
                _load_files = get_answer(title = ' File List ',
                                         prompt = 'Select files to save: ',
                                         ball = _ball)
                do_checkout_file_from_commit(_load_files, _load_hash)
                _result = 'done'
            else: # if i have to guess, i will try updating the repo
                _ans = get_answer(prompt = "Update current repository? [Y/n]",
                                  default = 'y',
                                  help = "after the update, you can choose to either" +
                                         "merge or rebase your local changes")
                if _ans != 'n' and _ans != 'N':
                    update_local_branch()
                    _result = "done"
                else:
                    exit_with_error("Please tell me more. You know I don't know what you know :(")
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

        'gdic' with or without other options shows a combined diff result.
    """
    check_git_path()
    _isremote, _ishash, _iscombined = ('r' in srv), ('h' in srv), ('c' in srv)
    _difftool = _file = _hashes = _remote_branch = ''
    #look for the user preferred diff tool
    if '2' in srv:
        _difftool = get_global('difftool.second')
    elif '3' in srv:
        _difftool = get_global('difftool.third')
    if not _difftool: #try to get the default diff tool in this case
        _difftool = get_global('difftool.first')
    if _isremote: #handle remote diff operation
        _remote_branch = get_remote_branch()
    else: #handle non-remote diff
        for x in param[1:]: #looking for any hash info
            if re.search('^[0-9a-fA-F]+\.\.[0-9a-fA-F]+$', x) is not None:
                _hashes = x #this seems like a <hash>..<hash> string
                break
            if re.search('^[0-9a-fA-F]+$', x):
                if if_hash_exist(x): #this seems like a <hash> string
                    _curhash = get_hashes(1)[0]
                    _hashes = _curhash + '..' + x #make up the hash string
                    break
                else:
                    continue #cannot find the hash, keep checking the rest params
        if _ishash and not _hashes: #allow user to select hashes on the fly
            _hashes = select_hash_range()
    for x in param[1:]:
        if os.path.isfile(x): #the file exist
            _file = x
            break
    if _iscombined:
        _cmd = git.show(selection = _hashes, param = '-m --pretty=short', file = _file)
    else:
        _cmd = git.difftool(_difftool, _hashes, _remote_branch, _file)
    #if there are too many files, warn the user before doing diff
    _num = number_of_changed_files(_hashes, _remote_branch, _file)
    if _num > 7: # i guess 7 is a good limit
        _ans = get_answer(prompt = 'are you sure to diff about ' +
                                   paint('red', '%d' % _num) +
                                   ' files?[y/N]', default = 'n')
        if _ans != 'y' and _ans != 'Y':
            exit()
    #for vim it appears we need to invoke it via os.system to make it work correctly
    if _difftool == 'vimdiff':
        os.system(_cmd)
    else:
        _tmp = invoke([_cmd])
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
    check_git_path()
    _isdir, _isremote, _ishash = ('d' in srv), ('r' in srv), ('h' in srv)
    _compare_str = param[1] if len(param) > 1 else ''
    _cmds, _status = list(), ''
    if _isremote: #comparing with the remote branch
        #first fetch the latest copy, and compare locally
        print("comparing with the remote repository, please wait...")
        _remote = get_local('branch.%s.remote' % get_current_branch())
        do_fetch(url = _remote)
        _compare_str = '%s..%s' % (get_current_branch(), get_remote_branch())
    elif _ishash:
        _compare_str = select_hash_range()
    if _compare_str:#with comparison objects specified, use 'git diff'
        for t in 'ACDMRTUXB':#diff with different diff filter to get the change's type
            _cmds.append(git.diff(selection = _compare_str, type = t))
    else:# without comparison objects specified, use 'git status'
        _cmds.append(git.status(param = '-s'))
    for c in _cmds:
        if _isdir: #only show the touched files in the current directory
            c += ' -- ' + os.getcwd()
        _tmp = invoke([c])
        _tmp = translate_status_code(c, _tmp)
        _status += _tmp[:_tmp.rfind('\n')] + '\n' if _tmp else ''
    _final_str = '' # prepare for a prettified outcome
    if _compare_str:#show changed files between two commits
        if '..' in _compare_str: #two compare candidates are given
            _comp1, _comp2 = split(_compare_str, '..')
        else:
            if if_branch_exist(_compare_str): #only one candidate given, which is a branch
                _comp2, _comp1 = _compare_str, get_current_branch()
            elif 'unknown revision' in _status: #something wrong with the given candidate
                exit_with_error('unknown hash/branch, please check')
            else:#assume this is comparison between hashes
                _comp1, _comp2 = _compare_str, get_hashes(1)[0]
            if num_uncommited_files(): #show 'working copy' if there is any local change
                _comp2 = 'working copy'
        if not _status or not _status.strip(' '):
            _status = '' #there is no changes found
            _changes = 0
        else:
            _changes = len(split(_status, '\n')) - 1
        _changed = split(_status, '\n')[:-1]
        _untracked= []
    else: #show changed but not yet commited files, with indexes added
        _changed, _untracked= get_changed_files(_status)
        _changes = len(_changed)
        _comp1, _comp2 = get_current_branch(), 'working copy'
    _files = FileBall(_changed + _untracked)
    _ans = get_answer(title = make_status_header(_comp1, _comp2),
                      prompt = '',
                      default = '/e',
                      help = _git_status_code,
                      ball = _files)
    return ''

def GITList(srv, param):
    """
    gls
    To show a list of commits with the information of:
        * hash, author, date and comment.
          'gls <n>' shows n latest commits' info.
          When no parameter is given, shows that of the latest commit.
          'gls <since index> <until index>' shows all the commits
          between the two indexes.
          e.g 'gls 3 0' shows the commits from HEAD to the 3rd parent of HEAD
              'gls 7 4' shows the commits from the 4th parent to the 7th parent of HEAD
        * hash, author, date, comment, branch and tag.
          'glst <n>' or 'glst <since index> <until index>'
          shows more information including branches and tags, if there is any.
          However, fetching the tag info would take a bit more time.
        * hash, committer and date in graphics.
          'glsg <n>' or 'glsg <since index> <until index>'
          shows a graphical commit tree.
          *NOTE*: graphviz and qiv is required to enable the 'g' option
        * hash, author, date and comment only from the given author.
          'glsa <n>' or 'glsa <since index> <until index>'
        * hash, author, date and comment during a period
          'glsd' with or without other parameters
    """
    check_git_path()
    _if_graphic, _if_show_tag = ('g' in srv), ('t' in srv)
    _if_author, _if_date = ('a' in srv), ('d' in srv)
    _since = _until = _num = 0
    if _if_author:
        _max_param = 4
        _author = param[1]
    else:
        _author = ''
        _max_param = 3
    if len(param) == _max_param: #start and end of a hash segment is given.
        _since, _until  = int(param[_max_param - 2]), int(param[_max_param - 1])
    elif len(param) == _max_param - 1: #the number of hashes is given.
        _num = int(param[_max_param - 2])
    else: #default, show the latest hash info
        _num = 1
    if _if_graphic:
        do_log_graphic(_num, _since, _until)
        return ''
    else:
        _format='___%nRev:       %h%nAuthor:    %an%nDate:      %cd%nComment:   %s'
        if _num != 0:
            _range = '-%d' % _num
        else:
            _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                    {'num_of_log': abs(_since - _until) + 1,
                     'num_to_skip': min(_since, _until) - 1}
        if _if_show_tag: #show the tag info
            print("this will take a while...")
            _result = do_log_tag(_range)
        elif _if_author or _if_date: #only show logs of given author
            _result = do_log_author_or_date(_if_author, _if_date, _format,  _range, _author)
        else:
            _result = do_log(_range, _format)
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
            set_local(section = param[2], value = param[3])
        elif param[1] == 'global': #set global value
            set_global(section = param[2], value = param[3])
    #local settings
    if root_path():
        _current_branch = get_current_branch()
        _current_branch_remote = get_local('branch.%s.remote' % _current_branch)
        _current_branch_merge = get_local('branch.%s.merge' % _current_branch)
        _remote_branch = get_remote_branch(show_remote_path = True)
        _repo_url = get_remote_url()
    else:
        _current_branch = _current_branch_remote = \
        _current_branch_merge = _remote_branch = None
    #global settings
    _email = get_global('user.email')
    _username = get_global('user.name')
    _first_diff_tool = get_global('difftool.first')
    _second_diff_tool = get_global('difftool.second')
    _third_diff_tool = get_global('difftool.third')
    #make up the output
    _ret = ""
    _ret += "current branch is %s\n" % _current_branch
    _ret += "remote branch is %s\n" % _remote_branch
    _ret += "remote repository url is %s\n" %  _repo_url
    _ret += paint('yellow', "---Local Settings---\n")
    _ret += "branch.%s.remote: %s\n" % (_current_branch, _current_branch_remote)
    _ret += "branch.%s.merge: %s\n" % (_current_branch, _current_branch_merge)
    _ret += paint('yellow', "---Global Settings---\n")
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
        traverse_nested_list_with_action(SERVICES, remove_link_file)
        print("restore the .gitconfig file")
        invoke(['cp ~/.gitconfig ~/.gitconfig.gittool'])
        invoke(['mv ~/.gitconfig.gittool.backup ~/.gitconfig'])
        exit()
    _ans = get_answer(prompt = 'Would you like to setup GITTool? [y/N]', default = 'n',
                       help = 'This will simply create a bunch of symbol links for you.' +
                              '\nSo would you like to setup GITTool? [y/N]')
    if 'y' == _ans or 'Y' == _ans:
        invoke(['cp ~/.gitconfig ~/.gitconfig.gittool.backup'])
        print("back up the original .gitconfig file")
        print("if your system supports colored text, you shall see them below:")
        for c in color.keys():
            print(paint(c, c))
        _ans = get_answer(prompt = 'do you see the colors?[Y/n]', default = 'y')
        if _ans == 'n' or _ans == 'N':
            set_global('GitTool.ColorSupport', 'no')
        else:
            set_global('GitTool.ColorSupport', 'yes')
        #setup the difftools
        print("Valid merge tools are: araxis, bc3, diffuse, emerge, ecmerge, gvimdiff, kdiff3," +
              "kompare, meld, opendiff, p4merge, tkdiff, vimdiff and xxdiff.")
        _ans = get_answer(prompt = "Please specify your first choice of diff tool:",
                           help = "it will be used as the default tool when diff")
        set_global('difftool.first', _ans)
        _ans = get_answer(prompt = "and your second choice of diff tool?",
                           help = "it will be used as the secondary tool when diff." +
                                  "\nleave it blank if you don't have a secondary diff tool")
        set_global('difftool.second', _ans)
        _ans = get_answer(prompt = "and your third choice of diff tool?",
                           help = "it will be used as the third tool when diff" +
                                  "\nleave it blank if you don't have a secondary diff tool")
        set_global('difftool.third', _ans)
        #set the graphic info tool settings
        #setup the symbolic links
        print("Please specify where you would like to put the GITTool facilities")
        print("[eg. '~/bin/GTool', '/tools']")
        print("\nMake sure the path is in your PATH variable")
        _ans = get_answer(help = "The GitUtilTool works based on" +
                                  paint('red', " A LOT OF ") + "small link files\n" +
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
                    invoke(["ln -s %(source)s %(link)s" %
                            {'source' : _source, 'link' : _target_dir + '/' + sub_service}])
            else:
                invoke(["ln -s %(source)s %(link)s" %
                        {'source' : _source,
                         'link' : _target_dir+'/'+service}])
        print("done.\ntry ghelp for more info")

#a list of services provided to the user, via symbolic links
SERVICES = [ 'gsv',
             'gld', 'gldr', 'gldb', 'gldh', 'gldt', 'gldf',
             'gst',
             ['gst' + x for x in allperm('dr')], #combination of 'd', 'r'
             ['gst' + x for x in allperm('br')], #combination of 'b', 'r'
             'gcf',
             'gls', 'glst', 'glsg',
             ['gls' + x for x in allperm('ad')], #combination of 'a', 'd'
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
    invoke(['export','LANG=en_US.UTF-8'])
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
                exit()
            try:
                result = CALL_TABLE[service[:3]](service[3:], sys.argv)
                print(result)
            except KeyError: #if no available service is found, try to install git-tool
                GITSetup(sys.argv)
    except Exception, err:
        sys.stderr.write('ERROR: %s\n' % str(err))
