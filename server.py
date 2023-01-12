import re
import sys
import shutil
import socket
import subprocess as sp
import os
import argparse
import tomlkit
from multiprocessing import Pool
from msg import CMD_CLIENT,CONFIG_CLIENT, recvmsg_byte,sendmsg, recvmsg
import logging
from core.task import VerifTask

def task(conn, tmp_dir, outs_dir, conn_cnt):
    config_data,_,_ = recvmsg(conn)
    verify_data,_,_ = recvmsg(conn)
    taskname,_,_    = recvmsg(conn)

    cfg = tomlkit.parse(config_data)
    srcname = cfg['file']['name']
    tmp_conn_dir = f'{tmp_dir}/{conn_cnt}'
    if not os.path.exists(tmp_conn_dir):
        os.mkdir(tmp_conn_dir)
    config_name = f'{tmp_conn_dir}/{srcname}.toml'
    with open(config_name, 'w') as config_file:
        config_file.write(config_data)
    verify_name = f'{tmp_conn_dir}/{srcname}'
    with open(verify_name, 'w') as verify_file:
        verify_file.write(verify_data)
    work_dir = f'{outs_dir}/conn{conn_cnt}'
    if not os.path.exists(work_dir):
        os.mkdir(work_dir)
    work_dir = f'{work_dir}/{taskname}'
    cmd = f"python3 core/task.py {config_name} -s {verify_name} -t {taskname} -d {work_dir} -f"
    proc = sp.Popen(['sh', '-c', cmd])
    while proc.poll() is None:
        pass
    src_res = f"{work_dir}/results.txt"
    src_trace_inv = f"{work_dir}/trace/inv.txt"
    src_trace_wit = f"{work_dir}/trace/witness.txt"
    src_trace_vcd = f"{work_dir}/trace/dump.vcd"

    res_data = open(src_res).read() 
    log = logging.getLogger(str(conn_cnt))
    log.setLevel(logging.INFO)
    log.info("send results")
    # print("aaaaaaaaaaaaaaaa")
    sendmsg(conn, res_data)
    # print("bbbbbbbbbbbbbbb")
    log.info("send trace")
    if len(re.findall(r'task return status: SAFE', res_data))!=0:
        if not os.path.exists(src_trace_inv):
            sendmsg(conn, 'NO TRACE')
        else:
            trace_inv_data = open(src_trace_inv).read()
            sendmsg(conn, trace_inv_data)
    elif len(re.findall(r'task return status: UNSAFE', res_data))!=0:
        if not os.path.exists(src_trace_wit):
            trace_wit_data = open(src_trace_wit).read()
            sendmsg(conn, trace_wit_data)
        else:
            sendmsg(conn, 'NO TRACE')
    else:
        sendmsg(conn, 'NO TRACE')
    if os.path.exists(src_trace_vcd):
        vcd_data = open(src_trace_vcd).read()
        sendmsg(conn, vcd_data)
    else:
        sendmsg(conn, 'NO VCD')
    conn.close()
    shutil.rmtree(tmp_conn_dir,ignore_errors=True)


