import gitcommand as git
import subprocess
import pdb
import os
import sys
import re

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
        return index_list(self.list, highlight = highlight)
    def add(self, item_list, func): #children will take care of the implementation
        pass
    def delete(self, item_list, func):
        item_list.sort(reverse = True) #remove the very last item in the list first
        for x in item_list:
            _result, _msg = func(self[x], self.name)
            if _result is True: #user might choose not to delete
                self.list.remove(self[x])
            print _msg

class BranchBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init__(self, list, name = 'branch'):
        super(BranchBall, self).__init__(list, name)
    def delete(self, item_list):
        super(BranchBall, self).delete(item_list, delete_branch)

class HashBall(Ball):
    """
    A ball that holds a list of hash
    """
    def __init__(self, list, name = 'hash'):
        super(HashBall, self).__init__(list, name)
    def __getitem__(self, k): #return the hash only
        _firstline = self.list[k].split('\n')[0]
        return _firstline.split()[-1]
    def delete(self, item_list):
        exit_with_error("Deleting a hash is not allowed")

class FileBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init__(self, list, name = 'file'):
        super(FileBall, self).__init__(list, name)
    def add(self, item_list): #to add a file into git
        for i in item_list:
            item = self.list[i]
            if item.strip().startswith('??'): #not in git's control
                #add the file into git
                _file = item[item.rfind(' ') + 1:]
                invoke(git.add(_file))
                self.list[i] = re.sub('\?\?', 'A_', self.list[i])
    def delete(self, item_list):
        super(FileBall, self).delete(item_list, revert_file_item)

class UrlSourceBall(Ball):
    """
    A ball that holds and manages a list of url sources
    """
    def __init__(self, list, name = 'url'):
        self.dict = {}
        _list = []
        for l in list:
            _name, _count = l.split() # expected string is "url_name linked_ref_count"
            _list.append(_name)
            self.dict[_name] = int(_count)
        super(UrlSourceBall, self).__init__(_list, name)
    def delete(self, item_list):
        for i in item_list:
            if self.dict[self[i]] > 0: #there are still refs linked to this url
                print("There are still references linked to this URL. Deletion Denied.")
                item_list.remove(i) #skip deleting the source item
        super(UrlSourceBall, self).delete(item_list, delete_source)

class RefSourceBall(Ball):
    """
    A ball that holds and manages a list of ref sources
    """
    def __init__(self, list, name = 'Ref Source'):
        self.dict = {}
        _list = []
        for r in list:
            _ref, _url_index = r.split() #expected string is 'ref url_index'
            _list.append(_ref)
            self.dict[_ref] = _url_index
        super(RefSourceBall, self).__init__(_list, name)
    def delete(self, item_list):
        for i in item_list:
            #first decrease the ref count of the linked url item
            _url_index = self.dict[self[i]]
            _url = get_global('sourcelist.url.item%s' % _url_index)
            _ref_count = int(_url.split()[1]) #TODO: what about the count is 0 here?
            set_global('sourcelist.url.item%d' % (_ref_count - 1))
        super(RefSourceBall, self).delete(item_list, delete_source)

class RemoteSourceBall(Ball):
    """
    A ball that holds and manages a list of remote section
    The input list to this ball object needs to follow the format below:
        remote.<name1>.<fetch/url> value
        remote.<name1>.<url/fetch> value
        remote.<name2>.<fetch/url> value
        remote.<name2>.<url/fetch> value
        ...
    """
    def __init__(self, list, name = 'Remote Source'):
        self.dict = {}
        _list = []
        for r in list[:-1]:
            _name_begin = 7 #skip the 'remote.'
            _tmp = r.split()[0]
            #the line is either a fetch or a url setting
            if _tmp.rfind('.fetch') != -1: #it's a fetch setting
                _name_end = -6 #location of '.fetch'
                _key = 'fetch'
            else: #it's a url setting
                _name_end = -4 #location of '.url'
                _key = 'url'
            _value = r.split()[1]
            _name = _tmp.strip(' \n')[_name_begin:_name_end]

            if not self.dict.has_key(_name):
                self.dict[_name] = {}
            self.dict[_name][_key] = _value
        for k in self.dict.keys():
            _list.append( k + '\n\tfetch: ' + self.dict[k]['fetch']
                            + '\n\turl: ' + self.dict[k]['url'])
        super(RemoteSourceBall, self).__init__(_list, name)


class GITError(Exception):
    """base class of all GitTool error exceptions"""
    def __init__(self, msg):
        self._msg = """General Error. Sorry I don't have too much to say..."""
    def complain(self):
        raise RuntimeError(self._msg)

class ConfigItemMissing(GITError):
    def __init__(self):
        self._msg = "The item/section in the git config file does not exist"

class UnsupportedOperation(GITError):
    def __init__(self):
        self._msg = "The operation is not supported, yet"

class NoBallFound(GITError):
    def __init__(self):
        self._msg = "The operation needs a ball but nothing is found"

#-------------------INTERNAL HELPPER FUNCTIONS-------------------
#The internal helpper functions are used by the service functions.
#Based on git direct call functions, the helpper functions fulfill certain git-tool sub features.
#No direct git command calls will be made in these functions.

def paint(text_color, str):
    return color[text_color] + str + _end_

#-------------------basic and misc helppers
#the services provided by the git tool box, used for creating the links
## {{{ http://code.activestate.com/recipes/577842/ (r1)
def allperm(inputstr):
    for i in range(len(inputstr)):
        yield(inputstr[i])
        for s in allperm(inputstr[:i] + inputstr[i+1:]):
            yield(inputstr[i] + s)
## end of http://code.activestate.com/recipes/577842/ }}}

def split(str, sep = None):
    return str.split(sep) if str else []

