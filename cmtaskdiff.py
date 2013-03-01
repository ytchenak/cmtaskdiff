"""
CM (Synergy) Task Diff.
This script creates diff of CCM task (can be used latter for a patch)

                                                                                 example: %prog 43731
"""
import sys
sys.path.append("Lib")

import optparse
import dumper
import sys
import logging
from logging import debug,info,warn,error
import difflib
import Executor
import shutil
import os
import re
import time
import csv
import patch

class Ccm:
    def __init__(self):
        self.ccm = 'ccm'
        pass

    def ExecuteCmd(self,cmd):
        return Executor.Execute(self.ccm + ' ' + cmd)

    def GetPrevObject(self,obj):

        """ get previous object for the current object
            use ccm diff -vc and find the prev. version in the following data
            Attribute name            ECSOrderForceGui.h#1       ECSOrderForceGui.h#2
        """

        (ver, type, inst ) = obj.split(":")
        out = self.ExecuteCmd("diff -vc  " + obj);
        m = re.search(r".*version\s+(\S+)\s+", out)
        if m:
            ver_prev = m.group(1)
        else:
            return None
        obj_name = obj.split('#')[0]
        prev_obj = "%s#%s:%s:%s" % (obj_name,ver_prev,type,inst)
        return prev_obj;


    def GetLastObject(self,obj):
        """ get last object for the current object
            use ccm history and find the last version
        """
        (ver, type, inst ) = obj.split(":")
        out = self.ExecuteCmd("history %s" % obj)
        m = re.search( r".*Object:\s+(\S+)", out, re.S ) #find last occurent
        if m:
            ver_last = m.group(1)
        prev_obj = "%s:%s:%s" % (ver_last,type,inst)
        return prev_obj

    def GetObjectPath(self,obj):
        """ get object path in file system
        alg: get last object in the object history and find use this object in some projects
        sometimes such project is not found, in this case the path will included only short file name
        """

        path = None
        last_obj = self.GetLastObject(obj)
        if last_obj:
            out = self.ExecuteCmd("finduse %s" % last_obj)
            m = re.search( r"(\S+)#[\d.\.]+@", out )
            if m:
                path = m.group(1)
            else:
                    path = self.GetObjectFilename(obj) #path is not found, take short file name as object path
        return path

    def GetObjectFilename(self,obj):
        m = re.search( r"(\S+)#", obj )
        filename = ''
        if m:
            filename = m.group(1)
        return filename

    def GetObjectType(self,obj):
        m = re.search( r"\:(\w+)\:", obj )
        typename = ''
        if m:
            typename = m.group(1)
        return typename



    def GetObjectContext(self,obj):
        text = self.ExecuteCmd("cat " + obj)
        return text;

    def GetObjects(self,task):
        objs = []
        objs_out = self.ExecuteCmd("task %s -show objs -u" % (task))
        if not objs_out:
            return objs #return empty object list

        for s in objs_out.split('\n'):
            if s:
                objs.append( s.split()[0] )
        return objs


    def GetTaskName(self,task):
        task_name = self.ExecuteCmd("task -show synopsis %s" % task);
        return task_name

    def ShowObjectHistory(self,obj):
        self.ExecuteCmd("history -g %s" % obj);


    def Checkout(self,obj):
        return self.ExecuteCmd("checkout %s" % obj);

    def DeleteReplace(self,obj):
        return self.ExecuteCmd("delete -replace %s" % obj);

    def Relate(self, prev_obj,cur_obj):
        return self.ExecuteCmd("relate /name successor /from %s  /to %s" % (prev_obj,cur_obj) );

    def UnRelate(self, prev_obj,cur_obj):
        return self.ExecuteCmd("unrelate /name successor /from %s  /to %s" % (prev_obj,cur_obj) );

    def IsCmAlive(self):
        self.ExecuteCmd("delimiter")
        return Executor.GetReturnCode() == 0

