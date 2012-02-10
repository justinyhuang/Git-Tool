def diff(selection = '', name_only = True):
    return 'git diff %s %s' % (selection, '--name-only' if name_only else '')

def log(version = '', num = 0, format = '', param = ''):
    return 'git log %(num)s %(version)s %(format)s %(other)s' %\
          {'num': ('-%d' % num) if num > 0 else '',
           'version': version if version else '',
           'format': ("--format='%s'" % format) if format else '',
           'other': param if param else ''}

def patch(selection, patch_file):
    _param = selection
    _param += (' > %s' % patch_file) if patch_file else ''
    return 'git format-patch -k --stdout %s' % _param

def clone(param):
    return 'git clone ' + param

def fetch(repo = '', src = '', dst = ''):
    _param = ('%(source)s:%(local)s' % {'source':src, 'local':dst})\
             if src and dst else ''
    return 'git fetch %s %s' % (repo, _param)

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

def push(repo, branch, ref):
    return 'git push %s %s:%s' % (repo, branch, ref)

def rebase(param = ''):
    return 'git rebase %s' % param

def status(param = ''):
    return 'git status %s' % param

def showref(branch = ''):
    return 'git show-ref -s %s' % branch

def config(config = '', section = '', value = ''):
    if value: #set function
        return 'git config --local %s "%s"' %(section, value) if config == 'local'\
          else 'git config --global %s "%s"' %(section, value)
    else: #get function
        return 'git config --local %s' % section if config == 'local'\
          else 'git config --global %s' % section

def revparse(version = '', param = ''):
    return 'git rev-parse %s %s' % (version, param)

def reset(file):
    return 'git reset %s' % file

def remote(param):
    return 'git remote %s' % param

def commit(param):
    return 'git commit %s' % param
