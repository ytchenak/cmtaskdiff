cmtaskfiff
==========
#3DP
http://downloads.activestate.com/ActivePython/releases/2.6.4.10/ActivePython-2.6.4.10-win32-x86.msi
http://docs.activestate.com/activepython/2.6/relnotes.html
https://pyscripter.googlecode.com/files/PyScripter-v2.5.3-Setup.exe
http://www.py2exe.org/
wget http://garr.dl.sourceforge.net/project/py2exe/py2exe/0.6.9/py2exe-0.6.9.win32-py2.6.exe


wget http://garr.dl.sourceforge.net/project/unxutils/unxutils/current/UnxUtils.zip


distribution:
	dist.bat


*** How make simulation log ***
* to record: cmtaskdiff.py -vvv ... > log.txt 2>&1
* to play from log: cmtaskdiff.py ... --simlog log.txt

using:
	cmtaskdiff.py 43731

#TODO
-- create 'new' patch. applying new pathch will create the object and apply the object
 -- do not patch directory
 -- new file patch apply: create instead checkout
 -- new file patch apply: undo delete w/o replace
 -- new file pathc: remove CM header (including define)
-- python patch does not work very well... use patch    -p0 -i c:\CmTasks\46719/patch/BIM_Server.sln.patch
-- add option: show rejects list; show only .rej files
-- avoid patching R/O files. skip with error
-- refact: create repository only with task number
-- refact: integrate index with repository (make it as ObjectMetadataq). saving a obect to reporsitory coming wiht a object meadata. loading restore object metadata as well
-- refact: Executor is normal class, it can use singleton simulator. some commnad will never fo to simulator(e.g.patch). singletone impl through ::Instance method to enable use it in one module

-- patch file name should reflect new object name: to avoid name collision, e.g. ExitNotification.cpp_4_cpp_9.patch.
-- multiline search does not work. for now it is replaced to search for 'version'
-- findpath not work. return empty path. but it will be need for report and patch
-- apply patch should be more smart: use target files and not embeded file path
-- find object path: today use ccm history; find last object and find use for them. last object in history can be very old. see GetLastObject;

-- extract dir diff. save as dirname.dir
-- TODO: p4 work only wiht default diff.exe (+++ c:\CmTasks\46768\new\... - make more general
