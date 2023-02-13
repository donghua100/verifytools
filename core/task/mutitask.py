import argparse
import os
import re
import shutil
import subprocess as sp
import sys

root_path = os.path.realpath(os.path.dirname(__file__))
sys.path.append(root_path)

def muti_task(workdir, srcfile, task_types:list):
    n = len(task_types)
    tasks = [str(i) for i in range(n)]
    taskRun = {}
    procIdx = []
    idx = 0
    for i, task in enumerate(tasks):
        task_type =  task_types[i] 
        task_workdir = f"{workdir}/{task}"
        cmd = f"python3 core/task/verify_task.py  -s {srcfile} -t {task} -w {task_workdir} -ty {task_type} -f"
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
                    if os.path.exists(src_trace_inv):
                        shutil.copy(src_trace_inv,dst_trace)
                    for x in taskRun.keys():
                        if x in procIdx:
                            proc = taskRun[x]
                            procIdx.remove(x)
                            proc.kill()
                elif len(re.findall(r'task return status: UNSAFE', fstr))!=0:
                    if os.path.exists(src_trace_wit):
                        shutil.copy(src_trace_wit,dst_trace)
                    if os.path.exists(src_trace_vcd):
                        shutil.copy(src_trace_vcd, dst_vcd)
                    for x in taskRun.keys():
                        if x in procIdx:
                            proc = taskRun[x]
                            procIdx.remove(x)
                            proc.kill()



