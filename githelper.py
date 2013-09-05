import gitcommand as git
import subprocess, pdb, os, sys, re, math, time, operator, termios

class TextWindowManager(object):
    def __init__(self, up, down):
        self.windows = [] # keeps all the windows
        self.current_ptr = 0 # keeps track of the current line of the text cursor
        self.UP = up
        self.DOWN = down
    def create_window(self, width, height):
        self.windows.append([width, height])
        return len(self.windows) # this would be the id for the new window
    def term_print(self, str):
        print(str)
        self.current_ptr += str.count('\n') + 1
    def move_to_top(self, win_id):
        sys.stdout.write(self.UP * self.current_ptr) # move to the top of everything
        self.current_ptr = 0
        for w, h in self.windows[:win_id]: # move towards the top of the window
            self.current_ptr += h
            sys.stdout.write(self.DOWN * h)
    def clear_window(self, win_id):
        self.move_to_top(win_id)
        window = self.windows[win_id]
        self.term_print((' ' * window[0] + '\n') * window[1])
    def update_window(self, win_id, str):
        self.clear_window(win_id)
        self.move_to_top(win_id)
        self.term_print(str)
    def set_win_height(self, win_id, height):
        self.windows[win_id][1] = height
    def set_win_width(self, win_id, width):
        self.windows[win_id][0] = width
    def get_win_height(self, win_id):
        return self.windows[win_id][1]
    def get_win_width(self, win_id):
        return self.windows[win_id][0]


