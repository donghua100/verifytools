import os
import Proc
import shutil


def run(task):
    logfilename = 'engine_avrpr.txt'
    avrpath = task.avr_path
    # avrbin = f'{avrpath}/build/bin_{task.solver}'
    curdir = os.path.abspath(os.curdir)
    avrout = f'{curdir}/{task.workdir}/avr'
    name = 'foo'
    file = f'{curdir}/{task.designdir}/{task.filename}.btor'
    workers = f'{curdir}/{task.workdir}/workers.txt'
    opts = task.engine_opt
    timeout = 0
    if task.task_timeout is None:
        timeout = 3600*24
    else:
        timeout = task.task_timeout + 5*60
    cmdline = f'cd {avrpath};python3 avr_pr.py -o {avrout} -n {name} {opts} -w {workers} --timeout {timeout} {file}'
    proc = Proc.Proc(task, 'run avrpr', cmdline, logfilename)
    def output_callback(outs=None):
        status = 'UNKNOWN'
        avr_workdir = f'{avrout}/pr_{name}'
        srccex = f'{avr_workdir}/cex.witness'
        dstcex = f'{task.tracedir}/witness.txt'
        srcsmt = f'{avr_workdir}/inv.smt2'
        srcinv = f'{avr_workdir}/inv.txt'
        dstinv = f'{task.tracedir}/invar.txt'
        if os.path.isfile(srccex):
            status = 'UNSAFE'
            shutil.copy(srccex, dstcex)
        if os.path.isfile(srcsmt):
            status = 'SAFE'
            with open(dstinv,'w') as f:
                inv_txt = open(srcinv,'r')
                f.write(inv_txt.read())
                inv_txt.close()
                f.write('\n\n\n')
                f.write('-'*50)
                f.write('\n')
                f.write(';smt2 format invar\n')
                inv_smt = open(srcsmt,'r')
                f.write(inv_smt.read())
                inv_smt.close()
        task.status = status
    proc.output_callback = output_callback
        