#invoke bash commands
def invoke(cmd, detached = False, need_error_and_out = False):
    if DEBUG == True: #for debug only
        print('>>> %s <<<' % cmd)
    if detached is False:
        execution=subprocess.Popen([cmd],
                                   shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        o=execution.communicate()
        if need_error_and_out: #return both stdout and stderr
            return o[0], o[1]
        else:
            if o[1]: #return error if there is any
                return o[1]
            if o[0]: #only return the std result, when there is no error
                return o[0]
    else: #invoke bash commands in separate process, no error return
        subprocess.Popen(cmd.split(), stderr=subprocess.PIPE)
    return ""

def get_indexes(line, operator = ''):
    #space, '-' or ',' is used as separator
    if re.search('^' + operator + '\d+([\s,-]+\d+)*\s*$', line):
        #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
        _tmp = re.sub('\d+[\s]*-[\s]*\d+', expand_indexes_from_range, line[len(operator):])
        return [int(x.group()) for x in re.finditer('\d+', _tmp)] #get all indexes
    else:
        return None

#helper function to prompt users information and receive answers
#this function returns either a list or a string, the caller should understand well
#what the return value could be and handle accordingly
def get_answer(title = '', prompt = '', postfix = '', default = None,
               help = '', ball = None, hl = -1):
    if (ball and ball.help): # take the help if it is provided by the ball
        help += ball.help
    if not help: #no help is available
        help = 'No help available... '
        _ps = PROMPT_SIGN
    else: #show colored prompt if help is available
        _ps = paint('lightblue', PROMPT_SIGN)
    while True: #loop until we have an acceptable answer
        if ball: # when a ball is given, show the item list in the ball.
            _prompt = make_msg_bar(title)
            _prompt += '\n'.join(ball.get_indexed_list(highlight = hl)) + '\n' +\
                       (postfix + '\n' if postfix else '') + prompt
        else:
            _prompt = prompt
        _ans = raw_input(_prompt + _ps).strip()
        if '/h' == _ans:
            print(help)
        elif '/e' == _ans:
            exit()
        elif _ans.startswith('/d '):
            if ball is None:
                NoBallFound.complain()
            _d_list = get_indexes(operator = '/d ', line = _ans)
            if _d_list:
                ball.delete(_d_list)
            else:
                exit_with_error("to delete an item, try '/d <index>'")
            #update the highlighted item
            for x in _d_list:
                if x < hl:
                    hl -= 1
        elif _ans.startswith('/a '):
            if ball is None:
                NoBallFound.complain()
            _a_list = get_indexes(operator = '/a ', line = _ans)
            if _a_list:
                ball.add(_a_list)
            else:
                exit_with_error("to add an item, try '/a <index>'")
            #update the highlighted item
            for x in _a_list:
                if x < hl:
                    hl += 1
        elif _ans == 'more':
            return ['more']
        elif ball:
            _list = get_indexes(line = _ans)
            if _list:
                _items = []
                for i in _list:
                    _items.append(ball[i])
                return _items
            elif _ans or default: #this is a non-empty input, or default is set to allow direct Enter
                return _ans if _ans else default
        else:
            return _ans if _ans else default

#show a list of items with index and one of the item highlighted
def index_list(list, index_color = 'none', highlight = -1, hl_color = 'red'):
    return [ paint(hl_color if index == highlight else index_color, '%d >> ' % index) +
             '\t' + x for (index, x) in zip(range(0, len(list)), list)]

#this function will expand strings like '1-3' to '1 2 3'
def expand_indexes_from_range(obj):
    _tmp = ''
    _line = obj.group()
    _range = split(_line, '-')
    for x in range(int(_range[0]), int(_range[1]) + 1):
        _tmp += ' %d ' % x
    return _tmp

#used in re.sub to fill the commit index in graphical commit tree
def fill_commit_index(obj):
    global commit_index
    commit_index += 1
    return obj.group() + ' [' + str(commit_index) + '] '

#used in re.sub to modify the matching string and link nodes with arrows
def build_merge_arrows(obj):
    _tmp = ''
    _line = obj.group()
    _from = _line[1:8]
    _list = re.findall('[a-f0-9]{7}', _line[7:])
    for x in _list:
        _tmp += '"%(v)s":f0 -> "%(f)s":f0 [color=blue style=bold arrowhead=vee]\n' %\
                {'f':_from, 'v':x}
    return _tmp

#print the header of status result
def make_status_header(ver1, ver2):
    return '[' + paint('red', ver1) + ']' + ' ==> ' +\
           '[' + paint('red', ver2) + ']'

def merge_or_checkout(target, in_list, default_op = ''):
    if default_op == '':
        default_op = get_answer(prompt = "Merge or Checkout? [m/C]", default = 'c')
    if default_op.lower() == 'm': #merge
        return do_merge(target)
    else: #checkout
        return do_checkout_branch(target, in_list)

#print message with a fixed length bar
def make_msg_bar(msg):
    _colorless_msg = msg
    _colorless_msg = re.sub('\033[^m]*m', '', _colorless_msg) #remove the color code
    _msg_len = len(_colorless_msg)
    _pre = paint('yellow', '=' * ((80 - _msg_len) / 2))
    _post = paint('yellow', '=' * ((80 - _msg_len) / 2 + (80 - _msg_len) % 2))
    return _pre+msg+_post+'\n'

#exit with error
def exit_with_error(msg = ''):
    print("Exit with error :\n" + msg)
    sys.exit()

def exit():
    sys.exit()

#do something by traversing the given nested list
def traverse_nested_list_with_action(lst, action):
    for x in lst:
        if isinstance(x, list):
            traverse_nested_list_with_action(x, action)
        else:
            action(x)

# translate the output of git status -s into git-tool's format
def translate_status_code(cmd, ori):
    if ori:
        if cmd.startswith('git status'): #status code is given by git status
            return re.sub('^[MADRCTUXB ]{2}|\n[MADRCTUXB ]{2}', #replace ' ' status code to '_'
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
#select a branch from list
#Returns: the complete branch list,
#         the selected branch/es, (COULD BE A BRANCH LIST)
def select_branch(isremote = False):
    _curbranch, _branch_list = get_branch_list(isremote)
    _listball = BranchBall(_branch_list, name = 'remote branch' if isremote else 'branch')
    _ans = get_answer(title = ' Branch List ', default = '/e',
                      ball = _listball, hl = _curbranch)
    if _ans == '/e': #user enters nothing, might think of quit
        exit()
    if isinstance(_ans, str): #guarantee that we always return a list of selected branches
        _ans = [_ans]
    return _branch_list, _ans

def make_branch(branch):
    _parent_branch = get_current_branch()
    _parent_remote = get_remote(_parent_branch)
    _tmp = invoke(git.branch(branch = branch)) #create branch with the name given
    _tmp = do_checkout_branch(target = branch)
    _result = 'created and switched to new branch: ' + paint('red', branch) + '\n'
    _result += invoke(git.branch(branch = branch,
                                 upstream = _parent_remote + '/' + _parent_branch))
    return _result

#based on the remote and fetch values of the parent, set up the values for the new branch
def link_branch_to_ref(bname, cur_branch, ref, local_ref, repo = ''):
    try:
       _remote = get_remote(cur_branch)
       _repo = repo if repo\
                    else get_local('remote.%s.url' % _remote)
    except ConfigItemMissing:
        exit_with_error("config item is missing, please report to the developer so that we can fix it!")
    _fetch = '+%s:%s' % (ref, local_ref)
    #set up a new remote section and a new branch section for this new branch
    set_local('remote.%s.url' % bname, value = _repo)
    set_local('remote.%s.fetch' % bname, value = _fetch)
    set_local('branch.%s.remote' % bname, value = bname)
    #set_local('branch.%s.merge' % bname, value = local_ref)
    set_local('branch.%s.merge' % bname, value = ref)
    # i am not sure about this, but look at the example of master branch,
    # the merge value for master branch is the remote path in the fetch section: +xx:

def get_branches_with_commit(hash):
    _cmd = git.branch(contains = hash)
    return [x.strip(' *') for x in split(invoke(_cmd), '\n') if x]

def update_local_branch():
    #1. fetch the updates from remote repo
    try:
       _current_branch = get_current_branch()
       _remote = get_remote(_current_branch)
    except ConfigItemMissing:
        exit_with_error("config item is missing, please report to the developer so that we can fix it!")
    print("fetching from %s ..." % _remote)
    print(invoke(git.fetch()))
    #2. ask for option
    _ans = get_answer(prompt = "fetch completes, shall we Merge or Rebase? (m/R)",
                      default = 'r',
                      help = "Merge will keep the history of changes but mix the local " +\
                             "changes with the merged changes; while Rebase keeps all " +\
                             "local changes together but modifies the change history " +\
                             "and make it hard to trace back. You shall determine which " +\
                             "strategy you would like to use, carefully.")
    _remote_branch = get_remote_branch()
    if _remote_branch is None:
        exit_with_error("ERROR: Cannot find the remote branch in your config file")
    if _ans.lower() == 'm': #3a. merge
        return do_merge(_remote_branch)
    else: #3b. rebase, which is recommended in many cases
        return do_rebase(_remote_branch)
    #TODO: there is yet another option, see the better (and more complicated) rebase at
    # http://softwareswirl.blogspot.com/2009/04/truce-in-merge-vs-rebase-war.html

#get a branch list. returns <master branch index>, <branch list>
def get_branch_list(isremote = False):
    _cmd = git.branch(lsoption = '-r' if isremote else '')
    _branches = split(invoke(_cmd), '\n')
    if _branches is None:
        exit_with_error("seems like there is no branch available...")
    _index = 0
    _current = None
    for line in _branches:
        if '*' in line:
            _current = _index
        _index += 1
    if isremote:
        return _current, ['refs/' + x.strip('* ') for x in _branches if x != '']
    else:
        return _current, [x.strip('* ') for x in _branches if x != '']

#based on git branch, to get the current git branch
def get_current_branch():
    _first_line = split(invoke(git.status()), '\n')[0]
    return split(_first_line)[-1] #last word of the first line is the branch name

def is_remote_branch(b):
    #TODO: check if we have network connected.
    _url = get_remote_url()
    return invoke(git.lsremote(_url, b))

#delete a branch
def delete_branch(branch, type):
    if type == 'remote branch': #to delete a remote branch
        _ans = get_answer('Delete the remote branch %s ? [y/N]' % branch, default = 'n')
        if _ans.lower() == 'y':
            #TODO: need to implement the deletion of a remote branch
            #_cmd = git.push
            pass
        else:
            return False, 'branch %s is not deleted' % branch
    else: #to delete a local branch
       if branch == get_current_branch():
           return False, 'current branch %s cannot be deleted' % branch
       _cmd = git.branch(del_branch = branch)
    _tmp = invoke(_cmd)
    if _tmp.startswith(('Deleted', 'warning:')):
        #delete the corresponding config values
        remove_local(section = 'branch.%s' % branch)
        remove_local(section = 'remote.%s' % branch)
        return True, _tmp
    elif 'is not fully merged' in _tmp: #check if we should try with -D
        _ans = get_answer(prompt = "%s is not fully merged. Delete it anyway? [y/N]" % branch,
                          default = 'n',
                          help = "it is likely you have changes in the branch.\n" +
                                 "you can force deleting the branch, or quit.")
        if _ans.lower() == 'y':
            #delete the corresponding config values
            remove_local(section = 'branch.%s' % branch)
            remove_local(section = 'remote.%s' % branch)
            return True, invoke(git.branch(force_del_branch = branch))
        else:
            return False, 'branch %s is not deleted' % branch
    else: # what else is missing?
        exit_with_error(_tmp)

#my way to figure out if a branch exist, returns False when a hash is given
def if_branch_exist(branch):
    _tmp = invoke(git.showref(branch = branch))
    return _tmp is not None

#-------------------config helppers
def change_branch():
    _tmp = invoke(git.config(exp = '^remote\.*'))
    _ball = RemoteSourceBall(_tmp.split('\n'))
    _ans = get_answer(title = 'Remote List', prompt = 'Pick a remote setting',
                      help = "this is to change the remote values of the current branch",
                      ball = _ball)
    _remote = _ans[0].split('\n')[0]
    bname = get_current_branch()
    set_local('branch.%s.remote' % bname, value = _remote)
    try:
        _fetch_str = get_local('remote.%s.fetch' % _remote)
    except ConfigItemMissing:
        exit_with_error("config item is missing, please report to the developer so that we can fix it!")
    _remote_path = _fetch_str.split(':')[0].strip('+')
    if not '*' in _remote_path:
        set_local('branch.%s.merge' % bname, value = _remote_path)
    else:
        _ans = get_answer(prompt = 'Would you like to load from %smaster? [Y/n]' %\
                                   _remote_path.strip('*'),
                          default = 'Y')
        if _ans.lower() == 'n':
            _branch = get_answer(prompt = 'Enter the ' + paint('red', 'remote ') +
                                          'branch name:')
        else:
            _branch = 'master'
        set_local('branch.%s.merge' % bname, value = _remote_path.replace('*', 'master'))

def get_configurations():
    #local settings
    if root_path():
        _current_branch = get_current_branch()
        try:
            _current_branch_remote = get_remote(_current_branch)
            _current_branch_merge = get_local('branch.%s.merge' % _current_branch)
        except ConfigItemMissing:
            exit_with_error("config item is missing, please report to the developer so that we can fix it!")
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

#set the config for a new branch
def copy_branch_config(branch_to, branch_from):
    #check if the config is already there
    try:
        _read_remote = get_remote(branch_to)
        _read_merge = get_local('branch.%s.merge' % branch_to)
    except ConfigItemMissing:
        #set the config values if they are not set properly
        #read the values from the parent branch
        try:
            _parent_remote = get_remote(branch_from)
            _parent_url = get_local('remote.%s.url' % _parent_remote)
            _parent_fetch = get_local('remote.%s.fetch' % _parent_remote)
            _parent_merge = get_local('branch.%s.merge' % branch_from)
        except ConfigItemMissing:
            exit_with_error("config item is missing, please report to the developer so that we can fix it!")
        #set the values of the current branch
        set_local('branch.%s.merge' % branch_to, _parent_merge)
        set_local('branch.%s.remote' % branch_to, branch_to)
        set_local('remote.%s.url' % branch_to, _parent_url)
        set_local('remote.%s.fetch' % branch_to, _parent_fetch)

#get the remote value for the corresponding branch
def get_remote(branch):
    try:
        return get_local('branch.%s.remote' % branch)
    except ConfigItemMissing:
        return None

#get the url of the corresponding remote repository
def get_remote_url():
    try:
        _remote = get_remote(get_current_branch())
        _url = get_local('remote.%s.url' % _remote)
        return _url
    except ConfigItemMissing:
        return None

#set the url of the corresponding remote repository
def set_remote_url(url):
    try:
        _remote = get_remote(get_current_branch())
    except ConfigItemMissing:
        exit_with_error("config item is missing, please report to the developer so that we can fix it!")
    set_local('remote.%s.url' % _remote, url)

#get the remote branch, the merge value in the branch section
def get_remote_branch(show_remote_path = False):
    try:
        #get the name of the corresponding remote branch
        _current_branch = get_current_branch()
        _remote_branch = get_local('branch.%s.merge' % _current_branch)
        if show_remote_path: # return the path in the remote repo
            # skip the 'remotes' part
            if _remote_branch.startswith('refs/remotes'):
                return _remote_branch[:5] + _remote_branch[13:]
            else:
                return _remote_branch
        else: # return the local copy path linked to the remote repo
            _remote = get_remote(_current_branch)
            _fetch = get_local('remote.%s.fetch' % _remote)
            _remote_copy, _local_copy = _fetch.split(':')
            if '*' in _local_copy: #this is a path with wildcard
                _remote_copy = _remote_copy.strip('*+')
                _local_copy = _local_copy.strip('*')
                return _remote_branch.replace(_remote_copy, _local_copy)
            else: #this is the exact path to the remote branch
                return _local_copy
    except ConfigItemMissing:
        return None

#set the remote branch, the merge value in the branch section
def set_remote_branch(branch):
    set_local('branch.%s.merge' % get_current_branch(), branch)

#command to get local git config value
def get_local(element):
    _tmp = invoke(git.config(type = 'local', element = element))
    if not _tmp or "error: invalid key" in _tmp:
        raise ConfigItemMissing
    else:
        return _tmp[:-1]

def set_local(element, value):
    _tmp = invoke(git.config(type = 'local', element = element, value = value))

#command to get global git config value
def get_global(element):
    _tmp = invoke(git.config(type = 'global', element = element))
    return None if _tmp is None else _tmp[:-1]

#command to set global git config value
def set_global(element, value):
    _tmp = invoke(git.config(type = 'global', element = element, value = value))

def remove_global(section):
    _tmp = invoke(git.config(type = 'global', section = section))

def remove_local(section):
    _tmp = invoke(git.config(type = 'local', section = section, value = ''))

#-------------------functional blocks
def do_status(isremote = False, ishash = False, isdir = False, compare_str = ''):
    _cmds, status = list(), ''
    if isremote: #comparing with the remote branch
        #first fetch the latest copy, and compare locally
        print("comparing with the remote repository, please wait...")
        try:
            _remote = get_remote(get_current_branch())
        except ConfigItemMissing:
            exit_with_error("ERROR: cannot find the remote branch in your config file")
        do_fetch(url = _remote)
        #this should be the path to the local copy of the remote branch
        compare_str = get_remote_branch()
        if compare_str is None:
            compare_str = "Unknow"
    elif ishash:
        compare_str = select_hash_range()
    if compare_str:#with comparison objects specified, use 'git diff'
        for t in 'ACDMRTUXB':#diff with different diff filter to get the change's type
            _cmds.append(git.diff(selection = compare_str, type = t))
    else:# without comparison objects specified, use 'git status'
        _cmds.append(git.status(param = '-s'))
    for c in _cmds:
        if isdir: #only show the touched files in the current directory
            c += ' -- ' + os.getcwd()
        _tmp = invoke(c)
        _tmp = translate_status_code(c, _tmp)
        status += _tmp[:_tmp.rfind('\n')] + '\n' if _tmp else ''
    return status, compare_str

def do_log(range, format):
    return invoke(git.log(hash = range, format = format, param = '--date=short'))

def do_log_tag(range):
    options = '--abbrev-commit --date=short'
    _cmd = git.log(hash = range, format = '%ad|%an [%ae]|%h|%s|%d', param = options)
    _logs = split(invoke(_cmd), '\n')[:-1]
    _result = ''
    for _line in _logs:
        if '|' not in _line:
            #TODO: handle the changed file info here
            continue
        [_date, _author, _hash, _comment, _tmp] =\
                _line.split('|') if _line else ['', '', '', '', '']
        _tmp = split(_tmp.strip(' ()'), ', ')
        _branch = get_branches_with_commit(_hash)
        _container_tags = invoke("git tag --contains %s" % _hash)
        _container_tags = split(_container_tags, '\n')
        if _container_tags:
            #the hash has tags attached, get the tags on this specific hash
            _tags = list(set(_tmp) & set(_container_tags))
            _result += '___\nRev:     %s\nAuthor:  %s\nDate:    %s\nBranch:  %s\nComment: %s\nTags: %s\n' %\
                       (_hash, _author, _date, _branch, _comment, _tags)
        else: #a hash without any tag
            _result += '___\nRev:     %s\nAuthor:  %s\nDate:    %s\nBranch:  %s\nComment: %s\n' %\
                       (_hash, _author, _date, _branch, _comment)
    return _result

def do_log_author_or_date(ifdate, format, range, authors):
    _options = ''
    if ifdate: #ask for the date range
        _d_start = get_answer(prompt = "Start Date: ",
                              help = "Enter the start date of the logs, e.g. 2012-12-26")
        _d_end = get_answer(prompt = "End Date: ",
                            help = "Enter the end date of the logs, e.g. 2012-12-26")
        if re.match('^[\s]*[\d]{4}-[\d]{1,2}-[\d]{1,2}[\s]*$', _d_start): #the input is valid
            _options += ' --after="%s"' % _d_start
        if re.match('^[\s]*[\d]{4}-[\d]{1,2}-[\d]{1,2}[\s]*$', _d_end): #the input is valid
            _options += ' --before="%s"' % _d_end
        range = 0 #with dates specified, no need for the range
    if type(authors) is list and authors: #get the logs only with the given author name
        for a in authors:
            _options += ' --author=%s ' % a
    return invoke(git.log(hash = range, format = format,
                           param = '--date=short %s' % _options))

def _remove_unwanted_logs(log, start, end):
    _list = log.split('\n')
    _log_pointer = 0
    _line_index = 0
    _start_index = _end_index = 0
    for line in _list:
        _line_index += 1
        if line.strip():
            _blank_line = 0
            continue
        else:
            _blank_line += 1
            if _blank_line == 2:
                _log_pointer += 1
            else:
                continue
        if _log_pointer == start - 1:
            _start_index = _line_index
        if _log_pointer == end:
            _end_index = _line_index - 1
            break;
    if _start_index == 0 or _end_index == 0:
        print("oops, parsing the log went wrong")
        sys.exit()
    _tmp = _list[:2] + _list[_start_index:_end_index]
    _result = '\n'.join(_tmp) + '\n}'
    return _result

_dot_file = '/tmp/gittool.dot'
_svg_file = '/tmp/gittool.dotty.svg'
commit_index = 0

def do_log_graphic(num, hash_from, hash_to):
    #first get logs from HEAD to hash_from, we will remove the logs after hash_to later
    if num == 0:
        _range = 'HEAD' + hash_from * '^' + '..HEAD' + ' --ancestry-path'
    else:
        _range = 'HEAD' + num * '^' + '..HEAD' + ' --ancestry-path'
    #_format = '"%h" [label="<f0> %h|{<f1> %an|<f2> %cd}"]\n"%h":f0 -> {%p}'
    _format = """"%h" [label=<<TABLE>
                            <TR><TD ROWSPAN="2" PORT="f0" BGCOLOR="bisque"> %h</TD>
                                <TD>%an</TD></TR>
                            <TR><TD>%cd</TD></TR>
                            </TABLE>>]\n"%h":f0 -> {%p}
              """
    _result = invoke(git.log(hash = _range, format = _format, param = '--date=short'))
    #link hashes with arrows
    _result = re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', build_merge_arrows, _result)
    _result = 'digraph G{\nnode [shape=plaintext]\n'\
            + _result\
            + '}' #get data ready for dotty
    global commit_index
    commit_index = 0
    _result = re.sub('BGCOLOR="bisque">', fill_commit_index, _result)
    if num == 0:
        #we do the dirty trick here to remove the logs from HEAD to hash_to
        _result = _remove_unwanted_logs(_result, hash_to, hash_from)
    with open(_dot_file, 'w') as f:
        f.write(_result)
    try:
        #make use of xdot.py from http://code.google.com/p/jrfonseca/
        _cmd = 'xdot.py ' + _dot_file
        return invoke(_cmd) #show the generated dot file
    except OSError:
        print("Seems like Graphviz has not been installed...")
        sys.exit()

def do_rebase(from_ref):
    print("rebasing from %s ..." % from_ref)
    _stdout, _stderr = invoke(git.rebase(), need_error_and_out = True)
    if 'Failed to merge' in _stdout: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _stdout + _stderr

#merge branch, assuming frombr and tobr are valid branches
def do_merge(from_ref, to_ref = None):
    if not to_ref:
        to_ref = get_current_branch()
    #first check if the from ref is on the same branch of to_ref
    #_refs = invoke(git.branch(contains = from_ref)).split('\n')
    #for r in _refs:
    #    if to_ref == r.strip(' *'):
    #        exit_with_error("I cannot merge %s to %s, they are on the same branch."\
    #                        % (from_ref, to_ref))
    print("merging from %s ..." % from_ref)
    if to_ref:#we need to first switch to the to ref
        do_checkout_branch(target = to_ref) #switch to the target branch
    _tmp = invoke(git.merge(from_ref)) #try auto merge
    if 'Automatic merge failed' in _tmp: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _tmp

#checkout a branch, or make a new branch and then check it out
def do_checkout_branch(target, in_list = True, isremote = False, new_branch = ""):
    if isremote: #to 'checkout' a remote branch is to fetch and make the branch local
        _tmp = do_fetch(ref = target)
    elif in_list: #this is an existing branch
        print("loading branch %s ..." % paint('red', target))
        _tmp = invoke(git.checkout(target = target, new_branch = new_branch))
        if new_branch != "":
            set_local("core.CurrentBranch", value = new_branch)
        else:
            set_local("core.CurrentBranch", value = target)
    else: #selected branch is not in the list
        _tmp = make_branch(target)
    return _tmp

def do_checkout_file_from_commit(files, hash):
    for f in files:
        invoke(git.checkout(target = '%s %s' % (hash, f)))

def do_checkout_from_commit(ref):
    _new_branch = ''
    while not _new_branch: #force to input a name
        _new_branch = get_answer(prompt = "Give a name to the new branch")
    _parent_branch = get_current_branch()
    _parent_remote = get_remote(_parent_branch)
    ref = ref.strip(' \n\t')
    _tmp =  invoke(git.checkout(target = ref, new_branch = _new_branch))
    if 'fatal: git checkout:' in _tmp: #something wrong occur when checking out
        exit_with_error(_tmp)
    _tmp += invoke(git.branch(branch = _new_branch,
                              upstream = _parent_remote + '/' + _parent_branch))
    return _tmp

def do_patch(hash_str, patch_file):
    if not hash_str:
        _file_list, hash_str = get_hash_change()
        print(_file_list)
        _ans = get_answer(prompt = 'Patch the change in these files? [y/N]', default = 'n')
        if _ans.lower() is 'n':
            exit()
    _tmp = invoke(git.patch(selection = hash_str, patch_file = patch_file))
    return '\npatch saved to %s' % patch_file

def do_commit(msg, files_to_save = None):
    if files_to_save: #to save some of the changed files
        files_to_save = [x.split()[1] for x in files_to_save]
        print('\n'.join(files_to_save))
        _ans = get_answer(prompt = "save the files above? [y/N]", default = 'n')
        if _ans.lower() == 'y':
            _files_str = ' '.join(files_to_save)
            invoke(git.commit(' %s -m "%s"' % (_files_str, msg)))
    else:
        invoke(git.commit(' -a -m "%s"' % msg))

def do_apply(file):
    _tmp = invoke(git.apply(file, check = True))
    for line in _tmp.split('\n'):
        if 'does not apply' in line:
            print("Attempt to load the patch failed.")
            _ans = get_answer(prompt = "Would you like to try another loose apply? [Y/n]",
                              default = 'y')
            if _ans.lower() is 'n':
                exit()
    _tmp = invoke(git.apply(file, check = True,
                            param = '--ignore-space-change --ignore-whitespace'))
    for line in _tmp.split('\n'):
        if 'does not apply' in line:
            exit_with_error("Loading the patch failed. Check the patch file")
    print("loading patch file %s ..." % paint('red', file))
    return invoke(git.apply(file))

def do_fetch(url = None, ref = None):
    #TODO: check if we have network connected.
    if url: #this is only to update the local repo by fetch
        print("updating ...")
        _result = invoke(git.fetch(url))
    else: #to fetch a remote branch to local repo
        _bname = ref[ ref.rfind('/') + 1: ] #get the branch name
        _local_ref = ref.replace('refs/', 'refs/remotes/', 1)
        _cur_branch = get_current_branch()
        try:
            _url = get_remote(_cur_branch) #assume the same url
        except ConfigItemMissing:
            exit_with_error("config item is missing, please report to the developer so that we can fix it!")
        print("loading remote branch %s ..." % paint('red', ref))
        _result = invoke(git.fetch(url = _url, src = ref, dst = _local_ref))
        #make a branch tracking the ref, forcing the branch name to be the same as the remote
        _local_ref = 'refs/remotes/' + ref[5:] #path to the local ref copy
        _result += do_checkout_branch(target = _local_ref, new_branch = _bname)
        link_branch_to_ref(_bname, _cur_branch, ref, _local_ref)
    return _result

def do_clone():
    #TODO: check if we have network connected.
    _urls = get_source_list('url')
    _ball = UrlSourceBall(_urls)
    _url = get_answer(prompt = 'Pick a source to clone from',
                      title = ' URL List ',
                      ball = _ball)
    if isinstance(_url, list):
        _url = _url[0]
    if _url not in [x.split()[0] for x in _urls]: #user type in a new item
        add_to_source_list('url', _url)
    print("Cloning %s ..." % _url)
    invoke(git.clone(_url))
    return "Done"

def push_to_remote():
    #TODO: check if we have network connected.
    #TODO: code is missing to set up the configuration properly after push from a local branch
    _url = get_remote_url()
    _ref = get_remote_branch(show_remote_path = True)
    if _url and _ref:
        _msg = 'push to ' + paint('red', 'URL') + ': ' + _url + '\n' +\
               '        ' + paint('red', 'REF') + ': ' + _ref + '\nOK? [Y/n]'
        _ans = get_answer(prompt = _msg, default = 'y')
    # if either of url or ref is None,
    # or the user would like to push to a new location
    if _url is None or _ref is None or _ans.lower() == 'n':
        #choose or specify a URL
        _urls = get_source_list('url')
        _ball = UrlSourceBall(_urls)
        _url = get_answer(prompt = 'Select a URL to push',
                          title = ' URL List ',
                          ball = _ball)[0]
        if _url not in [x.split()[0] for x in _urls]:
            #user type in a new item that is not in the ball list, remember it
            add_to_source_list('url', _url)
        # REVISIT: the set_remote_url here is to update the config file based on
        # the current push operation, however, in some environments doing this
        # will break the behavior of private tools.
        set_remote_url(_url)
        #choose or specify a REF
        _refs = get_source_list('ref')
        _ball = RefSourceBall(_refs)
        #TODO: FIX THE ISSUE HERE!!!
        _ref = get_answer(prompt = 'Select a REF to push',
                          title = ' Reference List ',
                          ball = _ball) #[0]
        if _ref not in [x.split()[0] for x in _refs]:
            #user type in a new item that is not in the ball list
            add_to_source_list('ref', _ref)
        increment_count('url', _url)
        increment_count('ref', _ref)
        set_remote_branch(_ref)  #this doesn't work yet
    _cmd = git.push(repo = _url, branch = get_current_branch(), ref = _ref)
    _tmp = invoke(_cmd)
    if 'non-fast-forward updates were rejected' in _tmp:
        print(_tmp)
        _ans = get_answer(prompt = 'would you like to force pushing? [y/N]',
                          default = 'N')
        if _ans.lower() == 'y':
            _cmd = git.push(repo = _url, branch = get_current_branch(),
                            ref = _ref, param = '--force')
            return invoke(_cmd)
        else:
            return "done"
    else:
        return _tmp #when the push is ok, return the git command result

#-------------------hash helppers
#take two hashes and return a valid hash string based on the age of the hashes
def ordered_hash_string(h1, h2):
    _birthday1 = invoke(git.log(hash = h1, num = 1, format = '%ct'))
    _birthday2 = invoke(git.log(hash = h2, num = 1, format = '%ct'))
    if int(_birthday1) > int(_birthday2): #h1 is younger than h2
        return '%s..%s' % (h2, h1)
    else:
        return '%s..%s' % (h1, h2)

#prompt the user a list of hashes and ask for a selected hash
def select_hash(since = 7, until = 0):
    _group_size = since
    while True:
        _range = "-%(num_of_log)d --skip=%(num_to_skip)d" %\
                {'num_of_log': abs(since - until) + 1,
                 'num_to_skip': min(since, until) - 1}
        _format='Rev:       %h%n\tDate:     %cd%n\tComment:  %s|'
        _tmp = do_log(_range, _format)
        _ball = HashBall(_tmp.split('|\n')[:-1])
        _ans = get_answer(title = ' Hash List ', default = 'more', ball = _ball,
                          help = '   Enter directly or "more" for more hashes, or\n' +
                                 '   "more <ID>" for further details of the hash, or\n')[0]
        if _ans == 'more':
            until = since
            since += _group_size
        elif _ans.startswith('more'):
            _index = int(split(_ans)[-1])
            print(invoke(git.log(hash = _ball[_index], num = 1)))
            raw_input('Press Enter to continue...')
        else:
            return _ans
        continue

def select_hash_range(with_current_hash = False, with_previous_hash = False):
    if with_previous_hash is True: #obtain the current and its previous hash
        _current_hash, _base_hash = get_hashes(2)
    else: #get the hashes given by the user
        print("[+] Select a hash")
        _base_hash = select_hash(since = 4)
        if not with_current_hash:#we need two hashes to get the range
            print("[+] Select the other hash")
            _current_hash = select_hash(since = 4)
        else:
            _current_hash = get_hashes(1)[0]
    return ordered_hash_string(_base_hash, _current_hash)

#get file differences between two hashes
def get_hash_change(with_current_hash = False, with_previous_hash = False):
    _hash_str = select_hash_range(with_current_hash = with_current_hash,
                                  with_previous_hash = with_previous_hash)
    #list all changed files
    _file_list = invoke(git.diff(selection = _hash_str))
    return _file_list.strip(' \n'), _hash_str

#get the current hash string
def get_hashes(num):
    _hash_str = invoke(git.log(num = num, format = '%h'))
    return split(_hash_str, '\n')[:-1] #get rid of the last empty line

#check if a hash exists
def if_hash_exist(ver):
    _tmp = invoke(git.show(param = ver)).split('\n')[0]
    if _tmp.startswith('fatal: ') or _tmp.strip() is None:
        return False
    else:
        return _tmp

#-------------------path helppers
#get the root path of the current repository
def root_path():
    _tmp = invoke(git.revparse(param = '--show-toplevel'))
    return None if 'Not a git repository' in _tmp else _tmp.strip(' \n')

#check if we are at a git repository
def check_git_path():
    if root_path() is None:
        exit_with_error("It seems you are not in a git repository...")

#-------------------source helppers
#get the source list length
def get_source_list_len(source):
    _len = get_global('sourcelist.%s.length' % source)
    return int(_len) if _len else 0

#read the remembered source list
def get_source_list(source):
    _list = list()
    for i in range(get_source_list_len(source)):
        _tmp = get_global('sourcelist.%s.item%d' % (source, (i + 1)))
        if _tmp is None:
            ConfigItemMissing.complain()
        _list.append(_tmp)
    return _list

def delete_source(source, name):
    _len = get_global('sourcelist.%s.length' % name)
    for i in range(int(_len)):
        _line = get_global('sourcelist.%s.item%d' % (name, i + 1))
        if _line.split()[0] == source:
            set_global ('sourcelist.%s.item%d' % (name, i + 1), '')
            set_global('sourcelist.%s.length' % name, str(int(_len) - 1))
            return True, '[%s] deleted' % source
    return False, '[%s] not deleted' % source

#add a new source into the source list
def add_to_source_list(type, item):
    _len = get_source_list_len(type)
    set_global('sourcelist.%s.item%d' % (type, (_len + 1)), item + ' 0')
    set_global('sourcelist.%s.length' % type, str(_len + 1))

#increment the count of a source item
def increment_count(type, item):
    _len = get_source_list_len(type)
    for i in range(1, _len + 1):
        _tmp = get_global('sourcelist.%s.item%d' % (type, i))
        if _tmp.split()[0] == item: # find the matching item
            set_global('sourcelist.%s.item%d' % (type, i),
                       '%s %d' % (item, int(_tmp.split()[1]) + 1))
            return
    exit_with_error("Something is wrong: can't find the souce item!")

#-------------------file helppers
def number_of_changed_files(_hashes = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = invoke(git.diff(selection = _hashes if _hashes else _remote_branch))
    return len(split(_tmp, '\n')) - 1

#return list of changed files and a list of untracked files from the output of 'git status -s'
def get_changed_files(str):
    _changed_files, _untracked_files = [], []
    if str is not None:
        _changed_pattern = '^[_MDACUT]{1,2}' #modifed/deleted/added/copied/unmerged/type_changed
        _untracked_pattern = '^\?\?.*' #untracked files
        _file_list = split(str, '\n')[:-1]
        for x in _file_list:
            _changed_files += [x] if re.search(_changed_pattern, x) else []
            _untracked_files += [x] if re.search(_untracked_pattern, x) else []
    return _changed_files, _untracked_files

#return the number of changed but not commited files
def num_uncommited_files():
    _tmp = invoke(git.status(param = '-s -uno'))
    _tmp = split(_tmp, '\n')
    return len(_tmp)

#revert a file given in a file item
def revert_file_item(item, unused):
    _file = item[item.rfind(' ') + 1:] #get the real file name
    _remove_from_list = False
    if re.search('^_[MDT]', item):    #not updated
        invoke(git.checkout(target = _file))
        _remove_from_list = True
    elif re.search('^[MARCD]_', item): #index and worktree are the same, need to reset first
        invoke(git.reset(file = _file))
        invoke(git.checkout(target = _file))
        _remove_from_list = True
    elif re.search('^UU', item): #this is a corner case i met when pull to a conflict situation
        invoke(git.reset(file = _file)) # put 'UU' to 'MM'
        invoke(git.reset(file = _file)) # put 'MM' to ' M'
        invoke(git.checkout(target = _file)) # clean ' M' eventually
        #NOTE: when in here we most likely came from a failed merge, so even when reverting all the changes
        #the repository is not yet cleaned, this is because of the existense of .git/MERGE_HEAD.
        #remove the file and everything works (like 'git pull')
        _remove_from_list = True
    elif re.search('^AA', item): #another case introduced possibly by a failed merge
        invoke(git.reset(file = _file)) # put 'AA' to '_M'
        invoke(git.checkout(target = _file)) # clean ' M' eventually
        _remove_from_list = True
    elif item.strip().startswith('??'): #the file is out of hash control
        invoke('rm ' + _file)
        _remove_from_list = True
    elif item.strip().startswith('*'): #the file status is unknown other than 'changed'
        exit_with_error("don't know how to revert %s" % _file)
    else:
        exit_with_error('oops, error when reverting file: %s' % item)
    return _remove_from_list, '%s reverted' % _file
    #TODO: what to do if file is commited, but need to delete from a diff list
    #   this means we need to copy a specified hash to overwrite

def remove_link_file(x):
    _fullpath = sys.argv[0]
    _dir = _fullpath[:_fullpath.rfind('/') + 1]
    invoke('rm %s' % (_dir + x))

#-------------------GLOBAL SETTINGS-------------------
# Edit the following settings to make GITTool fits your need
PROMPT_SIGN = ':> ' # unichr(0x263B) will show a smiling face.
DEBUG = False
COLOR = False if get_global('GitTool.ColorSupport') == 'no' else True

color = dict()
color['none'] = ''
if COLOR:
    color['red'] = '\033[31m'
    color['green'] = '\033[32m'
    color['yellow'] = '\033[33m'
    color['blue'] = '\033[34m'
    color['magenta'] = '\033[35m'
    color['lightblue'] = '\033[36m'
    color['white'] = '\033[37m'
    color['gray'] = '\033[30m'
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