class PatchCreator:
    '''
    -------------------------------------------------------------------------
    create an unified patch from old to new file
    ----------------------------------------------------------------------------
    '''

    def FixPatchFileNames(self,patch_text, path):
        '''get path ready to path'''
        ##TODO: so we need it?

        if path == None: return None

        head = "diff -u %s %s\n" % (path,path)
        head += "--- %s\n+++ %s\n" % (path,path)

        patch_fix = patch_text
        re.sub( r".*\n.*\n", head, patch_fix)
        return patch_fix;

    def FixPatch(self,patch_text):
        #remove CCM header
        patern = re.compile(r"@@.*?\%date_created:.*?@@", re.DOTALL)
        patch_text = re.sub(patern, "@@", patch_text)

        #remove CCM version mark
        patern = re.compile(r"@@.*?@\(#\).*?@@", re.DOTALL)
        patch_text = re.sub(patern, "@@", patch_text)
        return patch_text

    def MakePatchWithGnuDiff(self,fp_old, fp_new, obj_info):
        patch_text = Executor.Execute('diff -u {0} {1}' .format(fp_old, fp_new))
        #patch_text = "\n".join(patch_text.splitlines()) + "\n"
        return patch_text

    def MakePatchWithDifflib(self,fp_old, fp_new, obj_info):
        text_old = open(fp_old).read()
        text_new = open(fp_new).read()
        patch_text = difflib.unified_diff(
            text_old.splitlines(),
            text_new.splitlines(),
            obj_info.obj_curr,
            obj_info.obj_path,
            lineterm='\n'
            )
        patch_text = "\n".join(patch_text) + "\n"
        return patch_text

    def MakePatch(self,fp_old, fp_new, obj_info):
##        patch_text = self.MakePatchWithDifflib(fp_old, fp_new, obj_info)
        patch_text = self.MakePatchWithGnuDiff(fp_old, fp_new, obj_info)
        patch_text = self.FixPatch(patch_text)
        return patch_text
class PatchApplyer:
    def __init__(self):
        pass

    def ApplyWithGnuPatch(self,patch_file, target_dir, obj_info):
        fnp_obj = os.path.join(target_dir,obj_info.obj_path)
        info('patching %s' % fnp_obj)
        if os.path.exists( fnp_obj + '.orig'):
            os.remove(fnp_obj + '.orig')
        if os.path.exists( fnp_obj + '.rej'):
            os.remove(fnp_obj + '.rej')

        #TODO: -p4 work only wiht default diff.exe (+++ c:\CmTasks\46768\new\... - make more general
        out = Executor.Execute('patch.exe -p4 -d {0} -i {1} ' .format(target_dir, patch_file));
        if Executor.GetReturnCode() == 0:
            self.Result = 0
        elif Executor.GetReturnCode() == 1:
            if out.find('Reversed (or previously applied) patch detected!') > 0:
                #os.remove(fnp_obj + '.rej') #no need to know details, all was rejected
                self.Result = 1
            elif out.find("can't find file to patch") >= 0:
                self.Result = 2
            elif out.find("FAILED at") >= 0:
                self.Result = 3
            else:
                self.Result = 9
        elif Executor.GetReturnCode() == 2:
                self.Result = 10
        elif Executor.GetReturnCode() == 3:
                self.Result = 11
        else:
            self.Result = 99

        # we do not need orig...
        if os.path.exists( fnp_obj + '.orig'):
            os.remove(fnp_obj + '.orig')


    def ApplyWithPythonPatch(self, fnp_patch, target_dir, obj_info):
        os.chdir(target_dir)
        p = patch.fromfile(fnp_patch)
        p.apply()
        self.Result = 0

    def Apply(self,patch_file, target_dir, obj_info):
        ''' simulate the behavior of patch utility
            change the current dir to target dir
            perform patching from patch file to target file
            targt file will be taken from patch file
        '''
        debug('patch from {0} in {1}' .format(patch_file, target_dir))
#        self.ApplyWithPythonPatch(patch_file, target_dir,obj_info)
        self.ApplyWithGnuPatch(patch_file, target_dir,obj_info)

class Repository:
    """
        manage one task repository
    """

    rootDir = os.path.abspath( "c:/CmTasks" )

    def __init__(self):
        pass

    def MakeDir(self,dir):
        try:
            os.makedirs(dir)
        except OSError, e:
            # be h  appy if someone already created the path
            #if e.errno != errno.EEXIST:
            #    raise
            pass

    def SetTaskDir(self, taskDir):
        self.taskDir = os.path.join(Repository.rootDir,taskDir)


    def Clean(self):
        shutil.rmtree(self.taskDir, ignore_errors=True )
        self.MakeDir(self.taskDir)
##        self.MakeDir(self.taskDir + '/' + 'old')
##        self.MakeDir(self.taskDir + '/' + 'new')
##        self.MakeDir(self.taskDir + '/' + 'patch')


    def SaveTextToFile(self,filename, text):
        fullPathname = os.path.join(self.taskDir,filename)
        debug('saved to ' + fullPathname )
        d = os.path.dirname(fullPathname)
        debug('creating in %s' % d)
        if not os.path.exists(d):
            os.makedirs(d)
        debug('save text to file ' + fullPathname)
        fh = open (fullPathname,'w')
        text = "\n".join(text.splitlines()) + "\n"
        fh.write(text)
        fh.close()

    def LoadTextFromFile(self,filename):
        text = ''
        fullPathname = os.path.join(self.taskDir,filename)
        debug('load text from file' + fullPathname)
        fh = open(fullPathname,'r')
        text = fh.read()
        fh.close()
        return text
