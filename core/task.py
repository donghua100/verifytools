import os
import signal
import sys
import shutil
import json
import argparse
import re
import time
import Proc
from toolpath import AVRPATH,PONO

class TaskConfig():
    def __init__(self):
        mode_default = 'bmc'
        depth_default = '1000'
        engine_default = 'pono'
        solver_default = 'btor'
        engine_opt_default=''
        self.mode = mode_default
        self.depth = depth_default
        self.engine = engine_default
        self.solver = solver_default
        self.engine_opt = engine_opt_default
        self.task_timeout = None
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
                if lhs == 'options':
                    lhs = 'engine_opt'
                if lhs == 'mode':
                    match = re.match(r'(bmc)\s*(\d+)',rhs)
                    if match:
                        rhs = match.group(1)
                        depth = int(match.group(2))
                        config_dict['depth'] = depth
                if lhs == 'timeout':
                    config_dict['timeout'] = int(rhs)
                if lhs == 'solver':
                    config_dict['solver'] = rhs
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
            self.file_type = config['filetype']
            self.solver = config['solver']

class VerifTask(TaskConfig):
    def __init__(self,configfile:str,workdir:str,earlylogs:list,logfile=None):
        super().__init__()
        self.parser_config(configfile,workdir)
        self.workdir = workdir
        self.exe_path = {
                'yosys':os.getenv('YOSYS','yosys'),
                'pono':os.getenv('PONO',PONO),
                'avr':os.getenv('AVR',AVRPATH),
                }
        self.avr_path = ''
        self.designdir = self.workdir + '/' + 'design'
        os.mkdir(self.designdir)
        self.tracedir = self.workdir + '/' + 'trace'
        os.mkdir(self.tracedir)
        self.srcdir = self.workdir + '/' + 'src'
        os.mkdir(self.srcdir)
        self.logdir = self.workdir + '/' + 'log'
        os.mkdir(self.logdir)
        

        self.logfile = logfile or open(f"{self.workdir}/logfile.txt",'a')
        self.log_targets = [sys.stdout,self.logfile]
        for log in earlylogs:
            print(log,file=self.logfile,flush=True)
        self.task_start_time = time.monotonic()
        self.task_reach_timeout = False
        self.deps = []
        self.proc_pending = []
        self.proc_running = []

        # [UNSAFE,SAFE,UNKNOWN,TIMEOUT]
        self.status = None
        self.timeout_callback = None
        self.filename = None
        self.top = None
        self.bmc_steps = 0
    
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

    def terminate(self,timeout=False):
        if timeout:
            self.task_reach_timeout = True
        for proc in self.proc_pending:
            proc.terminate()
        for proc in self.proc_running:
            proc.terminate()
        
    def run(self):
        if self.file_type == 'sv':
            if self.top is None:
                self.log('ERROR:sv file type must specific top module')
                return 
            self.make_btor()
            self.make_aig()
        else:
            shutil.copy(f"{self.srcdir}/{self.filename}.{self.file_type}",f"{self.designdir}/{self.filename}.{self.file_type}")
        self.avr_path = self.exe_path['avr']
        if self.engine == 'avrpr':
            self.make_avrpr_workers_config(self.solver)
        self.log(f"mode is {self.mode}")
        self.log(f'engine is {self.engine}')
        if self.mode == 'bmc':
            import bmc_mode
            bmc_mode.run(self)
        elif self.mode == 'prove':
            import prove_mode
            prove_mode.run(self)
        if self.task_timeout is not None:
            signal.signal(signal.SIGALRM,self.handle_timeout)
            signal.alarm(self.task_timeout)
        for proc in task.deps:
            proc.run()
        for proc in task.proc_pending:
            proc.run()
        signal.alarm(0)

    def log(self,msg):
        tm = time.localtime()
        line = "[VERIF {:02d}:{:02d}:{:02d}] {}".format(tm.tm_hour,tm.tm_min,tm.tm_sec,msg)
        for f in self.log_targets:
            print(line,file=f,flush=True)

    def make_aig(self):
        self.log(f"generate yosys scripts in {self.designdir}/{self.filename}_aig.ys to make aig")
        with open(f"{self.designdir}/{self.filename}_aig.ys",'w') as f:
            print(f"read -formal {self.workdir}/src/{self.filename}.sv",file=f,flush=True)
            print(f"prep -top {self.top}",file=f,flush=True)
            print("flatten",file=f,flush=True)
            print("memory -nordff",file=f,flush=True)
            print("setundef -undriven -init -expose",file=f,flush=True)
            print("delete -output",file=f,flush=True)
            print("techmap",file=f,flush=True)
            print("abc -fast -g AND",file=f,flush=True)
            print(f"write_aiger -zinit {self.designdir}/{self.filename}.aig",file=f,flush=True)
        proc = Proc.Proc(self,"make aig",f"{self.exe_path['yosys']} {self.designdir}/{self.filename}_aig.ys",'make_aig.txt')
        self.deps.append(proc)
        return proc

    def make_btor(self):
        self.log(f"generate yosys scripts in {self.designdir}/{self.filename}_btor.ys to make btor")
        with open(f"{self.designdir}/{self.filename}_btor.ys",'w') as f:
            print(f"read -formal {self.workdir}/src/{self.filename}.sv",file=f,flush=True)
            print(f"prep -top {self.top}",file=f,flush=True)
            print("hierarchy -check",file=f,flush=True)
            print("chformal -assume -early",file=f,flush=True)
            print("memory -nomap",file=f,flush=True)
            print("flatten",file=f,flush=True)
            print("setundef -undriven -expose",file=f,flush=True)
            print(f"write_btor {self.designdir}/{self.filename}.btor",file=f,flush=True)
        proc = Proc.Proc(self,"make btor",f"{self.exe_path['yosys']} {self.designdir}/{self.filename}_btor.ys",'make_btor.txt')
        self.deps.append(proc)
        return proc
    def make_avrpr_workers_config(self,slv):
        self.log(f"generate default worker config file for avrpr engine in {self.workdir}/workers.txt")
        with open(f'{self.workdir}/workers.txt','w') as f:
            print(f'python3 avr.py --bin build/bin_{slv}',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa --kind',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa --bmc',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --split',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa8',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa16',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --abstract sa32',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --level 0',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --level 5',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --interpol 1',file=f,flush=True)
            print(f'python3 avr.py --bin build/bin_{slv} --forward 1',file=f,flush=True)


    
    def exit_callback(self):
        tot_time = int(time.monotonic()-self.task_start_time)
        res = open(f'{self.workdir}/results.txt','w')
        for f in [res,sys.stdout]:
            print(f'verify file:{self.filename}.{self.file_type}',file=f,flush=True)
            print(f'task using time: {tot_time} sec',file=f,flush=True)
            print(f'task return status: {self.status}',file=f,flush=True)
            if self.mode == 'bmc':
                print(f'bmc steps: {self.bmc_steps}',file=f,flush=True)
            print(f'subprocess log file in {self.logdir}',file=f,flush=True)
            print(f'trace file in {self.tracedir}',file=f,flush=True)
        res.close()

header='''
verifiedtools run on server
'''
logmsgs = []
def log(workdir:str,msg:str):
    tm = time.localtime()
    logmsgs.append("[VERIF {:02d}:{:02d}:{:02d}] {}".format(tm.tm_hour,tm.tm_min,tm.tm_sec,msg))
    print(logmsgs[-1])



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=header)
    p.add_argument('configfile',help='config file',type=str)
    p.add_argument('-s','--srcfile',help='the file to verify',type=str,required=True)
    p.add_argument('-d','--workdir',help='set workdir',metavar='workdir',type=str)
    p.add_argument('-f','--force',help='overwite the existsed path',action='store_true')
    p.add_argument('-t','--top',help='specific the top module for sv file',type=str,default=None)
    arg = p.parse_args()

    configfile = arg.configfile
    workdir = arg.workdir
    force = arg.force
    taskconfig = TaskConfig()
    if workdir == None:
        workdir = os.path.basename(configfile)
        workdir = os.path.splitext(workdir)[0]
        workdir = f'{os.path.abspath(os.curdir)}/{workdir}'

    if os.path.exists(workdir):
        if not force:
            print(f"{workdir} already exists,please choose another folder,or use -f overwite the folder")
            sys.exit(-1)
        else:
            shutil.rmtree(workdir,ignore_errors=True)
    os.mkdir(workdir)

    task = VerifTask(configfile,workdir,logmsgs)
    if task.file_type == 'sv' and arg.top is None:
        task.log('ERROR:sv file type must specific top module')
    srcfile = open(arg.srcfile,'r')
    srcname = os.path.basename(arg.srcfile)
    task.filename = os.path.splitext(srcname)[0]
    task.top = arg.top
    destfile = open(f"{task.srcdir}/{task.filename}.{task.file_type}","w")
    destfile.write(srcfile.read())
    srcfile.close()
    destfile.close()
    task.log('crate workdir')
    task.log('crate veriftask')
    task.log(f'write srcfile to {task.srcdir}/{task.filename}.{task.file_type}')
    # shutil.copy('mycounter-false.btor2',f"{task.designdir}/design.btor")
    task.log("run task")
    task.run()
    task.log('task over')
    task.exit_callback()
