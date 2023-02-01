import os
import copy
import argparse
import sys
import shutil
import time
from tomlkit import parse,dumps,table
import socket
from convert import Convert
from msg import CMD_CLIENT, COMMAND, CONFIG, CONFIG_CLIENT, DIR_CLIENT, FILE, sendmsg, recvmsg, sendmsg_byte
import logging
from multiprocessing import Process
descr = 'run verify tools on a server'

def parser_cmd():
    # python3 client.py bmc 
    parser = argparse.ArgumentParser(description=descr)
    # parser.add_argument('-c', '--config', help='config file',type=str,default=None)
    parser.add_argument('-c', '--config', help='config file',type=str,default=None)
    parser.add_argument('-o', '--output', help='output dir',type=str,default=None)
    parser.add_argument('-d', '--dir', help='verify dir',type=str,default=None)
    parser.add_argument('-f', '--force', help='overwrite work dir',action='store_true')
    parser.add_argument('--bit', help='do bit level mc',action='store_true')
    parser.add_argument('--prove', help='do prove', action='store_true')
    parser.add_argument('-s','--source', help='source file',type=str,default=None)
    parser.add_argument('-t', '--top',help = 'top moudle',type=str,default=None)
    parser.add_argument('-a','--args', help='args for chisel3',type=str,default=None)
    parser.add_argument('--ip',help='server ip',type=str,default=None)
    parser.add_argument('--port', help='server port',type=int,default=None)
    args = parser.parse_args()
    workdir = args.output
    config = args.config
    # ip = args.ip
    # port = args.port
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
    # if config == None:
    #     if ip == None and port == None:
    #         print('config file or ip and port must be specify')
    return args.dir, config, workdir,args.bit, args.prove,args.source,args.top,args.args,args.ip,args.port

def client(ip, port, cfg,taskname, srcfile, outs_dir):
    print(f"pid : {os.getpid()}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))

    log = logging.getLogger(taskname)
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)
    log.info('upload config file')

    sendmsg(s, CONFIG_CLIENT)

    sendmsg(s, dumps(cfg),CONFIG)


    src = open(srcfile).read()
    log.info('upload src verify file {}'.format(srcfile))
    sendmsg(s,src,FILE)

    log.info('task run: {}'.format(taskname))
    sendmsg(s,taskname)
    # print("aaaaa")
    res_data,_,_ = recvmsg(s)
    # print("bbbbb")
    if not os.path.exists(outs_dir):
        os.mkdir(outs_dir)
    result = open(f'{outs_dir}/results.txt','w')
    result.write(res_data)
    result.close()
    log.warning(res_data)

    trace_data,_,_ = recvmsg(s)
    if trace_data != 'NO TRACE':
        # print(trace_data)
        trace = open(f'{outs_dir}/trace.txt', 'w')
        trace.write(trace_data)

    vcd_data,_,_ = recvmsg(s)
    if vcd_data != 'NO VCD':
        vcd = open(f'{outs_dir}/dump.vcd', 'w')
        vcd.write(vcd_data)
    s.close()

default_config = '''tasks = ["foo","bar"]
timeout = 3600
[foo]
engine = "pono"
mode = "bmc"
depth = 100
solver = "btor"
[bar]
engine = "avr"
mode = "prove"
solver = "msat"
'''

def comand_client(outs_dir,bit,prove,src,top,args,ip,port):
    # cfg_path,outs_dir,bit,prove,src,top,args,ip,port    = parser_cmd()
    print(outs_dir)
    workdir = outs_dir
    convert = Convert(outs_dir,src,top,args)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    sendmsg(s,CMD_CLIENT)
    
    srcfile = convert.outaig
    cmd = ''
    if bit and prove:
        cmd = 'bit,prove'
    elif bit and not prove:
        cmd = 'bit,bmc'
    elif not bit and prove:
        cmd = 'word,prove'
        srcfile = convert.outbtor
    elif not bit and not prove:
        cmd = 'word,bmc'
        srcfile = convert.outbtor
    src = open(srcfile,'rb').read()
    # print(src)
    print(cmd)
    sendmsg_byte(s,src,COMMAND,cmd)
    # print(convert.filename,convert.type)
    sendmsg(s,f"{os.path.basename(srcfile)}");
    res,_,_ = recvmsg(s)
    print(res)
    with open(f"{workdir}/results.txt",'w') as f:
        f.write(res)
    

def muticlient(cfg_path,outs_dir):
    # cfg_path,outs_dir,bit,prove,src,_,_,_,_    = parser_cmd()
    # if cfg_path == None:
    #     cfg = parse(default_config)
    # else:
    cfg         = parse(open(cfg_path).read())
    default_timeout = '3600'
    default_engine = 'avr'
    default_mode  = 'prove'
    default_solver = 'msat'
    default_depth = '100'
    if 'timeout' not in cfg:
        cfg['timeout'] = default_timeout
    if 'tasks' not in cfg:
        cfg['tasks'] = ['foo', 'bar']
        ip = cfg['file']['ip']
        port = cfg['file']['port']
        tab = table()
        tab.add('engine', 'pono')
        tab.add('mode', 'bmc')
        tab.add('depth', default_depth)
        tab.add('solver', 'btor')
        tab.add('ip', ip)
        tab.add('port', port)
        cfg['foo'] = tab

        tab = table()
        tab.add('engine', default_engine)
        tab.add('mode', default_mode)
        tab.add('depth', default_depth)
        tab.add('solver', default_solver)
        tab.add('ip', ip)
        tab.add('port', port)
        cfg['bar'] = tab
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
        

def dir_client(dir, ip, port, outs_dir):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    sendmsg(s,DIR_CLIENT)
    file_vec = []
    for root,dirs,files in os.walk(dir):
        for file in files:
            if file.endswith('aig') or file.endswith('btor') or file.endswith('btor2'):
                file_vec.append((os.path.join(root,file),file))
    files_num = len(file_vec)
    sendmsg(s,str(files_num))
    for file_path, file_name in file_vec:
        f = open(file_path,'rb').read()
        sendmsg(s, file_name)
        sendmsg_byte(s, f)

    for i in range(files_num):
        filename,_,_ = recvmsg(s)
        res_msg,_,_ = recvmsg(s)
        out_res = f"{outs_dir}/{filename}"
        with open(out_res,'w') as f:
            f.write(res_msg)






if __name__ == '__main__':
    dir,cfg_path,outs_dir,bit,prove,src,top,args,ip,port    = parser_cmd()
    if cfg_path:
        muticlient(cfg_path,outs_dir)
    elif dir:
        dir_client(dir,ip,port,outs_dir)
    else:
        comand_client(outs_dir,bit,prove,src,top,args,ip,port)
    #parser_cmd()

