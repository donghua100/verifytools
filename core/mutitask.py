import argparse
import os
import re
import shutil
import subprocess as sp
import sys
import time
import tomlkit

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('configfile', help='config file', type=str)
    p.add_argument('-s', '--srcfile', help='the file to verify', type=str, required=True)
    p.add_argument('-w','--workdir', help='muti task work dir', type=str, required=True)
    p.add_argument('-f', '--force', help='overwrite work dir',action='store_true')

    arg             = p.parse_args()
    workdir         = arg.workdir
    configfile      = arg.configfile
    srcfile         = arg.srcfile
    workdir = os.path.abspath(workdir)
    if not os.path.exists(workdir):
        os.mkdir(workdir)
    else:
        if arg.force:
            shutil.rmtree(workdir,ignore_errors=True)
            os.mkdir(workdir)
        else:
            sys.exit(-1)
    cfg         = tomlkit.parse(open(configfile).read())
    srcname     = cfg['file']['name']
    dst_cfg     = f"{workdir}/config.toml"
    dst_file    = f"{workdir}/{srcname}"
    shutil.copy(configfile, dst_cfg)
    shutil.copy(srcfile,dst_file)

    tasks = cfg['tasks']
    taskRun = {}
    procIdx = []
    idx = 0
    for task in tasks:
        task_workdir = f"{workdir}/{task}"
        cmd = f"python3 core/task.py {configfile} -s {dst_file} -t {task} -d {task_workdir} -f"
        print(cmd)
        proc = sp.Popen(['sh', '-c', cmd])
        taskRun[idx] = proc
        procIdx.append(idx)
        idx += 1
    while True:
        if len(procIdx) == 0:
            break
        for k in procIdx:
            proc = taskRun[k]
            if proc.poll() is not None:
                procIdx.remove(k)
                resfile = f"{workdir}/{tasks[k]}/results.txt"
                fstr = open(resfile).read()
                dst_res = f"{workdir}/results.txt"
                dst_vcd = f"{workdir}/dump.vcd"
                shutil.copy(resfile,dst_res)
                src_trace_inv = f"{workdir}/{tasks[k]}/trace/inv.txt"
                src_trace_wit = f"{workdir}/{tasks[k]}/trace/witness.txt"
                src_trace_vcd = f"{workdir}/{tasks[k]}/trace/dump.vcd"
                dst_trace = f"{workdir}/trace.txt"
                if len(re.findall(r'task return status: SAFE', fstr))!=0:
                    shutil.copy(src_trace_inv,dst_trace)
                    for x in taskRun.keys():
                        if x in procIdx:
                            proc = taskRun[x]
                            procIdx.remove(x)
                            proc.kill()
                elif len(re.findall(r'task return status: UNSAFE', fstr))!=0:
                    shutil.copy(src_trace_wit,dst_trace)
                    if os.path.exists(src_trace_vcd):
                        shutil.copy(src_trace_vcd, dst_vcd)
                    for x in taskRun.keys():
                        if x in procIdx:
                            proc = taskRun[x]
                            procIdx.remove(x)
                            proc.kill()



