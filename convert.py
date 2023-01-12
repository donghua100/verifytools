import subprocess as sp
import signal
import shutil
import os
import tempfile
from setting import YOSYS,CHISEL2BTOR
class Convert():
    def __init__(self, workdir, srcfile, top, args = None):
        self.workdir = workdir
        self.srcfile = srcfile
        self.filename = os.path.basename(srcfile)
        # print(self.filename,srcfile)
        self.filename, self.type  = os.path.splitext(self.filename)
        self.type = self.type[1:]
        # print(self.filename)
        if self.type == 'btor2':
            self.type = 'btor'
        self.designdir = f"{workdir}/design"
        self.top = top
        self.args = args
        self.exe_path = {
                'yosys':os.getenv('YOSYS',YOSYS),
                }
        if not os.path.exists(self.designdir):
            os.mkdir(self.designdir)
        # shutil.copy(srcfile,self.designdir)
        self.srcfile = f"{self.designdir}/{self.filename}.{self.type}"
        self.outaig = f"{self.designdir}/{self.filename}.aig"
        self.outbtor = f"{self.designdir}/{self.filename}.btor"
        shutil.copy(srcfile,self.srcfile)
        # print(srcfile,self.srcfile)
        if self.type == 'sv' or self.type == 'v':
            self.make_aig()
            self.make_btor()
        elif self.type == 'scala':
            self.chisel2btor()
    def make_aig(self):
        with open(f"{self.designdir}/{self.filename}_aig.ys",'w') as f:
            print(f"read -formal {self.designdir}/{self.filename}.{self.type}",file=f,flush=True)
            print(f"prep -top {self.top}",file=f,flush=True)
            print("flatten",file=f,flush=True)
            print("memory -nordff",file=f,flush=True)
            print("setundef -undriven -init -expose",file=f,flush=True)
            print("delete -output",file=f,flush=True)
            print("techmap",file=f,flush=True)
            print("abc -fast -g AND",file=f,flush=True)
            print(f"write_aiger -zinit {self.designdir}/{self.filename}.aig",file=f,flush=True)
        def preexec_fn():
            # self.task.log(f'IN PREEXEC_FN,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.setpgrp()
            # self.task.log(f'SET pgrp,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
        cmd = f"{self.exe_path['yosys']} {self.designdir}/{self.filename}_aig.ys"
        proc = sp.Popen(['/usr/bin/env','bash','-c',cmd],stdin=sp.DEVNULL,stdout=sp.PIPE,
                stderr=sp.STDOUT,preexec_fn=preexec_fn)

        while  proc.poll() == None:
            pass
        
        return 


    def chisel2btor(self):
        chisel_file = self.srcfile
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
        def preexec_fn():
            # self.task.log(f'IN PREEXEC_FN,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.setpgrp()
        cmd = f"cd {chisel_dir}; sbt run"
        proc = sp.Popen(['/usr/bin/env','bash','-c',cmd],stdin=sp.DEVNULL,stdout=sp.PIPE,
                stderr=sp.STDOUT,preexec_fn=preexec_fn)

        while proc.poll() == None:
            pass

        # sp.run(["sbt", "run"], cwd=chisel_dir)
        
        # copy the generated btor2 file(self.chisel_dir + self.instance + _ + btor + _ + gen + self.instance + .btor2) to the current directory
        shutil.copy(f"{chisel_dir}/{instance}_btor_gen/{instance}.btor2", out_btor)
        # remove src/main/scala/Btor2Generator.scala and src/main/scala/<chisel_file>
        os.remove(chisel_dir + "/src/main/scala/Btor2Generator.scala")
        os.remove(chisel_dir + "/src/main/scala/" + chisel_file.split("/")[-1])
        shutil.rmtree(f"{chisel_dir}/{instance}_btor_gen", ignore_errors=True)
        
        return 

    def make_btor(self):
        with open(f"{self.designdir}/{self.filename}_btor.ys",'w') as f:
            print(f"read -formal {self.srcfile}",file=f,flush=True)
            print(f"prep -top {self.top}",file=f,flush=True)
            print("hierarchy -check",file=f,flush=True)
            print("chformal -assume -early",file=f,flush=True)
            print("memory -nomap",file=f,flush=True)
            print("flatten",file=f,flush=True)
            print("setundef -undriven -expose",file=f,flush=True)
            print(f"write_btor {self.designdir}/{self.filename}.btor",file=f,flush=True)
        def preexec_fn():
            # self.task.log(f'IN PREEXEC_FN,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.setpgrp()
        cmd = f"{self.exe_path['yosys']} {self.designdir}/{self.filename}_btor.ys"
        proc = sp.Popen(['/usr/bin/env','bash','-c',cmd],stdin=sp.DEVNULL,stdout=sp.PIPE,
                stderr=sp.STDOUT,preexec_fn=preexec_fn)

        while proc.poll() == None:
            pass
        return
