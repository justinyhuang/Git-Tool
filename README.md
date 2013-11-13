![Git-Tool](https://raw.github.com/justinyhuang/Git-Tool/master/Git-Tool.png)  
Git, though powerful and popular, in most cases is too complicated to use. The command set is huge,
the parameters are too many, the design is sophisticated and hense the learning period is too long.
For some one who wants only a tool to manage his/her source code or document, to master Git and
make it work requires too much learning.  
(I bet most of the Git users keep a ProGit or something similar on hand)  
I have many questions since using Git:

- Why use different command for similar requests?  
- Why type long command + parameters when the requirement is simple?  
- What is 'stage'?  
- How do I know my changes are really safe?  
- Why do I have so many questions when all I need is simply to back up my work?  
    ...

This is why GitTool is here.  
GitTool tries to simplify the use of git providing simple yet powerful interfaces to the user.  
GitTool learns Git so you don't have to =)

#DEMOS
For visual folks, there are some video demos available:

- [Install Demo](http://youtu.be/LF0PA5XoRfQ)
- [GitList Demo](http://youtu.be/FzAex-pHJlE)
- [GitSave Demo](http://youtu.be/JkIRy663RYw)
- [GitStatus Demo](http://youtu.be/qzTeuVD5xp4)

#TARGET USER
GitTool is specialized for those who need to use git everyday but don't like to master the tool.  
These users only need git to help managing changes of their work, as well as communicating with
others via Git. Spending time to know 1001 ways of using git is unacceptable for them.

#FEATURES
- Easy, short yet powerful commands. In most cases a GitTool command varies from 3 to 5 characters, very few arguments are required. GitTool, in most cases, is smart enough to guess what the parameters mean, so the order of the parameters doesn't matter. Some examples are given to show how GitTool commands work: (what Git command will need to accomplish the same task?)

  To show the latest commit info  
      ```gls```

  To show the latest 3 commits info:  
      ```gls 3```

  To show commits from the 3rd to the 5th  
      ```gls 3 5```(gls 5 3 also works)

  To show the latest 3 commits by one, or several authors  
      ```gls <author1 email> <author2 email> ... 3 ```

  To show the latest 5 commits to a directory by the author  
      ```gls <author email> <directory name> 5```  
  or  
      ```gls <directory name> <author email> 5```

  To show commits' relationship in a graph for the latest 5 commits  
      ```glsg 5```

  To show commits from date1 to date2  
      ```glsd```  
  and GitTool will prompt to ask for the two dates.

  This only showcases the use of 'gls', check out 'gld', 'gsv' and other commands for much more
  exciting examples!

- One command for similar uses. You don't have to remember Git's over 20 commands for daily use.
  With GitTool, the number would be 5. Take 'gld' for example (again, think about what Git command
  will need to accomplish the same task...)

  To 'load' the latest version and apply to the current branch:  
      ```gld```

  To 'load' a local branch:  
      ```gld <branch_name>```  
  or you could do 'gldb' to pick a branch from a list of the local branches.

  To 'load' a remote branch:  
      ```gldr```  
  and pick a branch from a list of the remote branches.

  To 'load' some changes from a patch file:  
      ```gld <patch file name>```

  To 'load' new changes from another version/branch and perform a merge/rebase:  
      ```gld <version hash>/<branch name>```

  To 'load' a specific file from a given version:  
      ```gld <filename> <version name>```

  Yes, the command 'gld' does all tasks related to 'load'.  
  This is the beauty of simplicity.

- Graphic git history presentation. A slightly better graphical presentation compared to those by other tools like gitk.  
  For example, to show a graphical version tree of the last 10 nodes, 'gifg 10' will show you the graph.  
  Powered by Graphviz.

- Iterative mode. In many cases you will be give a list of branches/changed files/repositories.
  You can manipulate branches/files/repositories easily with a few key strokes.  
  In many cases you could use '/h' to get a bit more help, and anytime you could type '/e' to
  quit GitTool prompt.

- View configuration similar to ClearCase. GitTool provides a means to select files from
  different commits/versions, yet with some version control capabilities. (I am working on this)

#INSTALL
"Why do I need to install?"  
GitTool works in a way similar to 'busybox'. That is, many symbolic links pointed to the same executable. It needs to know your bin directory to put the symbolic link files. GitTool have to backup your .gitconfig file before adding GitTool specific settings later. It also will ask for your preference to using the tool after setup, for example your choices of diff tools.

The installation will take care of all above.

Installing GitTool is simple. Just run 'git_tool_box.py' directly and answer
the questions along the setup process. The tool will setup itself and ready for use.

#COLORED TEXT
During the setup process, GitTool asks if colored text is supported in your environment, with an example of colored text. We recommend saying yes if you are using a terminal that supports colored texts, as many GitTool features highlights some key contents by using different colors.

#PROMPT MODE
There are many cases where you will be asked for choices or answers when GitTool shows a line and waits for your input with a prompt (by default it is a ':>' sign). This is called the Prompt Mode in GitTool.  
GitTool enters the Prompt Mode when user intervention is required, and it tries to ask questions in the shortest way. Because as you use the tool, you become familiar with what it is asking. For new users, one can always try the

   * help command
    When in Prompt Mode, type '\h' to get help messages if there is any. In you have colored text enabled when setting up GitTool, there is an easy way to tell if help message is available:  
    There is help messages if the prompt sign changes color.(default color with help is light blue)

Or if you decide to quit instead of answering the question, use the

   * exit command
    When in Prompt Mode, type '\e' to safely exiting GitTool.  

There is yet another command that is useful in use cases like being shown a list of branches and you would like to delete one of them. That is the

   * delete command
    When in the Prompt Mode and a lost of items are shown, type '\d' followed by the index of the item to delete it, no matter what the item is: a branch, a history entry or a file shown in a diff-file list (Right! That could be 'git checkout', or 'git reset', or whatever effort you would pay to reverse a change you made to a file)

#HOWTO GET HELP
After installation, 'ghelp' will show you a list of available services with a brief description. Use 'ghelp <command>' for detailed information of the corresponding command.
You can also put a '?' after the command to get the help message, which is equal to 'ghelp \<command\>'

#I DONT LIKE IT
Your previous gitconfig is named '.gitconfig.gittool.backup' in your home directory.  
Simply remove the directories where GitTool symbolic links and git_tool_box.py reside and you won't see GitTool anymore. 

GitTool is green and uninstall is easy.  
But...why?