class Index:
    """ task Index """

    indexName = '_index.csv'

    class Record:
        def __init__(self):
            self.obj_curr = ''
            self.obj_type = ''
            self.fn_curr = ''
            self.fn_patch = ''
            self.obj_path = ''
            self.obj_prev = ''
            self.fn_prev = ''

    def __init__(self):
        self.taskname = ''
        self.records = []

    def Save(self, taskdir):
        filename = os.path.join(taskdir,self.indexName)
        debug('save index to ' + filename)
        csv_writer = csv.writer(open(filename, 'wb'))
        csv_writer.writerow([self.taskname])
        csv_writer.writerow(['Number',
        'Object',
        'Type',
        'Filename',
        'Patch',
        'FullPath',
        'ObjPrev',
        ])
        for i,r in enumerate(self.records,1):
            csv_writer.writerow([i,
                r.obj_curr,
                r.obj_type,
                r.fn_curr,
                r.fn_patch,
                r.obj_path,
                r.obj_prev,
                ])

    def Load(self,taskdir):
        filename = os.path.join(taskdir, self.indexName)
        self.records = []
        debug('load index from ' + filename)
        csv_reader = csv.reader(open(filename, "rb"))
        self.taskname = csv_reader.next()[0]
        csv_reader.next() #skip header

        for fields in csv_reader:
            r = Index.Record()
            r.obj_curr   = fields[1]
            r.obj_type   = fields[2]
            r.fn_curr    = fields[3]
            r.fn_patch   = fields[4]
            r.obj_path   = fields[5]
            r.obj_prev   = fields[6]
            self.records.append(r)

        debug('index records = %d' % len(self.records) )
class Differ:

    def __init__(self):
        self.deltas = []
        pass



    def ExtractFromCm(self,ccm,task,repository):
        ''' extract current and previous file version of task's files'''

        index = Index()
        index.taskname = ccm.GetTaskName(task)
        objs = ccm.GetObjects(task)
        for obj_curr in objs:
            r = Index.Record()
            r.obj_curr = obj_curr
            r.obj_path = ccm.GetObjectPath( obj_curr)
            r.fn_curr = ccm.GetObjectFilename( obj_curr )
            r.obj_type = ccm.GetObjectType( obj_curr )
            debug( 'object '+  obj_curr+ ' has type '+ r.obj_type )
            if r.obj_type != 'dir':
                text_curr = ccm.GetObjectContext( obj_curr )
                p_new = os.path.join("new",r.obj_path)
                repository.SaveTextToFile( p_new, text_curr  )
                info('make patch for ' + r.obj_path)
                print('processing ' + r.obj_path)
                r.obj_prev = ccm.GetPrevObject( obj_curr )
                if r.obj_prev != None:
                    text_prev = ccm.GetObjectContext( r.obj_prev )
                    r.fn_prev = ccm.GetObjectFilename( r.obj_prev )
                    p_old = os.path.join("old",r.obj_path)
                    repository.SaveTextToFile( p_old, text_prev  )
                    patchCreator = PatchCreator()
                else:
                    r.obj_prev = 'None'
                    r.fn_prev = 'None'
                    text_prev = ''

                fp_old = os.path.join(repository.taskDir, p_old)
                fp_new = os.path.join(repository.taskDir, p_new)
                text_patch = patchCreator.MakePatch(fp_old, fp_new, r)
                r.fn_patch = ccm.GetObjectFilename( obj_curr ) + ".patch"
                p_patch = os.path.join("patch", r.fn_patch)
                repository.SaveTextToFile( p_patch, text_patch  )
            #endif
            index.records.append(r)
        #endfor
        index.Save(repository.taskDir)