# borrowed from
# http://code.activestate.com/recipes/475116-using-terminfo-for-portable-color-output-cursor-co/
# and added the capability of holding/showing/updating a text buffer
class TerminalController:
    """
    A class that can be used to portably generate formatted output to
    a terminal.

    `TerminalController` defines a set of instance variables whose
    values are initialized to the control sequence necessary to
    perform a given action.  These can be simply included in normal
    output to the terminal:

        >>> term = TerminalController()
        >>> print 'This is '+term.GREEN+'green'+term.NORMAL

    Alternatively, the `render()` method can used, which replaces
    '${action}' with the string required to perform 'action':

        >>> term = TerminalController()
        >>> print term.render('This is ${GREEN}green${NORMAL}')

    If the terminal doesn't support a given action, then the value of
    the corresponding instance variable will be set to ''.  As a
    result, the above code will still work on terminals that do not
    support color, except that their output will not be colored.
    Also, this means that you can test whether the terminal supports a
    given action by simply testing the truth value of the
    corresponding instance variable:

        >>> term = TerminalController()
        >>> if term.CLEAR_SCREEN:
        ...     print 'This terminal supports clearning the screen.'

    Finally, if the width and height of the terminal are known, then
    they will be stored in the `COLS` and `LINES` attributes.
    """
    # Cursor movement:
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Terminal size:
    COLS = None          #: Width of the terminal (None for unknown)
    LINES = None         #: Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        """
        Create a `TerminalController` and initialize its attributes
        with appropriate values for the current terminal.
        `term_stream` is the stream that will be used for terminal
        output; if this stream is not a tty, then the terminal is
        assumed to be a dumb terminal (i.e., have no capabilities).
        """
        # Curses isn't available on all platforms
        try: import curses
        except: return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty(): return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')
        self.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or '')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or '')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg, i) or '')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg_ansi, i) or '')
        self.text_buffer = ''
        self.title = ''
        self.buffer_size = 0
        self.buffer_begin = 0
        self.buffer_end = 0
        self.win_mgr = TextWindowManager(self.UP, self.DOWN)
    def set_buffer(self, buff):
        self.text_buffer = buff
        self.buffer_size = len(buff)
    def set_windows(self, width1, height1, width2, height2, width3, height3):
        self.buffer_begin = 0
        self.buffer_end = height2
        # win0 is the title window
        self.win_mgr.create_window(width1, height1)
        # win1 is the window of which the content could be updated
        self.win_mgr.create_window(width2, height2)
        # win2 is the window for input from the user
        self.win_mgr.create_window(width3, height3)
    def set_title(self, title):
        self.title = title
        self.win_mgr.set_win_height(0, title.count('\n') + 1)
    def show_input_prompt(self, postfix, prompt):
        self.win_mgr.move_to_top(2)
        self.win_mgr.update_window(2, (postfix + '\n' if postfix else '') + prompt + '_')
    def backward_buffer(self):
        self.buffer_begin = self.buffer_end
        win_height = self.win_mgr.get_win_height(1)
        self.buffer_end = self.buffer_end + win_height\
                          if self.buffer_end + win_height < self.buffer_size\
                          else self.buffer_size

    def forward_buffer(self):
        win_height = self.win_mgr.get_win_height(1)
        self.buffer_begin = self.buffer_begin - win_height\
                            if self.buffer_begin > win_height\
                            else 0
        self.buffer_end = self.buffer_begin + win_height

    def show_buffer(self, browse_mode = True, highlight = None):
        self.win_mgr.update_window(0, self.title)
        _buffer = self.text_buffer[:] # to copy the list
        if highlight:
            # we are asked to show the highlighted portion of the buffer
            for i in highlight:
                try:
                    _buffer[i] = self.text_buffer[i].replace('\t', '\t' + color['reverse']) + _end_
                except LookupError:
                   pass # some of the selection is invalid, just ignore
            _last_hl_idx = highlight[-1] + 1
            # if the highlighted item is outside of this window, we
            # will update the window to show the item
            while _last_hl_idx < self.buffer_begin:
                self.forward_buffer()
            while _last_hl_idx > self.buffer_end:
                self.backward_buffer()

        if self.win_mgr.get_win_height(1) >= self.buffer_size:
            # we can show the entire text buffer
            self.win_mgr.set_win_height(1, self.buffer_size)
            self.buffer_end = self.buffer_size
            self.win_mgr.update_window(1, '\n'.join(_buffer[self.buffer_begin:self.buffer_end]))
        else:
            quit_keys = ['TwiceEsc', 'q', 'Q']
            page_down_keys = ['PgDn', 'j', 'J', ' ', 'Down', 'Enter']
            page_up_keys = ['PgUp', 'Up', 'k', 'K']
            self.win_mgr.update_window(1, '\n'.join(_buffer[self.buffer_begin:self.buffer_end]))
            if browse_mode == False:
                return # escape when we are told only to show the buffer and quit
            _key = capture_keypress()
            while (_key not in quit_keys and
                   not (_key == ' ' and self.buffer_end == self.buffer_size)) :
                if _key in page_down_keys:
                    self.backward_buffer()
                elif _key in page_up_keys:
                    self.forward_buffer()
                self.win_mgr.update_window(1, '\n'.join(_buffer[self.buffer_begin:self.buffer_end]))
                _key = capture_keypress()

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or ''
        return re.sub(r'\$<\d+>[/*]?', '', cap)

    def render(self, template):
        """
        Replace each $-substitutions in the given template string with
        the corresponding terminal control string (if it's defined) or
        '' (if it's not).
        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

#-------------------INTERNAL CLASSES-------------------
class Ball(object):
    """
    A ball is a carrier that holds the output of a git-tool helper function
    the carrier is able to perform certain operations on the data it holds.
    """
    def __init__(self, _list, name = 'item'):
        _height, _width = os.popen('stty size', 'r').read().split()
        self.term_height = int(_height)
        self.term_width = int(_width)
        #cut off the over-length data so that we could show the data
        #better in the terminal
        self.list = [x[:self.term_width] for x in _list]
        self.name = name
        self.highlight = 0
        self.selected_list = []
        self.display_list = []
        self.term = TerminalController() # for better control of the terminal output
        self.help = "You can: \
          \n   Type the index of the %s or,\
          \n   Type the name for a %s or,\
          \n   Use '/d <item_index>' to delete an %s or,\
          \n   Use '/e' to quit" % (self.name, self.name, self.name)
    def __getitem__(self, k):
        return self.list[k]
    def get_list(self):
        return self.list
    def get_indexed_list(self, highlight):
        return index_list(self.list, highlight = highlight)
    def paint_indexed_list(self, title, highlight, postfix, prompt):
        self.highlight = highlight
        self.prompt = prompt
        _buff = index_list(self.list, highlight = highlight)
        # configure the TerminalController for display
        self.term.set_buffer(_buff)
        # limit the buffer window to half of the terminal height,
        #so that we could still show things like title, help messages etc.
        self.term.set_windows(self.term_width, 1,
                              self.term_width, self.term_height / 2,
                              self.term_width, 1)
        self.term.set_title(title)
        self.term.show_buffer()
        self.term.show_input_prompt(postfix, self.prompt)
    def set_selected_indexed_list(self, highlight, selected_list):
        self.highlight = highlight
        self.selected_list = selected_list
    # for a ball we could do more when user providing the selection
    # including highlighting the selection etc.
    def get_selection(self):
        _result = ''
        _key = getkey()
        while _key != '\n': #quit when enter is pressed
            if ord(_key) == 127: # that is a backspace
                _result = _result[:-1]
            else:
                _result += _key
            _hl_indexes = self.get_highlight_indexes(_result)
            self.term.win_mgr.update_window(2, self.prompt + _result + '_')
            self.term.show_buffer(browse_mode = False, highlight = _hl_indexes)
            _key = getkey()
        return _result
    def get_highlight_indexes(self, string):
        _operator = re.findall('^[\s\D]*', string) #it always returns something
        #return the highlighted indexes
        return get_indexes(operator = _operator[0], line = string)
    def add(self, item_list, func): #children will take care of the implementation
        pass
    def delete(self, item_list, func):
        item_list.sort(reverse = True) #remove the very last item in the list first
        for x in item_list:
            try:
                _result, _msg = func(self[x], self.name)
                if _result is True: #user might choose not to delete
                    self.list.remove(self[x])
            except LookupError:
                _msg  = "item %d doesn't exist" % x
            print(_msg)

class BranchBall(Ball):
    """
    A ball that holds a list of branches
    """
    def __init__(self, list, name = 'branch'):
        super(BranchBall, self).__init__(list, name)
    def delete(self, item_list):
        super(BranchBall, self).delete(item_list, delete_branch)
    def get_height(self):
        return 1

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
    def get_height(self):
        return 3

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
    def get_height(self):
        return 1

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
    def get_height(self):
        return 1

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
    def get_height(self):
        return 1

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
    def get_height(self):
        return 1


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
# to capture a keypress, in Linux
def capture_keypress():
    a = [0, 0, 0, 0, 0, 0]
    try:
        os.system('stty -icanon')
        os.system('stty -echo')
        a[0]=ord(sys.stdin.read(1))
        if a[0]==27:
            a[1]=ord(sys.stdin.read(1))
            if a[1]==91:
                a[2]=ord(sys.stdin.read(1))
                if (a[2]>=49 and a[2]<=54) or a[2]==91:
                    a[3]=ord(sys.stdin.read(1))
                    if a[3]>=48 and a[3]<=57:
                        a[4]=ord(sys.stdin.read(1))
    finally:
        os.system('stty echo')
        os.system('stty icanon')
    if a==[ 10, 0, 0, 0, 0, 0]: k = "Enter"         #13
    elif a==[ 27, 27, 0, 0, 0, 0]: k = "TwiceEsc"   #27
    elif a==[ 27, 91, 91, 65, 0, 0]: k = "F1"       #1059
    elif a==[ 27, 91, 91, 66, 0, 0]: k = "F2"       #1060
    elif a==[ 27, 91, 91, 67, 0, 0]: k = "F3"       #1061
    elif a==[ 27, 91, 91, 68, 0, 0]: k = "F4"       #1062
    elif a==[ 27, 91, 91, 69, 0, 0]: k = "F5"       #1063
    elif a==[ 27, 91, 49, 55, 126, 0]: k = "F6"     #1064
    elif a==[ 27, 91, 49, 56, 126, 0]: k = "F7"     #1065
    elif a==[ 27, 91, 49, 57, 126, 0]: k = "F8"     #1066
    elif a==[ 27, 91, 50, 48, 126, 0]: k = "F9"     #1067
    elif a==[ 27, 91, 50, 49, 126, 0]: k = "F10"    #1068
    elif a==[ 27, 91, 50, 51, 126, 0]: k = "F11"    #1133
    elif a==[ 27, 91, 50, 52, 126, 0]: k = "F12"    #1134
    elif a==[ 27, 91, 50, 126, 0, 0]: k = "Insert"  #1082
    elif a==[ 27, 91, 51, 126, 0, 0]: k = "Delete"  #1083
    elif a==[ 27, 91, 49, 126, 0, 0]: k = "Home"    #1071
    elif a==[ 27, 91, 52, 126, 0, 0]: k = "End"     #1079
    elif a==[ 27, 91, 53, 126, 0, 0]: k = "PgUp"    #1073
    elif a==[ 27, 91, 54, 126, 0, 0]: k = "PgDn"    #1081
    elif a==[ 27, 91, 65, 0, 0, 0]: k = "Up"        #1072
    elif a==[ 27, 91, 66, 0, 0, 0]: k = "Down"      #1080
    elif a==[ 27, 91, 68, 0, 0, 0]: k = "Left"      #1075
    elif a==[ 27, 91, 67, 0, 0, 0]: k = "Right"     #1077
    elif a==[127, 0, 0, 0, 0, 0]: k = "Backspace"   #8
    else: k = chr(a[0])                             # Ascii code
    return k

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

def hide_cursor():
    if sys.platform == 'darwin':
        os.system('echo "\033[?25l"')
    elif sys.platform == 'linux':
        os.system('setterm -cursor off')
    elif sys.platform == 'Windows':
        pass #i don't know how to do this in Windows

def show_cursor():
    if sys.platform == 'darwin':
        os.system('echo "\033[?25h"')
    elif sys.platform == 'linux':
        os.system('setterm -cursor on')
    elif sys.platform == 'Windows':
        pass #i don't know how to do this in Windows

def get_stdout(pipe):
    while(True):
        retcode = pipe.poll() #returns None while subprocess is running
        line = pipe.stdout.readline()
        yield line
        if(retcode is not None):
            break

# to get a pressed key without the 'enter'
def getkey():
    TERMIOS = termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[3] = new[3] & ~TERMIOS.ICANON & ~TERMIOS.ECHO
    new[6][TERMIOS.VMIN] = 1
    new[6][TERMIOS.VTIME] = 0
    termios.tcsetattr(fd, TERMIOS.TCSANOW, new)
    c = None
    try:
        c = os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, TERMIOS.TCSAFLUSH, old)
    return c

#invoke bash commands
def invoke(cmd, detached = False):
    if DEBUG == True: #for debug only
        print('>>> %s <<<' % cmd)
    if detached is False:
        execution=subprocess.Popen(cmd, shell=True, bufsize = -1,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result = ""
        for line in get_stdout(execution):
            result += line
        return result
    else: #invoke bash commands in separate process, no error return
        subprocess.Popen(cmd.split(), stderr=subprocess.PIPE)
    return ""

def get_indexes(line, operator = ''):
    #space, '-' or ',' is used as separator
    if re.search('^' + operator + '\s*\d+([\s,-]+\d+)*\s*$', line):
        #expand strings like '1-3' to '1 2 3' to further get all the indexes to delete
        _tmp = re.sub('\d+[\s]*-[\s]*\d+', expand_indexes_from_range, line[len(operator):])
        return [int(x.group()) for x in re.finditer('\d+', _tmp)] #get all indexes
    else:
        return None

#helper function to prompt users information and receive answers
#this function returns either a list or a string, the caller should understand well
#what the return value could be and handle accordingly
def get_answer(title = '', prompt = '', postfix = '', default = None,
               help = '', ball = None, hl = -1, loop = True):
    if (ball and ball.help): # take the help if it is provided by the ball
        help += ball.help
    if not help: #no help is available
        help = 'No help available for this case...\n'\
             + "'/a' to add; '/d' to delete; '/m' for more\n"\
             + "'/f' to find; '/h' for help; '/e' to exit"
        _ps = PROMPT_SIGN
    else: #show colored prompt if help is available
        _ps = paint('lightblue', PROMPT_SIGN)
    while True: #loop until we have an acceptable answer
        if ball: # when a ball is given, show the item list in the ball.
            # we are drawing everything ourselves, so hide the system
            # cursor (we will draw a 'fake' one)
            hide_cursor()
            ball.paint_indexed_list(make_msg_bar(title),
                                    hl,
                                    postfix,
                                    prompt + _ps)
            _ans = ball.get_selection()
            show_cursor()
        else:
            _ans = raw_input(prompt + _ps).strip()
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
            if not loop: #quit looping, the caller will call again with updated data
                return ''
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
            if not loop: #quit looping, the caller will call again with updated data
                return ''
        elif _ans.startswith('/m') or _ans.startswith('/f'):
            return [_ans]
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

#to convert a git-relative path to relative path of the current directory
def convert_relative_path(path, root_path, cur_path):
    abs_path = root_path + '/' + path.strip()
    if not cur_path.endswith('/'):
        cur_path += '/'
    if cur_path not in abs_path: #the file is not in current directory
        common_path = os.path.commonprefix([cur_path, abs_path])
        path_diff_str = re.sub('^%s' % common_path, '', cur_path)
        path_diff = '..' + '..'.join(re.findall('/', path_diff_str))
        return re.sub(common_path, path_diff, abs_path)
    else:
        return re.sub('^%s' % cur_path, '', abs_path)

def process_git_diff_stat(raw):
    git_path = root_path()
    cur_path = os.getcwd()
    if git_path is None:
        exit_with_error("You are not in a Git repository")
    result = {}
    for line in [x.strip() for x in raw.split('\n')]:
        if line == '':
            continue
        _tmp = line.split()
        _add, _delete = _tmp[0:2]
        _file = ''.join(_tmp[2:]) #in case some filename contains space
        #convert the git-relative-path to the relative-path to current directory
        _relative_path = convert_relative_path(_file, git_path, cur_path)
        #combine files that are in the same directory
        _top_path = re.search('^[^/]+[/]*', _relative_path).group()
        if '-' == _add or '-' == _delete:# this is a binary file change, ignore
            continue
        if _top_path in result.keys():
            result[_top_path][0] += int(_add)
            result[_top_path][1] += int(_delete)
        else:
            result[_top_path] = [int(_add), int(_delete)]
    return result

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

def make_branch(branch, track_info = None):
    _parent_branch = get_current_branch()
    _tmp = invoke(git.branch(branch = branch, upstream = track_info)) #create branch with the name given
    _tmp = do_checkout_branch(target = branch) #to switch to the new branch
    _result = 'created and switched to new branch: ' + paint('red', branch) + '\n'
    copy_branch_config(branch, _parent_branch)
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

def get_active_branches(first_x = None):
    _active_branches = {}
    for b in get_branch_list()[1]:
        _active_branches[b] = invoke(git.log(num = 1,
                                             format = '%ci, %cr',
                                             param = b)).split(',')
    #sort the result by time, ignoring the 6-char ending time zone, e.g. ' +0800'
    result = sorted(_active_branches.iteritems(),
                    key = lambda(k, v): time.strptime(v[0][:-6], '%Y-%m-%d %H:%M:%S'),
                    reverse = True)
    return result[:first_x]

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
    if _tmp == '': # no configure setting available, need to create one
        _url = get_answer(prompt = 'Enter the URL of the remote repository')
        set_local('remote.origin.url', _url)
        _default_fetch = '+refs/heads/*:refs/remotes/origin/*'
        set_local('remote.origin.fetch', _default_fetch)
        set_local('branch.master.remote', 'origin')
        set_local('branch.master.merge', 'refs/heads/master')
    else:
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

months = ['Dec', 'Nov', 'Oct', 'Sep', 'Aug', 'Jul',
          'Jun', 'May', 'Apr', 'Mar', 'Feb', 'Jan',
          'Dec', 'Nov', 'Oct', 'Sep', 'Aug']
days = ['Sun', 'Sat', 'Fri', 'Thu', 'Wed', 'Tue', 'Mon',
        'Sun', 'Sat', 'Fri', 'Thu', 'Wed', 'Tue']
def get_activity_distribution(author, time = 'monthly'):
    _area_dist = ''
    _time_dist = ''
    # build the time distribution
    # we could validate the user's email by checking "git log --format='%ae',
    # but for performance consideration, we just don't check the email
    if time == 'monthly':
        _buff = invoke(git.log(authors=[author], format='%cd %h', param='--since="6 months ago"'))
        if _buff == '':
            _time_dist = '0 commits in the recent 6 months'
        else:
            _list_months = [x.split()[1] for x in _buff.split('\n') if x is not '']
            _this_month = _list_months[0]
            _index = months.index(_this_month)
            _time_dict = dict((m, _list_months.count(m)) for m in months[_index : _index + 6])
            for m in months[_index : _index + 6]:
                _time_dist += '%s: %d commits\n\t' % (m, _time_dict[m])
    elif time == 'daily':
        _buff = invoke(git.log(authors=[author], format='%cd', param='--since="7 days ago"'))
        if _buff == '':
            _time_dist = '0 commits in the recent 7 days'
        else:
            _list_days = [x.split()[0] for x in _buff.split('\n') if x is not '']
            _today = _list_days[0]
            _index = days.index(_today)
            _time_dict = dict((d, _list_days.count(d)) for d in days[_index : _index + 7])
            for d in days[_index : _index + 7]:
                _time_dist += '%s: %d commits\n\t' % (d, _time_dict[d])
    elif time == 'weekly':
        _week_buff = invoke(git.log(authors=[author], format='%cd', param='--since="1 week ago"'))
        _commits = len(_week_buff.split('\n')) - 1
        _time_dist += 'This week: %d commits \n\t' % _commits
        for w in xrange(1, 5):
            _since = '--since="%d week ago"' % (w + 1)
            _until = '--until="%d week ago"' % w
            _week_buff = invoke(git.log(authors=[author], format='%cd', param='%s %s' % (_since, _until)))
            _commits = len(_week_buff.split('\n')) - 1
            _time_dist += 'Previous %d week: %d\n\t' % (w, _commits)
            _buff += _week_buff
    # build the file distribution
    _change_len = 10 #assume there are at most 9999999999 changes to show
    first_x = 5
    _hashes = [x.split()[-1] for x in _buff.split('\n') if x is not '']
    _changed_files = ''
    for h in _hashes:
        _changed_files += invoke(git.diff(selection = '%(hash)s..%(hash)s^ --numstat' % {'hash': h},
                                 name_only = False))
    _area_dict = process_git_diff_stat(_changed_files)
    _longest_name = max([len(x) for x in _area_dict.keys()])
    _area_dist = ['%s, %s, %s' % ("Item".center(_longest_name),
                              paint('green', "Added".center(_change_len)),
                              paint('red', "Deleted".center(_change_len)))]
    _all = sorted(_area_dict.items(), key=lambda x: sum(x[1]), reverse=True)
    for k, v in _all[:first_x]:
        _area_dist.append("%s, %s, %s" % (k.ljust(_longest_name),
                                     str(v[0]).ljust(_change_len),
                                     str(v[1]).ljust(_change_len)))
    return _time_dist, _area_dist

def do_status(isremote = False, ishash = False, dir = '', compare_str = ''):
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
        if dir: #only show the touched files in the given directory
            c += ' -- ' + dir
        _tmp = invoke(c)
        _tmp = translate_status_code(c, _tmp)
        status += _tmp[:_tmp.rfind('\n')] + '\n' if _tmp else ''
    return status, compare_str

def get_file_change_distribution(num_history, first_x = None):
    _change_len = 10 #assume there are at most 9999999999 changes to show
    range = 'HEAD%s..HEAD --numstat' % ('~%s' % num_history)
    _raw = invoke(git.diff(selection = range, name_only = False))
    #print(_raw)
    _tmp = process_git_diff_stat(_raw)
    _longest_name = max([len(x) for x in _tmp.keys()])
    result = ['%s, %s, %s' % ("Item".center(_longest_name),
                              paint('green', "Added".center(_change_len)),
                              paint('red', "Deleted".center(_change_len)))]
    _all = sorted(_tmp.items(), key=lambda x: sum(x[1]), reverse=True)
    for k, v in _all[:first_x]:
        result.append("%s, %s, %s" % (k.ljust(_longest_name),
                                     str(v[0]).ljust(_change_len),
                                     str(v[1]).ljust(_change_len)))
    return result

def get_repo_age():
    _tmp = invoke(git.log(format = '%cr', param = '--reverse'))
    return re.search('^.+ago', _tmp).group()[:-4] #skip the ' ago'

def get_active_contributors(first_x = None, recent_commits = None):
    result = []
    total_commit = 0
    if recent_commits is not None:
        total_commit = recent_commits
        _tmp = {}
        #get active contributors in the recent commits
        _raw = invoke(git.log(num = recent_commits,
                              format = '%an|<%ae>'))
        for name, email in [line.split('|') for line in _raw.split('\n') if line]:
            if _tmp.has_key(name):
                _tmp[name][1] += 1
            else:
                _tmp[name] = [email, 1]
        result = sorted(_tmp.iteritems(), key = lambda(k, v): v[1], reverse = True)
        if first_x:
            result = result[:first_x]
        for record in result: #convert the commit counts to string
            record[1][1] = str(record[1][1])
    else:
        _tmp = invoke(git.shortlog(param = '-s -n -e')).split('\n')
        for line in [x.strip() for x in _tmp[:first_x]]:
            _commits = re.search('^\d+', line).group()
            _email = re.search('<.+>', line).group()
            _name = line[line.find(_commits) + len(_commits): line.find(_email)]
            result.append([_name.strip(), [_email, _commits]])
            total_commit += int(_commits)
    return total_commit, result

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

def do_log_author_or_date(ifdate, format, range, authors = []):
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
    return invoke(git.log(hash = range, format = format, authors = authors,
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
        _range = 'HEAD' + '~%d' % hash_from + '..HEAD' + ' --ancestry-path'
    else:
        _range = 'HEAD' + '~%d' % num + '..HEAD' + ' --ancestry-path'
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
    _stdout = invoke(git.rebase())
    if 'Failed to merge' in _stdout: #need manual merge
        os.system(git.mergetool())
        _tmp = 'Done'
    return _stdout

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
        #get the track info if there is any and clone it to the new branch
        try:
            _track_info = get_local("%s.TrackInfo" % get_current_branch())
        except ConfigItemMissing:
            _track_info = None
        _tmp = make_branch(target, track_info = _track_info)
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
    try:
        _track_info = get_local("branch.%s.TrackInfo" % get_current_branch())
    except ConfigItemMissing:
        _track_info = None
    _tmp =  invoke(git.checkout(target = ref, new_branch = _new_branch))
    if 'fatal: git checkout:' in _tmp: #something wrong occur when checking out
        exit_with_error(_tmp)
    _tmp += invoke(git.branch(branch = _new_branch, upstream = _track_info))
    set_local("branch.%s.TrackInfo" % _new_branch, value = _track_info)
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
        """
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
        """
        _bname = ref[ ref.rfind('/') + 1: ] #get the branch name
        _local_track = 'remotes/' + ref[ref.find('/') + 1: ]
        print("loading remote branch %s ..." % paint('red', ref))
        _result = invoke(git.fetch(url = 'origin'))
        #make a branch tracking the ref, forcing the branch name to be the same as the remote
        _result += invoke(git.checkout(new_branch = _bname, track = _local_track))
        set_local("core.CurrentBranch", value = _bname)
        #this is the first branch we check out from a remote branch, remember the track info
        set_local("branch.%s.TrackInfo" % _bname, value = _local_track)
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

def do_init():
    #show all files and prompt what to add into the initial commit
    _files = FileBall(os.listdir('.'))
    _new_files = get_answer(prompt = 'Select the files to be added into the new repository',
                            title = 'File List',
                            ball = _files)
    invoke(git.init())
    invoke(git.add(_new_files))
    #do git commit
    _msg = get_answer(prompt = 'Any comment? [empty comment is not allowed]')
    do_commit(msg = _msg)

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
def get_log_index_by_hash(hash):
    _current_hash = get_hashes(1)
    _hashes_inbetween = do_log(range = '%s..HEAD' % hash,
                               format = '%h')
    return len(_hashes_inbetween.split('\n'))

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
        _ans = get_answer(title = ' Hash List ', default = '/m', ball = _ball,
                          help = '   Enter directly or "/m" for more commits, or\n' +
                                 '   "/m <ID>" for further details of the hash, or\n' +
                                 '   "/f <commit hash>" to go to a specified commit\n')[0]
        if _ans == '/m': # to show more older commits
            until = since
            since += _group_size
        elif _ans.startswith('/m'): # to show detailed info about a commit
            _index = int(split(_ans)[-1])
            print(invoke(git.log(hash = _ball[_index], num = 1)))
            raw_input('Press Enter to continue...')
        elif _ans.startswith('/f'): # to find a specific commit
            if [] != re.findall('^/f\s*[0-9abcdef]{7,}$', _ans):
                _hash = _ans.split()[1]
                if if_hash_exist(_hash):
                    until = get_log_index_by_hash(_hash)
                    since = until + _group_size
                    # find the commit by a hash
                else:
                    #print the error and return
                    pass

            _search_hash = _ans[1:]
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
def do_file_summary(file):
    _buff = invoke(git.blame(file = file, param = '--show-stats'))
    _lines = _buff.split('\n')
    lines = len(_lines) - 4 # there are 4 extra lines other than those of the file
    _contributors = {}
    for l in _lines[:-4]: # only read the lines belong to the file
        c = re.findall('\(.+ \d{4}-\d{2}-\d{2}', l)[0]
        c = c[1:-11].strip()
        if c in _contributors.keys():
            _contributors[c] = _contributors[c] + 1
        else:
            _contributors[c] = 1
    commits = _lines[-2].split()[-1]
    top_5_contributors = sorted(_contributors.iteritems(),
                                key = operator.itemgetter(1),
                                reverse = True) [:5]
    age = 'unknown'
    return top_5_contributors, lines, commits

def number_of_changed_files(_hashes = '', _remote_branch = '', _file = ''):
    if _file:
        return 1
    _tmp = invoke(git.diff(selection = _hashes if _hashes else _remote_branch))
    return len(split(_tmp, '\n')) - 1

#return list of changed files and a list of untracked files from the output of 'git status -s'
def get_changed_files(str):
    git_path = root_path()
    cur_path = os.getcwd()
    _changed_files, _untracked_files = [], []
    if str is not None:
        _changed_pattern = '^[_MDACUT]{1,2}' #modifed/deleted/added/copied/unmerged/type_changed
        _untracked_pattern = '^\?\?.*' #untracked files
        #print(str)
        _file_list = split(str, '\n')[:-1]
        for x in _file_list:
            #TODO: FIX THE GIT PATH HERE
            #x = convert_relative_path(x, git_path, cur_path)
            #print(x)
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
        invoke('rm -fr ' + _file) #so that we could also remove directories
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
    color['reverse'] = '\033[07m'
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
    color['reverse'] = ''
    _end_ = ''


