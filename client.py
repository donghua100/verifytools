import os
import copy
import argparse
import sys
import shutil
import time
from tomlkit import parse,dumps
import socket
from msg import sendmsg, recvmsg
import logging
from multiprocessing import Process
descr = 'run verify tools on a server'

def parser_cmd():
    # python3 client.py bmc 
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('config', help='config file')
    parser.add_argument('-o', '--output', help='output dir',type=str,default=None)
    parser.add_argument('-f', '--force', help='overwrite work dir',action='store_true')
    args = parser.parse_args()
    workdir = args.output
    if workdir is None:
        workdir = 'demo'
    if not os.path.exists(workdir):
        os.mkdir(workdir)
    else:
        if args.force:
            shutil.rmtree(workdir,ignore_errors=True)
            os.mkdir(workdir)
        else:
            print(f"workdir {workdir} have exist, use force to remove")
            sys.exit(-1)
    return args.config, workdir

def client(ip, port, cfg,taskname, srcfile, outs_dir):
    print(f"pid : {os.getpid()}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))

    log = logging.getLogger(taskname)
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info('upload config file')
    sendmsg(dumps(cfg), s)


    src = open(srcfile).read()
    log.info('upload src verify file {}'.format(srcfile))
    sendmsg(src, s)

    log.info('task run: {}'.format(taskname))
    sendmsg(taskname, s)
    # print("aaaaa")
    res_data = recvmsg(s)
    # print("bbbbb")
    if not os.path.exists(outs_dir):
        os.mkdir(outs_dir)
    result = open(f'{outs_dir}/results.txt','w')
    result.write(res_data)
    result.close()
    log.warning(res_data)

    trace_data = recvmsg(s)
    if trace_data != 'NO TRACE':
        # print(trace_data)
        trace = open(f'{outs_dir}/trace.txt', 'w')
        trace.write(trace_data)

    vcd_data = recvmsg(s)
    if vcd_data != 'NO VCD':
        vcd = open(f'{outs_dir}/dump.vcd', 'w')
        vcd.write(vcd_data)
    s.close()

def muticlient():
    cfg_path,outs_dir    = parser_cmd()
    cfg         = parse(open(cfg_path).read())
    tasks       = cfg['tasks']
    procs = []
    for task in tasks:
        ip      = cfg[task]['ip']
        port    = int(cfg[task]['port'])
        srcfile = cfg['file']['name']
        srcname = os.path.basename(srcfile)
        srcname = os.path.splitext(srcname)[0]
        task_out_dir = f"{outs_dir}/{task}"
        new_cfg = copy.deepcopy(cfg)
        new_cfg['file']['name'] = srcname
        p = Process(target=client, args=(ip,port,new_cfg,task,srcfile,task_out_dir,))
        procs.append(p)
        p.start()
    for p in procs:
        p.join()
        # client(ip, port, new_cfg, task, srcfile, task_out_dir)
        

if __name__ == '__main__':
    muticlient()
    #parser_cmd()

