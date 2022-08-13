import subprocess as sp
import os
import signal
class Proc():
    def __init__(self,task,cmdline,logfile=None,logstderr=False,slient=False):
        self.task = task
        self.cmdline = cmdline
        self.logfile = logfile
        self.logstderr = logstderr
        self.slient = slient

        self.running = False
        self.exited = False
        self.finished = False
        self.terminated = False

        self.output_callback = None
        self.exit_callback = None
        self.error_callback = None
        self.outs = []

        self.task.update_proc_pending(self)
        self.task.log(f'Proc({os.getpid()}) crate,pgid:{os.getpgid(os.getpid())}, ppid:{os.getppid()}')

    def read_output(self):
        while True:
            line = self.p.stdout.readline().decode('utf-8')
            if not line:
                break
            self.outs.append(line.strip())
        self.handle_output()
    
    def log(self,msg):
        if self.logfile is not None:
            print(msg,file=self.logfile)
        self.task.log(f"log:{msg}")

    def handle_output(self):
        self.task.log(f"handle_output proc terminated:{self.terminated}")
        if self.terminated or len(self.outs) == 0:
            pass
        if self.output_callback is not None:
            self.output_callback(self.outs)
        for line in self.outs:
            self.log(line)

    def terminate(self):
        self.task.log(f"terminate :{self.p.pid}")
        if self.running:
            os.killpg(self.p.pid,signal.SIGTERM)
            # self.task.log(f"terminate subprocess({self.p.pid})")
            # self.p.kill()
            self.task.update_proc_stopped(self)
        elif not self.terminated and not self.finished and not self.exited:
            self.task.update_proc_canceled(self)
        self.terminated = True

    def run(self):
        def preexec_fn():
            # self.task.log(f'IN PREEXEC_FN,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.setpgrp()
            # self.task.log(f'SET pgrp,pid:{os.getpid()},pgid:{os.getpgid(os.getpid())}')
        self.p = sp.Popen(['/usr/bin/env','bash','-c',self.cmdline],stdin=sp.DEVNULL,stdout=sp.PIPE,
                stderr=(sp.STDOUT if self.logstderr else None),preexec_fn=preexec_fn)
        self.task.log(f"Proc({os.getpid()}) crate subprocess({self.p.pid}),subprocess pgid:{os.getpgid(self.p.pid)}")
        self.running = True
        self.task.update_proc_running(self)
        self.read_output()
        if self.p.poll() is not None:
            returncode = self.p.returncode
            self.task.log(f"subprocess({self.p.pid}),returncode:{returncode}")
            if self.exited or self.terminated or self.finished:
                return
            self.task.update_proc_stopped(self)
            self.running = False
            self.exited = True
            if returncode == 0:
                self.finished = True

