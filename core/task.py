import os
import signal
import sys
import shutil
import json
import argparse
import re
import time


class TaskConfig():
    def __init__(self):
        self.mode = None
        self.depth = None
        self.engine = None
        self.engine_opt = None
    def parser_config(self,configfile:str,workdir:str):
        with open(configfile,'r') as f:
            lines = f.readlines()
            config_dict = {}
            for line in lines:
                line = line.strip()
                if line == '':continue
                lhs,rhs = line.split(':')
                lhs = lhs.strip()
                rhs = rhs.strip()
                if lhs == 'engine options':
                    lhs = 'engine_opt'
                if lhs == 'mode':
                    match = re.match(r'(bmc)\s*(\d+)',rhs)
                    if match:
                        rhs = match.group(1)
                        depth = int(match.group(2))
                        config_dict['depth'] = depth
                if lhs == 'timeout':
                    config_dict['timeout'] = int(rhs)
                config_dict[lhs] = rhs
            with open(f"{workdir}/config.json","w") as fjson:
                json.dump(config_dict,fjson,indent=4)
        with open(f"{workdir}/config.json",'r') as f:
            config = json.load(f)
            self.mode = config['mode']
            if self.mode == 'bmc':
                self.depth = config['depth']
            self.engine = config['engine']
            self.engine_opt = config['engine_opt']
            self.task_timeout = int(config['timeout']) if int(config['timeout']) > 0 else None

class VerifTask(TaskConfig):
    def __init__(self,configfile:str,workdir:str,earlylogs:list,logfile=None):
        super().__init__()
        self.parser_config(configfile,workdir)
        self.workdir = workdir
        self.exe_path = {
                'yosys':os.getenv('YOSYS','yosys'),
                'pono':os.getenv('PONO','pono'),
                }
        self.designdir = self.workdir + '/' + 'design'
        os.mkdir(self.designdir)
        self.tracedir = self.workdir + '/' + 'trace'
        os.mkdir(self.tracedir)
        self.logfile = logfile or open(f"{self.workdir}/logfile.txt",'a')
        self.log_targets = [sys.stdout,self.logfile]
        for log in earlylogs:
            print(log,file=self.logfile,flush=True)
        self.task_start_time = time.monotonic()
        self.task_reach_timeout = False
        self.proc_pending = []
        self.proc_running = []
        self.status = None
        self.timeout_callback = None
    
    # manage process in task
    def update_proc_pending(self,proc):
        self.proc_pending.append(proc)

    def update_proc_running(self,proc):
        self.proc_pending.remove(proc)
        self.proc_running.append(proc)

    def update_proc_stopped(self,proc):
        self.proc_running.remove(proc)

    def update_proc_canceled(self,proc):
        self.proc_pending.remove(proc)

    def handle_timeout(self,signum,frame):
            self.log(f"Task TIMEOUT:{self.task_timeout} seconds.Terminating all subprocess")
            self.status = 'TIMEOUT'
            self.terminate(timeout=True)

    def error(self,msg):
        self.status = 'ERROR'
        self.log(f"ERROR:{msg}")
        self.terminate()

    def terminate(self,timeout=False):
        if timeout:
            self.task_reach_timeout = True
        for proc in self.proc_pending:
            proc.terminate()
        for proc in self.proc_running:
            proc.terminate()
        
    def run(self):
        self.log(f"mode is {self.mode}")
        if self.mode == 'bmc':
            import bmc_mode
            bmc_mode.run(self)
        elif self.mode == 'prove':
            import prove_mode
            prove_mode.run(self)
        if self.task_timeout is not None:
            signal.signal(signal.SIGALRM,self.handle_timeout)
            signal.alarm(self.task_timeout)
        for proc in task.proc_pending:
            proc.run()
        signal.alarm(0)

    def log(self,msg):
        tm = time.localtime()
        line = "VERIF {:02d}:{:02d}:{:02d} [{}] {}".format(tm.tm_hour,tm.tm_min,tm.tm_sec,self.workdir,msg)
        for f in self.log_targets:
            print(line,file=f,flush=True)

    def make_aig(self):
        with open(f"{self.workdir}/design.ys",'w') as f:
            print("",file=f,flush=True)

        # proc = Proc.Proc()



header='''
verifiedtools run on server
'''
logmsgs = []
def log(workdir:str,msg:str):
    tm = time.localtime()
    logmsgs.append("VERIF {:02d}:{:02d}:{:02d} [{}] {}".format(tm.tm_hour,tm.tm_min,tm.tm_sec,workdir,msg))
    print(logmsgs[-1])



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=header)
    p.add_argument('configfile',help='config file',type=str)
    p.add_argument('-d','--workdir',help='set workdir',metavar='workdir',type=str)
    p.add_argument('-f','--force',help='overwite the existsed path',action='store_true')
    arg = p.parse_args()

    configfile = arg.configfile
    workdir = arg.workdir
    force = arg.force
    taskconfig = TaskConfig()
    if workdir == None:
        workdir = os.path.basename(configfile)
        workdir = os.path.splitext(workdir)[0]

    if os.path.exists(workdir):
        if not force:
            print(f"{workdir} already exists,please choose another folder,or use -f overwite the folder")
            sys.exit(-1)
        else:
            shutil.rmtree(workdir,ignore_errors=True)
    os.mkdir(workdir)
    task = VerifTask(configfile,workdir,logmsgs)
    task.log('crate workdir')
    task.log('crate veriftask')
    task.log('copy btor to design')
    shutil.copy('mycounter-false.btor2',f"{task.designdir}/design.btor")
    task.log("run task")
    # def timeout_callback(signum,frame):
    #     task.handle_timeout()
    # if task.task_timeout is not None:
    #     signal.signal(signal.SIGALRM,timeout_callback)
    #     signal.alarm(task.task_timeout)
    task.run()
    # if task.task_timeout is not None:
    #     signal.alarm(0)
    task.log('task over')
