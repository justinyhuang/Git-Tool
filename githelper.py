import gitcommand as git
import subprocess
import pdb
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
        _firstline = self[k].split('\n')[0]
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
                invoke([git.add(_file)])
                self.list[i] = re.sub('\?\?', 'A_', self.list[i])
    def delete(self, item_list):
        super(FileBall, self).delete(item_list, revert_file_item)

class UrlSourceBall(Ball):
    """
    A ball that holds and manages a list of url sources
    """
    def __init__(self, list, name = 'URL Source'):
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

class GITError(Exception):
    """base class of all GitTool error exceptions"""

class ConfigItemMissing(GITError):
    """The item/section in the git config file does not exist"""

#-------------------INTERNAL HELPPER FUNCTIONS-------------------
#The internal helpper functions are used by the service functions.
#Based on git direct call functions, the helpper functions fulfill certain git-tool sub features.
#No direct git command calls will be made in these functions.

#-------------------GLOBAL SETTINGS-------------------
# Edit the following settings to make GITTool fits your need
PROMPT_SIGN = ':> ' # unichr(0x263B) will show a smiling face.
DEBUG = False
COLOR = True

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
def invoke(cmd, detached = False):
    if DEBUG == True: #for debug only
        print(paint('yellow', ''.join(cmd)))
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
def get_answer(prefix = '', prompt = '', postfix = '', default = None,
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
            _prompt = (prefix + '\n' if prefix else '') +\
                      '\n'.join(ball.get_indexed_list(highlight = hl)) + '\n' +\
                      (postfix + '\n' if postfix else '') + prompt
        else:
            _prompt = prompt
        _ans = raw_input(_prompt + _ps).strip()
        if _ans == '/h':
            print(help)
        elif '/e' == _ans:
            exit()
        elif _ans.startswith('/d '):
            if ball is None:
                exit_with_error("no ball is passed while a delete is required")
            if re.search('^\/d\s+\d+([\s,-]+\d+)*\s*$', _ans): #space or ',' is used as separator
                #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
                _tmp = re.sub('\d+[\s]*-[\s]*\d+', expand_indexes_from_range, _ans[3:])
                _d_list = [int(x.group()) for x in re.finditer('\d+', _tmp)] #get all indexes
                ball.delete(_d_list)
            else:
                exit_with_error("to delete an item, try '/d <index>'")
            #update the highlighted item
            for x in _d_list:
                if x < hl:
                    hl -= 1
        elif _ans.startswith('/a '):
            if ball is None:
                exit_with_error("no ball is passed while a delete is required")
            if re.search('^\/a\s+\d+([\s,-]+\d+)*\s*$', _ans): #space or ',' is used as separator
                #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
                _tmp = re.sub('\d+[\s]*-[\s]*\d+', expand_indexes_from_range, _ans[3:])
                _a_list = [int(x.group()) for x in re.finditer('\d+', _tmp)] #get all indexes
                ball.add(_a_list)
            else:
                exit_with_error("to add an item, try '/a <index>'")
            #update the highlighted item
            for x in _a_list:
                if x < hl:
                    hl += 1
        elif re.search('^\s*\d+\s*', _ans) and ball: #return the selected ball item
            return ball[int(_ans)]
        elif _ans or default: #this is a non-empty input, or default is set to allow direct Enter
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

def merge_or_checkout():
    _ans = get_answer(prompt = "Merge or Checkout? [m/C]", default = 'c')
    return 'm' if _ans == 'm' or _ans == 'M' else 'c'

#print message with a fixed length bar
def make_msg_bar(msg):
    _colorless_msg = msg
    _colorless_msg = re.sub('\033[^m]*m', '', _colorless_msg) #remove the color code
    _msg_len = len(_colorless_msg)
    _pre = '_' * ((80 - _msg_len) / 2)
    _post = '_' * ((80 - _msg_len) / 2 + (80 - _msg_len) % 2)
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
#select a branch from list
def select_branch(isremote = False):
    _curbranch, _branch_list = get_branch_list(isremote)
    _listball = BranchBall(_branch_list, name = 'remote branch' if isremote else 'branch')
    _ans = get_answer(prefix = '--- Branch List ---', default = '/e',
                      ball = _listball, hl = _curbranch)
    if _ans == '/e': #user enters nothing, might think of quit
        exit()
    return _branch_list, _ans

def make_branch(branch):
    _previous_branch = get_current_branch()
    _tmp = invoke([git.branch(branch = branch)]) #create branch with the name given
    _tmp = invoke([git.checkout(target = branch)])
    set_branch_config(branch_from = _previous_branch) #new branch, set the config properly
    _result = 'created and switched to new branch: ' + paint('red', branch) + '\n'
    _result += 'config is set based on ' + paint('red', _previous_branch)
    return _result

#based on the remote and fetch values of the parent, set up the values for the new branch
def make_branch_linked_to_ref(bname, ref, repo = ''):
    _ref = ref[5:] #skip the 'refs/'
    _remote = get_local(section = 'branch.%s.remote' % get_current_branch())
    _repo = repo if repo\
                 else get_local(section = 'remote.%s.url' % _remote)
    _cmd = git.checkout(target = _ref, new_branch = bname)
    _tmp = invoke([_cmd])
    _fetch = '+refs/' + _ref + ':refs/remotes/' + _ref
    #set up a new remote section and a new branch section for this new branch
    set_local(section = 'remote.%s.url' % bname, value = _repo)
    set_local(section = 'remote.%s.fetch' % bname, value = _fetch)
    set_local(section = 'branch.%s.remote' % bname, value = bname)
    set_local(section = 'branch.%s.merge' % bname, value = ref)
    return _tmp

def get_branches_with_commit(hash):
    _cmd = git.branch(contains = hash)
    return [x.strip(' *') for x in split(invoke([_cmd]), '\n') if x]

def update_local_branch():
    #1. fetch the updates from remote repo
    _current_branch = get_current_branch()
    _remote = get_local('branch.%s.remote' % _current_branch)
    _merge = get_local('branch.%s.merge' % _current_branch)
    if _remote and _merge: #only initiate fetch when the config values are correct
        print("fetching from %s ..." % _remote)
        print(invoke([git.fetch()]))
    else: #quit if the corresponding config items are not set
        exit_with_error('There are item or section missing in the config file')
    #2. ask for option
    _ans = get_answer(prompt = "fetch completes, shall we Merge or Rebase? (m/R)",
                      default = 'r',
                      help = "Merge will keep the history of changes but mix the local " +\
                             "changes with the merged changes; while Rebase keeps all " +\
                             "local changes together but modifies the change history " +\
                             "and make it hard to trace back. You shall determine which " +\
                             "strategy you would like to use, carefully.")
    _remote_branch = get_remote_branch()
    if _ans == 'm' or _ans == 'M': #3a. merge
        return do_merge(_remote_branch)
    else: #3b. rebase, which is recommended in many cases
        return do_rebase(_remote_branch)
    #TODO: there is yet another option, see the better (and more complicated) rebase at
    # http://softwareswirl.blogspot.com/2009/04/truce-in-merge-vs-rebase-war.html

#get a branch list. returns <master branch index>, <branch list>
def get_branch_list(isremote = False):
    _cmd = git.branch(lsoption = '-r' if isremote else '')
    _branches = split(invoke([_cmd]), '\n')
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
    _first_line = split(invoke([git.status()]), '\n')[0]
    return split(_first_line)[-1] #last word of the first line is the branch name

def is_remote_branch(b):
    #TODO: check if we have network connected.
    _url = get_remote_url()
    return invoke([git.lsremote(_url, b)])

#delete a branch
def delete_branch(branch, type):
    if type == 'remote branch': #to delete a remote branch
        _ans = get_answer('Delete the remote branch %s ? [y/N]' % branch, default = 'n')
        if _ans == 'y' or _ans == 'Y':
            #TODO: need to implement the deletion of a remote branch
            #_cmd = git.push
            pass
        else:
            return False, 'branch %s is not deleted' % branch
    else: #to delete a local branch
       if branch == get_current_branch():
           return False, 'current branch %s cannot be deleted' % branch
       _cmd = git.branch(del_branch = branch)
    _tmp = invoke([_cmd])
    if _tmp.startswith(('Deleted', 'warning:')):
        return True, _tmp
    elif 'is not fully merged' in _tmp: #check if we should try with -D
        _ans = get_answer(prompt = "%s is not fully merged. Delete it anyway? [y/N]" % branch,
                          default = 'n',
                          help = "it is likely you have changes in the branch.\n" +
                                 "you can force deleting the branch, or quit.")
        if _ans == 'y' or _ans == 'Y':
            return True, invoke([git.branch(force_del_branch = branch)])
        else:
            return False, 'branch %s is not deleted' % branch
    else: # what else is missing?
        exit_with_error(_tmp)

#my way to figure out if a branch exist, returns False when a hash is given
def if_branch_exist(branch):
    _tmp = invoke([git.showref(branch = branch)])
    return _tmp is not None

#-------------------config helppers
#set the config for a new branch
def set_branch_config(branch_from):
    #check if the config is already there
    _cur_branch = get_current_branch()
    _read_remote = get_local('branch.%s.remote' % _cur_branch)
    _read_merge = get_local('branch.%s.merge' % _cur_branch)
    if _read_merge is None or _read_remote is None:
        #read the values from the parent branch
        _parent_remote = get_local('branch.%s.remote' % branch_from)
        _parent_merge = get_local('branch.%s.merge' % branch_from)
        #set the values of the current branch
        set_local('branch.%s.remote' % _cur_branch, _parent_remote)
        set_local('branch.%s.merge' % _cur_branch, _parent_merge)

#get the url of the corresponding remote repository
def get_remote_url():
    _remote = get_local('branch.%s.remote' % get_current_branch())
    if _remote is None:
        raise ConfigItemMissing
    _url = get_local('remote.%s.url' % _remote)
    return _url

#set the url of the corresponding remote repository
def set_remote_url(url):
    _remote = get_local('branch.%s.remote' % get_current_branch())
    if _remote is None:
        raise ConfigItemMissing
    set_local('remote.%s.url' % _remote, url)

#get the remote branch, the merge value in the branch section
def get_remote_branch():
    #get the name of the corresponding remote branch
    _current_branch = get_current_branch()
    _remote_branch = get_local(section = 'branch.%s.merge' % _current_branch)
    return _remote_branch if _remote_branch else ''

#set the remote branch, the merge value in the branch section
def set_remote_branch(branch):
    set_local('branch.%s.remote' % get_current_branch(), branch)

#command to get local git config value
def get_local(section):
    _tmp = invoke([git.config(config = 'local', section = section)])
    return None if _tmp is None else _tmp[:-1]

def set_local(section, value):
    _tmp = invoke([git.config(config = 'local', section = section, value = value)])

#command to get global git config value
def get_global(section):
    _tmp = invoke([git.config(config = 'global', section = section)])
    return None if _tmp is None else _tmp[:-1]

#command to set global git config value
def set_global(section, value):
    _tmp = invoke([git.config(config = 'global', section = section, value = value)])

#-------------------functional blocks
def do_log(range, format):
    return invoke([git.log(hash = range, format = format, param = '--date=short')])

def do_log_tag(range):
    _cmd = git.log(hash = range, format = '%ad|%an|%h|%s|%d',
                   param = '--abbrev-commit --date=short')
    _logs = split(invoke([_cmd]), '\n')[:-1]
    _result = ''
    for _line in _logs:
        [_date, _author, _hash, _comment, _tmp] =\
                _line.split('|') if _line else ['', '', '', '', '']
        _tmp = split(_tmp.strip(' ()'), ', ')
        _branch = get_branches_with_commit(_hash)
        _container_tags = invoke(["git tag --contains %s" % _hash])
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

def do_log_author_or_date(ifauthor, ifdate, format, range, author):
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
    pdb.set_trace()
    if ifauthor: #get the logs only with the given author name
        _options += ' --author=%s' % author
    return invoke([git.log(hash = range, format = format,
                           param = '--date=short %s' % _options)])

_dot_file = '/tmp/gittool.dotty.tmp'
_svg_file = '/tmp/gittool.dotty.svg'
commit_index = 0
def do_log_graphic(num, hash_from, hash_to):
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
    _result = invoke([git.log(hash = _range, format = _format, param = '--date=short')])
    #link hashes with arrows
    _result = re.sub('"[a-f0-9]{7}":f0 -> \{[ a-f0-9]+\}', build_merge_arrows, _result)
    _result = 'digraph G{\nnode [shape=plaintext]\n'\
            + _result\
            + '}' #get data ready for dotty
    global commit_index
    commit_index = 0
    _result = re.sub('BGCOLOR="bisque">', fill_commit_index, _result)
    with open(_dot_file, 'w') as f:
        f.write(_result)
    _tmp = invoke(['dot -Tsvg %s > %s' % (_dot_file, _svg_file)])
    _cmd = ['qiv', _svg_file]
    return invoke(_cmd, detached=True) #feed the data to dotty

def do_rebase(from_ref):
    print("rebasing from %s ..." % from_ref)
    return invoke([git.rebase()])

#merge branch, assuming frombr and tobr are valid branches
def do_merge(from_ref, to_ref = None):
    if not to_ref:
        to_ref = get_current_branch()
    #first check if the from ref is on the same branch of to_ref
    _refs = invoke([git.branch(contains = from_ref)]).split('\n')
    for r in _refs:
        if to_ref == r.strip(' *'):
            exit_with_error("I cannot merge %s to %s" % (from_ref, to_ref))
    print("merging from %s ..." % from_ref)
    if to_ref:#we need to first switch to the to ref
        invoke([git.checkout(target = to_ref)]) #switch to the target branch
    _tmp = invoke([git.merge(from_ref)]) #try auto merge
    if 'Automatic merge failed' in _tmp: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _tmp

#checkout a branch, or make a new branch and then check it out
def do_checkout_branch(selected_branch, in_list = True, isremote = False):
    if isremote: #to 'checkout' a remote branch is to fetch and make the branch local
        _tmp = do_fetch(selected_branch)
    elif in_list: #this is an existing branch
        _tmp = invoke([git.checkout(target = selected_branch)])
    else: #selected branch is not in the list
        _tmp = make_branch(selected_branch)
    return _tmp

def do_checkout_from_commit(ref):
    _new_branch = ''
    while not _new_branch: #force to input a name
        _new_branch = get_answer(prompt = "Give a name to the new branch")
    return invoke([git.checkout(target = ref, new_branch = _new_branch)])

def do_apply(file):
    _tmp = invoke([git.apply(file, check = True)])
    for line in _tmp.split('\n'):
        if 'does not apply' in line:
            exit_with_error("Loading the patch failed. Check the patch file")
    return invoke([git.apply(file)])

def do_fetch(ref):
    #TODO: check if we have network connected.
    _bname = ref[ ref.rfind('/') + 1: ] #get the branch name
    _local_ref = ref.replace('refs/', 'refs/remotes/', 1)
    _url = get_local(section = 'branch.%s.remote' % get_current_branch()) #assume the same url
    _result = invoke([git.fetch(url = _url, src = ref, dst = _local_ref)])
    #make a branch tracking the ref, forcing the branch name to be the same as the remote
    _result += make_branch_linked_to_ref(_bname, ref)
    return _result

def do_clone():
    #TODO: check if we have network connected.
    _urls = get_source_list('url')
    _ball = UrlSourceBall(_urls)
    _url = get_answer(prompt = 'Pick a source to clone from', ball = _ball)
    if _url not in [x.split()[0] for x in _urls]: #user type in a new item
        add_to_source_list('url', _url)
    print("Cloning %s ..." % _url)
    invoke([git.clone(_url)])
    return "Done"

def push_to_remote():
    #TODO: check if we have network connected.
    #TODO: code is missing to set up the configuration properly after push from a local branch
    _url = get_remote_url()
    _ref = get_remote_branch()
    if _url is None:
        exit_with_error('config values are missing, you will need to manually fix this issue')
    else:
        _msg = 'push to ' + paint('red', 'URL') + ': ' + _url + '\n' +\
               '        ' + paint('red', 'REF') + ': ' + _ref + '\nOK? [Y/n]'
        _ans = get_answer(prompt = _msg, default = 'y')
        if _ans == 'n' or _ans == 'N':
            #choose or specify a URL
            _urls = get_source_list('url')
            _ball = UrlSourceBall(_urls)
            _url = get_answer(prompt = 'Select a URL to push', ball = _ball)
            if _url not in _urls: #user type in a new item that is not in the ball list
                add_to_source_list('url', _url)
            set_remote_url(_url)
            #choose or specify a REF
            _refs = get_source_list('ref')
            _ball = RefSourceBall(_refs)
            _ref = get_answer(prompt = 'Select a REF to push', ball = _ball)
            if _ref not in _refs: #user type in a new item that is not in the ball list
                add_to_source_list('ref', _ref)
            increment('url', _url)
            increment('ref', _ref)
            set_remote_branch(_ref)
    _cmd = git.push(repo = _url, branch = get_current_branch(), ref = _ref)
    return invoke([_cmd])

#-------------------hash helppers
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
        _ans = get_answer(default = 'more', ball = _ball,
                          help = '   Enter directly or "more" for more hashes, or\n' +
                                 '   "more <ID>" for further details of the hash, or\n')
        if _ans == 'more':
            until = since
            since += _group_size
        elif _ans.startswith('more'):
            _index = int(split(_ans)[-1])
            print(invoke([git.log(hash = _ball[_index], num = 1)]))
            raw_input('Press Enter to continue...')
        else:
            return _ans
        continue

def select_hash_range(with_previous_hash = False):
    if with_previous_hash is True: #obtain the current and its previous hash
        _current_hash, _base_hash = get_hashes(2)
    else: #get the hashes given by the user
        print("[+] Select the" + paint('red', " start ") + 'hash')
        _base_hash = select_hash(since = 4)
        print("[+] Select the" + paint('red', " end ") + 'hash')
        _current_hash = select_hash(since = 4)
    return _base_hash + '..' + _current_hash

#get file differences between two hashes
def get_hash_change(with_previous_hash = False):
    _hash_str = select_hash_range(with_previous_hash)
    #list all changed files
    _file_list = invoke([git.diff(selection = _hash_str, name_only = True)])
    print(_file_list)
    _tmp = get_answer(prompt = 'Are the files that you changed? [y/N]', default = 'n')
    if _tmp is 'N' or _tmp is 'n':
        return None, None
    else:
        return _file_list, _hash_str

#get the current hash string
def get_hashes(num):
    _hash_str = invoke([git.log(num = num, format = '%h')])
    return split(_hash_str, '\n')[:-1] #get rid of the last empty line

#check if a hash exists
def if_hash_exist(ver):
    _tmp = invoke([git.revparse(hash = ver)])
    return not re.search('unknown revision', _tmp)

#-------------------path helppers
#get the root path of the current repository
def root_path():
    _tmp = invoke([git.revparse(param = '--show-toplevel')])
    return None if 'Not a git repository' in _tmp else _tmp

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
            raise ConfigItemMissing
        _list.append(_tmp)
    return _list

def delete_source(source, name):
    _len = get_global('sourcelist.%s.length' % name)
    for i in range(int(_len)):
        if get_global('sourcelist.%s.item%d' % (name, i + 1)) == source:
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
    for i in range(_len):
        _tmp = get_global('sourcelist.%s.item%d' % (type, i))
        if _tmp.split()[0] == item: # find the matching item
            set_global('sourcelist.%s.item%d' % (type, i),
                       '%s %d' % (item, str(_tmp.split()[1]) + 1))
            return
    exit_with_error("Something is wrong: can't find the souce item!")

#-------------------file helppers
def number_of_changed_files(_hashes = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = invoke([git.diff(selection = _hashes if _hashes else _remote_branch, name_only = True)])
    return len(split(_tmp, '\n')) - 1

#return list of changed files and a list of untracked files from the output of 'git status -s'
def get_changed_files(str):
    _changed_files, _untracked_files = [], []
    if str is not None:
        _changed_pattern = '^[_MDACU]{1,2}' #modifed/deleted/added/copied/unmerged files
        _untracked_pattern = '^\?\?.*' #untracked files
        _file_list = split(str, '\n')[:-1]
        for x in _file_list:
            _changed_files += [x] if re.search(_changed_pattern, x) else []
            _untracked_files += [x] if re.search(_untracked_pattern, x) else []
    return _changed_files, _untracked_files

#return the number of changed but not commited files
def num_uncommited_files():
    _tmp = invoke([git.status(param = '-s -uno')])
    _tmp = split(_tmp, '\n')
    return len(_tmp)

#revert a file given in a file item
def revert_file_item(item, unused):
    _file = item[item.rfind(' ') + 1:] #get the real file name
    _remove_from_list = False
    if re.search('^_[MD]', item):    #not updated
        invoke([git.checkout(target = _file)])
    elif re.search('^[MARCD]_', item): #index and worktree are the same, need to reset first
        invoke([git.reset(file = _file)])
        invoke([git.checkout(target = _file)])
    elif item.strip().startswith('??'): #the file is out of hash control
        invoke(['rm ' + _file])
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
    invoke(['rm %s' % (_dir + x)])