def cmd_task(conn,tmp_dir,outs_dir,conn_cnt):

    src,kind,cmd = recvmsg_byte(conn)
    filename,_,_ = recvmsg(conn)
    tmp_conn_dir = f'{tmp_dir}/{conn_cnt}'
    if not os.path.exists(tmp_conn_dir):
        os.mkdir(tmp_conn_dir)
    file_name = f"{tmp_conn_dir}/{filename}"
    print(src)
    print(file_name)
    with open(file_name, 'wb') as file:
        file.write(src)
    print(src)
    print(file_name)
    modes = ['bmc', 'prove']
    depths = ['100','1000','100000']
    bit_engines = ['abc']
    word_engines = ['avr', 'pono']
    solvers = ['btor', 'msat', 'yices', 'z3']
    engine_opts = ['']
    timeout_default = None
    top = None
    args = ''
    file_type = ''

    if cmd == 'bit,bmc' or cmd == 'bit,prove':
        file_type = 'aig'
    elif cmd =='word,bmc' or cmd == 'word,prove':
        file_type = 'btor'
    tasks = []
    config_file = ''
    workdir = ''
    taskname = ''
    earlylogs = []
    logfile = None
    useconfig = False
    if cmd == 'bit,bmc':
        workdir = f"{tmp_conn_dir}/bitbmc"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        task = VerifTask(config_file,workdir,'bit bmc',[],logfile,useconfig)
        task.mode = 'bmc'
        task.depth = '10000'
        task.engine = 'abc'
        task.solver = 'btor'
        task.engine_opt = ''
        task.task_timeout = None
        task.top = None
        task.file_type = 'aig'
        task.args = ''
        
        srcfile = open(file_name,'rb')
        srcname = os.path.basename(file_name)
        task.filename = os.path.splitext(srcname)[0]
        destfile = open(f"{task.srcdir}/{task.filename}.{task.file_type}","wb")
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
    elif cmd == 'bit,prove':
        workdir = f"{tmp_conn_dir}/bitprove"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        task = VerifTask(config_file,workdir,'bit prove',[],logfile,useconfig)
        task.mode = 'prove'
        task.depth = '10000'
        task.engine = 'abc'
        task.solver = 'btor'
        task.engine_opt = ''
        task.task_timeout = None
        task.top = None
        task.file_type = 'aig'
        task.args = ''
        
        srcfile = open(file_name,'rb')
        srcname = os.path.basename(file_name)
        task.filename = os.path.splitext(srcname)[0]
        destfile = open(f"{task.srcdir}/{task.filename}.{task.file_type}","wb")
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

    elif cmd == 'word,bmc':
        workdir = f"{tmp_conn_dir}/wordbmc"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        task = VerifTask(config_file,workdir,'word bmc',[],logfile,useconfig)
        task.mode = 'bmc'
        task.depth = '10000'
        task.engine = 'pono'
        task.solver = 'btor'
        task.engine_opt = ''
        task.task_timeout = None
        task.top = None
        task.file_type = 'btor'
        task.args = ''
        
        srcfile = open(file_name,'r')
        srcname = os.path.basename(file_name)
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

    elif cmd == 'word,prove':
        workdir = f"{tmp_conn_dir}/wordprove"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        task = VerifTask(config_file,workdir,'word prove',[],logfile,useconfig)
        task.mode = 'prove'
        task.depth = '10000'
        task.engine = 'avr'
        task.solver = 'msat'
        task.engine_opt = ''
        task.task_timeout = None
        task.top = None
        task.file_type = 'btor'
        task.args = ''
        
        srcfile = open(file_name,'r')
        srcname = os.path.basename(file_name)
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
    else:
        assert 0
    res = open(f"{workdir}/results.txt").read()
    sendmsg(conn, res)
    shutil.rmtree(tmp_conn_dir,ignore_errors=True)
        
def server(ip, port):
    global outs_dir
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((ip, port))
    s.listen()
    p = Pool(os.cpu_count())
    conn_cnt = 0
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    if not os.path.exists(outs_dir):
        os.mkdir(outs_dir)
    while True:
        conn,addr = s.accept()
        client_type,_,_ = recvmsg(conn)
        print(client_type)
        if client_type == CONFIG_CLIENT:
            p.apply_async(task,args=(conn,tmp_dir,outs_dir,conn_cnt,))
        elif client_type == CMD_CLIENT:
            cmd_task(conn,tmp_dir,outs_dir,conn_cnt)
            # p.apply_async(cmd_task,args=(conn,tmp_dir,outs_dir,conn_cnt,))

        conn_cnt += 1


if __name__ == '__main__':
    sys.path.append('core')
    cur_dir = os.path.abspath(os.curdir)
    outs_dir = f"{cur_dir}/tasks"
    tmp_dir = f'{cur_dir}/tmp'
    p = argparse.ArgumentParser()
    p.add_argument('-ip', type=str, required=True)
    p.add_argument('-p', '--port', type=int, required=True)
    p.add_argument('-o', '--output', type=str, help='output dir', default=outs_dir)
    args = p.parse_args()
    ip = args.ip
    port = args.port
    outs_dir = args.output
    server(ip,port)

