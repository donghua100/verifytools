import os
import sys
import signal
import sys
import shutil
import json
import argparse
import re
import time
import subprocess as sp
import tempfile

import tomlkit
root_path = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(root_path)
# sys.path.append('core')
# sys.path.append('core/engine')
import Proc
from toolpath import AVRPATH,PONO,YOSYS,YOSYS_ABC,CHISEL2BTOR

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
        self.top = None
        self.file_type = 'btor'
        self.args = ''
    def aig_bmc_config(self):
        self.mode = 'bmc'
        self.depth = '10000'
        self.engine = 'abc'
        self.solver = 'btor'
        self.engine_opt = ''
        self.task_timeout = 3600
        self.top = None
        self.file_type = 'aig'
        self.args = ''

    def aig_pdr_config(self):
        self.mode = 'prove'
        self.depth = '10000'
        self.engine = 'abc'
        self.solver = 'btor'
        self.engine_opt = ''
        self.task_timeout = 3600
        self.top = None
        self.file_type = 'aig'
        self.args = ''

    def btor_bmc_config(self):
        self.mode = 'bmc'
        self.depth = '10000'
        self.engine = 'avr'
        self.solver = 'yices'
        self.engine_opt = ''
        self.task_timeout = 3600
        self.top = None
        self.file_type = 'btor'
        self.args = ''

    def btor_pdr_config(self):
        self.mode = 'prove'
        self.depth = '10000'
        self.engine = 'avr'
        self.solver = 'yices'
        self.engine_opt = ''
        self.task_timeout = 3600
        self.top = None
        self.file_type = 'btor'
        self.args = ''

    def parser_config(self, configfile:str, taskname:str):
        cfg = tomlkit.parse(open(configfile).read())
        self.mode           = cfg[taskname]['mode']
        self.engine         = cfg[taskname]['engine']
        self.solver         = cfg[taskname]['solver']
        if 'timeout' in cfg:
            self.task_timeout   = int(cfg['timeout'])
        self.file_type      = cfg['file']['type']
        if self.mode == 'bmc':
            self.depth      = cfg[taskname]['depth']
        if 'options' in cfg:
            self.engine_opt     = cfg['options']
        if cfg['file']['type'] == 'sv':
            self.top = cfg['file']['top']
        if cfg['file']['type'] == 'scala':
            self.top = cfg['file']['top']
        if cfg['file']['type'] == 'scala':
            self.args = cfg['file']['args']

    # def parser_config0(self,configfile:str,workdir:str):
    #     with open(configfile,'r') as f:
    #         lines = f.readlines()
    #         config_dict = {}
    #         for line in lines:
    #             line = line.strip()
    #             if line == '':continue
    #             lhs,rhs = line.split(':')
    #             lhs = lhs.strip()
    #             rhs = rhs.strip()
    #             if lhs == 'options':
    #                 lhs = 'engine_opt'
    #             if lhs == 'mode':
    #                 match = re.match(r'(bmc)\s*(\d+)',rhs)
    #                 if match:
    #                     rhs = match.group(1)
    #                     depth = int(match.group(2))
    #                     config_dict['depth'] = depth
    #             if lhs == 'timeout':
    #                 config_dict['timeout'] = int(rhs)
    #             if lhs == 'solver':
    #                 config_dict['solver'] = rhs
    #             # if lhs == 'top':
    #             #     config_dict['top'] = rhs
    #             config_dict[lhs] = rhs
    #         with open(f"{workdir}/config.json","w") as fjson:
    #             json.dump(config_dict,fjson,indent=4)
    #     with open(f"{workdir}/config.json",'r') as f:
    #         config = json.load(f)
    #         self.mode = config['mode']
    #         if self.mode == 'bmc':
    #             self.depth = config['depth']
    #   self.engine = config['engine']
    #   self.engine_opt = config['engine_opt']
    #         self.task_timeout = int(config['timeout']) if int(config['timeout']) > 0 else None
    #         self.file_type = config['filetype']
    #         self.solver = config['solver']
    #         # self.top = config['top']