def GetCli():
    usage = "%prog [options] task(s), -h for help"
    parser = optparse.OptionParser(
      usage=usage,
      description=__doc__,
      epilog="",
      version="%prog 0.5.1"
      )

    parser.add_option('-e', '--extract',   action='store_const', dest='mode', const='extract', help='extract task diff',)
    parser.add_option('-p', '--patch',  action='store_const', dest='mode', const='patch', help='apply task patch',)
    parser.add_option('-i', '--history',  action='store_const', dest='mode', const='history', help='show CM history',)
    parser.add_option('-c', '--checkout',  action='store_const', dest='mode', const='checkout', help='checkout all task objects',)
    parser.add_option('', '--undo',  action='store_true', dest='undo', help='undo (use with -c or -r)',)
    parser.add_option('-r', '--relate',  action='store_const', dest='mode', const='relate', help='relate all task object to current objects',)
    parser.add_option('-l', '--list',  action='store_const', dest='mode', const='list', help='list all task objects',)

    parser.add_option('-v','--verbose', dest='verbose', action='count',   help="Increase verbosity (specify multiple times for more)")
    parser.add_option('-a','--auto', dest='auto', action='store_true',   help="no user interaction")

    parser.add_option("", "--repo",                          help='set task repository')
    parser.add_option('', '--target', help='target directory (default: current)',)
    parser.add_option('','--sim', dest='simlog',   help="simulate from log file")


    (options, args) = parser.parse_args()

    if options.target == None:
        options.target = '.' #defualt

    #dumper.dump(options)

    log_level = logging.WARNING # default
    if options.verbose == 1:
        log_level = logging.INFO
    if options.verbose > 1:
        log_level = logging.DEBUG
    if options.verbose > 2:
        Executor.trace = 1

    logging.basicConfig(level=log_level,
      #format="%(name)s %(levelname)-5s %(message)s"
      format="%(funcName)s (%(filename)s:%(lineno)d): %(message)s"
      )

    logging.debug('parsing...')
    logging.debug('get:' +    str(options))

    if len(args) == 0:
        parser.error('wrong number of arguments')

    return (options, args)

def DoExtract(task):
    ccm = Ccm()

    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository.Clean()

    differ = Differ()
    differ.ExtractFromCm(ccm,task,repository)

def DoApplyPatch(task, target_dir, auto):
    debug('applying patch for task %s to directory %s' % (task,target_dir))

    info( 'current dir is ' + os.path.abspath('.') )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    for r in index.records:
        if r.obj_type == 'dir':
            continue # no patch for directory
        fnp_patch = os.path.join(repository.taskDir,'patch',r.fn_patch)
        p = PatchApplyer()
        p.Apply(fnp_patch, target_dir, r)
        if p.Result == 0:
            print 'successfully patched', r.obj_path
        elif p.Result == 1:
            print 'already patched', r.obj_path
        elif p.Result == 2:
            print 'target not found', r.obj_path
        elif p.Result == 3:
            print 'partial patched', r.obj_path
        elif p.Result == 9:
            print 'error', r.obj_path
        elif p.Result == 10:
            print 'file error', r.obj_path
        elif p.Result == 11:
            print 'bad patch', r.obj_path

        if not auto:
            ccm = Ccm();
            ccm.ShowObjectHistory(r.obj_curr)
            raw_input('enter to continue')

def DoShowHistory(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )

    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();
    print("Showing history of task %s, press enter key for continue" % task)
    for r in index.records:
        ccm.ShowObjectHistory(r.obj_curr)
        raw_input(r.fn_curr)

def DoCheckout(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();

    print("Checkout...")
    for r in index.records:
        print ccm.Checkout(r.obj_path),

def DoUndoCheckout(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();

    for r in index.records:
        obj_work = ccm.GetLastObject(r.obj_curr)
        #ccm.UnRelate(r.obj_curr, obj_work) -- TODO canno make blind, can remove wrong dep. recheck!
        print ccm.DeleteReplace(r.obj_path),

def DoRelate(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();

    for r in index.records:
        obj_work = ccm.GetLastObject(r.obj_curr)
        print ccm.Relate(r.obj_curr, obj_work)

def DoUndoRelate(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();

    for r in index.records:
        obj_work = ccm.GetLastObject(r.obj_curr)
        print ccm.UnRelate(r.obj_curr, obj_work)

def DoListTask(task):
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    repository = Repository()
    repository.SetTaskDir('%s' % task )
    index = Index()
    index.Load(repository.taskDir)
    ccm = Ccm();

    for r in index.records:
        print r.obj_path
def CheckIfCmAllive():
    cm = Ccm()
    if not cm.IsCmAlive():
        print "Error: cannot connect to CCM. Ensure that ccm in PATH and CCM engine is up\n"
        sys.exit(1)
def main():

    (options, args) = GetCli()
    if not options:
      return 0;

    ##Debug
    if options.simlog:
      Executor.SetSimLog(options.simlog)

    CheckIfCmAllive()
    #print os.path.dirname(os.path.abspath(sys.argv[0]))

    tasks = args
    for task in tasks:
        if options.mode == 'diff' or options.mode == None:
            DoExtract(task)
        elif options.mode == 'patch':
            DoApplyPatch(task, options.target, options.auto)
        elif options.mode == 'history':
            DoShowHistory(task)
        elif options.mode == 'checkout':
            DoCheckout(task)
        elif options.mode == 'list':
            DoListTask(task)
        elif options.mode == 'checkout' and options.undo:
            DoUndoCheckout(task)
        elif options.mode == 'relate' and options.undo:
            DoUndoRelate(task)
        elif options.mode == 'relate':
            DoRelate(task)
        else:
            print 'unsupported option'

if __name__ == '__main__':
    main()

