#!python
#util
import subprocess
import logging
from logging import error,warn, debug, info
import re

trace = 0
executorImpl = None;


class ExecutorSimulate:

    def __init__(self, simlog):
        self.cmds = {}

        f = open(simlog)
        for (cmd,out) in self.ReadFile(f):
            self.cmds[cmd] = out

    def ReadFile(self,f):
        """ look for cmd in simulation file and it output as fragment of text between staert and end marker """

        out = ''
        state = 0
        for line in f:
            if state == 0:
                cmd = None
                out = ''
                m = re.match( r".*EXECUTE_CMD\:\s(.*)$", line )
                if m:
                    cmd = m.group(1)
                    #debug('found cmd %s' % cmd)
                    state = 1
            elif state == 1:
                if 'OUTPUT_BEGIN' in line:
                    state = 2
                else:
                    warn('not found OUTPUT_BEGIN')
                    break
            elif state == 2:
                if 'OUTPUT_END' in line:
                    yield cmd, out
                    state = 0
                else:
                    out += line;


    def Execute(self, cmd):
        try:
            return self.cmds[cmd]
        except KeyError:
            #raise RuntimeError('command %s not found' % cmd)
            error ('command %s not found' % cmd)

    def GetReturnCode(self):
        return 0; #success all time


class ExecutorReal:

    def __init__(self):
        returncode = 0

    def Execute(self,cmd):
        """execute a command
        the command is represented as sequence; first element of the sequence is command itself
        """

        out = ''
        err = ''
        self.returncode = 0
        try:
            p = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
            self.returncode = p.returncode
        except Exception as e:
            warn ( 'error: %s'% e )

        return out + err;

    def GetReturnCode(self):
        return self.returncode;




executorImpl = ExecutorReal() #default


def Execute(cmd):
    if trace == 1:
        debug("EXECUTE_CMD: " + cmd)
    out = executorImpl.Execute(cmd)
    info('returncode=%d' % GetReturnCode())
    if trace == 1:
        debug( "OUTPUT_BEGIN\n%sOUTPUT_END\n" % out)

    return out

def GetReturnCode():
    return executorImpl.GetReturnCode()

def SetSimLog(simlog):
    global executorImpl
    executorImpl = ExecutorSimulate(simlog)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    SetSimLog('./examples/log.txt');

    Execute('ccm task -show synopsis 43731')
    Execute('ccm task 43731 -show objs -u')