class VerifTask(TaskConfig):
    def __init__(self,configfile:str,workdir:str,taskname:str,earlylogs:list,logfile=None,useconfig=True):
        super().__init__()
        self.taskname = taskname
        if useconfig:
            self.parser_config(configfile,taskname)
        self.workdir = workdir
        self.exe_path = {
                'yosys':os.getenv('YOSYS',YOSYS),
                'pono':os.getenv('PONO',PONO),
    'avr':os.getenv('AVR',AVRPATH),
    'yosys_abc':os.getenv('YOSYS_ABC',YOSYS_ABC),
    }
        self.chisel2btorpath = CHISEL2BTOR
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
        elif self.file_type == 'scala':
            if self.top is None:
                self.log('ERROR:scala file type must specific top module')
                return
            self.chisel2btor()
            
        else:
            shutil.copy(f"{self.srcdir}/{self.filename}.{self.file_type}",f"{self.designdir}/{self.filename}.{self.file_type}")
        self.avr_path = self.exe_path['avr']
        if self.engine == 'avrpr':
            self.make_avrpr_workers_config(self.solver)
        self.log(f"mode is {self.mode}")
        self.log(f'engine is {self.engine}')
        if self.engine == 'pono':
            from engine import engine_pono
            engine_pono.run(self)
        elif self.engine == 'avr':
            from engine import engine_avr
            engine_avr.run(self)
        elif self.engine == 'avrpr':
            from engine import engine_avrpr
            engine_avrpr.run(self)
        elif self.engine == 'abc':
            from engine import engine_abc
            engine_abc.run(self)
        else:
            assert False,f'not support engine:{task.engine}'
        

        if self.task_timeout is not None:
            signal.signal(signal.SIGALRM,self.handle_timeout)
            signal.alarm(self.task_timeout)
        for proc in self.deps:
            proc.run()
        for proc in self.proc_pending:
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

    def chisel2btor2(self):
        self.log(f"generate btor from chisel")
        src_chisel = f"{self.srcdir}/{self.filename}.{self.file_type}"
        out_btor = f"{self.designdir}/{self.filename}.btor"
        proc = Proc.Proc(self, "convert chisel to btor", f"python3 {self.chisel2btorpath} {src_chisel} {self.top} {out_btor}", 'chisel2btor.txt')
        self.deps.append(proc)
        return proc

    def chisel2btor(self):
        chisel_file = f"{self.srcdir}/{self.filename}.{self.file_type}"
        out_btor = f"{self.designdir}/{self.filename}.btor"

        instance = self.top
        args = self.args
        tmp_dir = tempfile.TemporaryDirectory()
        chisel_tmp_dir = tmp_dir.name
        # print(tmp_dir)
        # print(chisel_tmp_dir)
        shutil.copytree(CHISEL2BTOR,chisel_tmp_dir,dirs_exist_ok=True)
        chisel_dir = chisel_tmp_dir
        # print(chisel_dir)
        shutil.copy(chisel_file, chisel_dir + "/src/main/scala")
        script = f"""import chiselFv._

object Btor2Generator extends App {{
    Check.generateBtor(() => new {instance}({args}))
}}
"""
        with open(chisel_dir + "/src/main/scala/Btor2Generator.scala", 'w') as f:
            f.write(script)
        # run `sbt run Btor2Generator` in chisel_dir
        # You need to make sure there is only one Main in the project (that is, the Object that inherits from the App)
        proc = Proc.Proc(self, "convert chisel to btor", f"cd {chisel_dir}; sbt run")
        proc.run();
        # sp.run(["sbt", "run"], cwd=chisel_dir)
        
        # copy the generated btor2 file(self.chisel_dir + self.instance + _ + btor + _ + gen + self.instance + .btor2) to the current directory
        shutil.copy(f"{chisel_dir}/{instance}_btor_gen/{instance}.btor2", out_btor)
        # remove src/main/scala/Btor2Generator.scala and src/main/scala/<chisel_file>
        os.remove(chisel_dir + "/src/main/scala/Btor2Generator.scala")
        os.remove(chisel_dir + "/src/main/scala/" + chisel_file.split("/")[-1])
        shutil.rmtree(f"{chisel_dir}/{instance}_btor_gen", ignore_errors=True)
        
        return 

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
            print(f'task name: {self.taskname}',file=f,flush=True)
            print(f'verify file:{self.filename}.{self.file_type}',file=f,flush=True)
            print(f'task using time: {tot_time} sec',file=f,flush=True)
            print(f'task return status: {self.status}',file=f,flush=True)
            if self.mode == 'bmc':
                print(f'bmc steps: {self.bmc_steps}',file=f,flush=True)
            # print(f'subprocess log file in {self.logdir}',file=f,flush=True)
            # print(f'trace file in {self.tracedir}',file=f,flush=True)
        res.close()

header='''
verifiedtools run on server
'''
logmsgs = []
def log(workdir:str,msg:str):
    tm = time.localtime()
    logmsgs.append("[VERIF {:02d}:{:02d}:{:02d}] {}".format(tm.tm_hour,tm.tm_min,tm.tm_sec,msg))
    print(logmsgs[-1])


# tasks = {}
# taskRun = []
# task_idx = 0
# def run_new_task(workdir:str,cfg:str,idx:int):
#     task = VerifTask(cfg,workdir,logmsgs)
#     tasks[idx] = task
#     taskRun.append(idx)
#
# def check_task(idx:int):
#     task = tasks[idx]
#     if task.status is not None:



if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('configfile',help='config file',type=str)
    p.add_argument('-s','--srcfile',help='the file to verify',type=str,required=True)
    p.add_argument('-d','--workdir',help='set workdir',metavar='workdir',type=str)
    p.add_argument('-f','--force',help='overwite the existsed path',action='store_true')
    p.add_argument('-t','--taskname',help='specific the task name',type=str,required=True)
    arg = p.parse_args()

    configfile = arg.configfile
    workdir = arg.workdir
    force = arg.force
    taskname = arg.taskname
    taskconfig = TaskConfig()
    if workdir == None:
        workdir = f'{os.path.abspath(os.curdir)}/{taskname}'
    if os.path.exists(workdir):
        if not force:
            print(f"{workdir} already exists,please choose another folder,or use -f overwite the folder")
            sys.exit(-1)
        else:
            shutil.rmtree(workdir,ignore_errors=True)
    if  not os.path.abspath(workdir):
        workdir = f'{os.path.abspath(os.curdir)}/{workdir}'

    os.mkdir(workdir)

    task = VerifTask(configfile,workdir,taskname,logmsgs)
    srcfile = open(arg.srcfile,'r')
    srcname = os.path.basename(arg.srcfile)
    task.filename = os.path.splitext(srcname)[0]
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
