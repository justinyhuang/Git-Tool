import pdb

def diff(selection = '', name_only = True, type = 'ACDMRTUXB*'):
    return 'git diff %s %s %s' % (selection,
                                  '--name-only' if name_only else '',
                                  '--diff-filter=%s' % type if type else '')

def difftool(difftool, hashes, remote_branch, file):
    return 'git difftool -y -t %(t)s %(h)s %(r)s %(f)s' %\
           {'t': difftool, 'h': hashes, 'r': remote_branch, 'f': file}

def log(hash = '', num = 0, format = '', param = ''):
    return 'git log %(num)s %(hash)s %(format)s %(other)s' %\
          {'num': ('-%d' % num) if num > 0 else '',
           'hash': hash if hash else '',
           'format': ("--format='%s'" % format) if format else '',
           'other': param if param else ''}

def patch(selection, patch_file):
    _param = selection
    _param += (' > %s' % patch_file) if patch_file else ''
    return 'git format-patch -k --stdout %s' % _param

def clone(param):
    return 'git clone ' + param

def fetch(url = '', src = '', dst = ''):
    _param = ('%(source)s:%(local)s' % {'source':src, 'local':dst})\
             if src and dst else ''
    return 'git fetch %s %s' % (url, _param)

def checkout(target = '', new_branch = '', track = ''):
    _param = target
    _param += (' -b %s' % new_branch) if new_branch else ''
    _param += (' -t %s' % track) if track else ''
    return 'git checkout %s' % _param

def merge(param = ''):
    return 'git merge %s' % param

def mergetool(param = ''):
    return 'git mergetool %s' % param

def branch(lsoption = None, del_branch = '', force_del_branch = '',
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

def push(repo, branch, ref, param = ''):
    return 'git push %s %s:%s %s' % (repo, branch, ref, param)

def rebase(param = ''):
    return 'git rebase %s' % param

def status(param = ''):
    return 'git status %s' % param

def showref(branch = ''):
    return 'git show-ref -s %s' % branch

def show(selection = '', param = '', file = ''):
    return 'git show %s %s %s' % (selection, param, file)

def config(type = '', section = '', element = '', value = None, exp = None):
    if exp: #for querying config items via a regular expression
        return 'git config --get-regexp %s' % exp
    if value: #set function to an element, you can't set value of a section, can you?
        return 'git config --local %s "%s"' %(element, value) if type == 'local'\
          else 'git config --global %s "%s"' %(element, value)
    elif value == '': #remove a section, or an element
        if element:
            return 'git config --local --unset %s' % section if type == 'local'\
              else 'git config --global --unset %s' % section
        if section:
            return 'git config --local --remove-section %s' % section if type == 'local'\
              else 'git config --global --remove-section %s' % section
    else: #get function, when value is None
        return 'git config --local %s' % element if type == 'local'\
          else 'git config --global %s' % element

def revparse(hash = '', param = ''):
    return 'git rev-parse %s %s' % (hash, param)

def reset(file):
    return 'git reset %s' % file

def remote(param):
    return 'git remote %s' % param

def commit(param):
    return 'git commit %s' % param

def lsremote(url, branch):
    return 'git ls-remote %s %s' % (url, branch)

def apply(patch_file, check = False):
    return 'git apply %s %s' % ('--check' if check else '', patch_file)

def add(file):
    return 'git add %s' % file
