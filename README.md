cmtaskfiff
==========
CM (Synergy) Task Diff. This script creates diff of CCM task (can be used latter for a patch)

	Usage: cmtaskdiff.exe [options] task(s)

	example: cmtaskdiff.exe 43731

	Options:
	  --version        show program's version number and exit
	  -h, --help       show this help message and exit
	  -e, --extract    extract task diff
	  -p, --patch      apply task patch
	  -i, --history    show CM history
	  -c, --checkout   checkout all task objects
	  --undo           undo (use with -c or -r)
	  -r, --relate     relate all task object to current objects
	  -l, --list       list all task objects
	  -v, --verbose    Increase verbosity (specify multiple times for more)
	  -a, --auto       no user interaction
	  --repo=REPO      set task repository
	  --target=TARGET  target directory (default: current)
	  --sim=SIMLOG     simulate from log file

Development information
-----------------------
###3DP
* http://downloads.activestate.com/ActivePython/releases/2.7.2.5/ActivePython-2.7.2.5-win32-x86.msi
* https://pyscripter.googlecode.com/files/PyScripter-v2.5.3-Setup.exe
* http://sourceforge.net/projects/pyinstaller/files/2.0/pyinstaller-2.0.zip

###How make simulation log 
	to record: cmtaskdiff.py -vvv ... > log.txt 2>&1
	to play from log: cmtaskdiff.py ... --simlog log.txt

###TODO
* updated patch implementation to new one
* create 'new' patch. applying new pathch will create the object and apply the object
* do not patch directory
* new file patch apply: create instead checkout
* new file patch apply: undo delete w/o replace
* new file pathc: remove CM header (including define)
* add option: show rejects list; show only .rej files
* avoid patching R/O files. skip with error
* re-factoring: create repository only with task number
* re-factoring: integrate index with repository (make it as ObjectMetadataq). saving a object to repository coming with a object meadata. loading restore object metadata as well
* re-factoring: Executor is normal class, it can use singleton simulator. some commnad will never fo to simulator(e.g.patch). singleton implementation through ::Instance method to enable use it in one module
* patch file name should reflect new object name: to avoid name collision, e.g. ExitNotification.cpp_4_cpp_9.patch.
* multi-line search does not work. for now it is replaced to search for 'version'
* findpath not work. return empty path. but it will be need for report and patch
* apply patch should be more smart: use target files and not embedded file path
* find object path: today use ccm history; find last object and find use for them. last object in history can be very old. see GetLastObject;
* extract dir diff. save as dirname.dir
* TODO: p4 work only wiht default diff.exe (+++ c:\CmTasks\46768\new\... - make more general
