import subprocess as sp
import os
import signal
class Proc():
    def __init__(self,task,info,cmdline,logfilename=None):
        self.task = task
        self.cmdline = cmdline
        self.logfilename = logfilename
        if logfilename is not None:
            self.logfile = open(f'{self.task.logdir}/{logfilename}','w')
        else:
            self.logfile = None
        self.info = info

        self.ran = False
        self.returncode = None

        self.output_callback = None
        self.exit_callback = None
        self.error_callback = None
        self.outs = []

        self.task.update_proc_pending(self)
        self.p_info = None

    def read_output(self):
        self.task.log(f"read subprocess({self.info}:{self.p.pid}) outputs")
        while True:
            line = self.p.stdout.readline().decode('utf-8')
            if not line:
                break
            self.outs.append(line.strip())
        self.handle_output()
    
    def log(self,msg):
        if self.logfile is not None:
            print(msg,file=self.logfile)
        # self.task.log(f"log:{msg}")

    def handle_output(self):
        self.task.log(f"handle subprocess({self.info}:{self.p.pid}) outputs")
        if len(self.outs) == 0:
            self.task.log(f'subprocess({self.info}:{self.p.pid}) has no output')
            return
        if self.output_callback is not None:
            self.output_callback(self.outs)
        for line in self.outs:
            self.log(line)
        if self.logfile is not None:
            self.task.log(f'subprocess({self.p_info}) outputs has been wrieten in {self.task.logdir}/{self.logfilename}')

    def terminate(self):
        self.task.log(f"terminate :{self.p.pid}")
        if self.ran:
            if self.returncode is None:
                os.killpg(self.p.pid,signal.SIGTERM)
                # self.task.log(f"terminate subprocess({self.p_info})")
                # self.p.kill()
                self.task.update_proc_stopped(self)
        else:
            self.task.update_proc_canceled(self)

    def run(self):
        def preexec_fn():
            # self.task.log(f'IN PREEXEC_FN,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.setpgrp()
            # self.task.log(f'SET pgrp,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
        self.p = sp.Popen(['/usr/bin/env','bash','-c',self.cmdline],stdin=sp.DEVNULL,stdout=sp.PIPE,
                stderr=sp.STDOUT,preexec_fn=preexec_fn)
        self.p_info = f"{self.info}:{self.p.pid}"
        self.task.log(f"Proc({os.getpid()}) crate subprocess({self.p_info}),subprocess pgid:{os.getpgid(self.p.pid)}")
        self.task.log(f"run command:{self.cmdline}")
        self.ran = True
        self.task.update_proc_running(self)
        self.read_output()
        # after reed outputs subprocess is not exited,wait a moment
        while self.p.poll() is None:
            pass
        self.returncode = self.p.returncode
        self.task.log(f"subprocess({self.p_info}),returncode:{self.returncode}")
        if self.returncode!=0:
            if self.exit_callback is not None:
                self.task.status = 'ERROR'
                self.task.log(f"subprocess({self.p_info}) exited abnormaly")
                self.exit_callback(self.returncode)
            return
        self.task.update_proc_stopped(self)

