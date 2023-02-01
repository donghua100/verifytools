import re
import sys
import shutil
import socket
import subprocess as sp
import os
import argparse
import tomlkit
from multiprocessing import Pool
from msg import CMD_CLIENT,CONFIG_CLIENT, DIR_CLIENT, recvmsg_byte,sendmsg, recvmsg
import logging
from core.task import verify_task
from core.task import AIG_BMC_TASK, AIG_PROVE_TASK, BTOR_BMC_TASK,BTOR_PROVE_TASK
from core.mutitask import muti_task

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
    # print("send trace")
    log.info("send trace")
    # print(res_data)
    if len(re.findall(r'task return status: SAFE', res_data))!=0:
        if not os.path.exists(src_trace_inv):
            sendmsg(conn, 'NO TRACE')
        else:
            trace_inv_data = open(src_trace_inv).read()
            sendmsg(conn, trace_inv_data)
    elif len(re.findall(r'task return status: UNSAFE', res_data))!=0:
        if not os.path.exists(src_trace_wit):
            sendmsg(conn, 'NO TRACE')
        else:
            trace_wit_data = open(src_trace_wit).read()
            sendmsg(conn, trace_wit_data)
    else:
        sendmsg(conn, 'NO TRACE')
    print("send vcd")
    if os.path.exists(src_trace_vcd):
        vcd_data = open(src_trace_vcd).read()
        sendmsg(conn, vcd_data)
    else:
        sendmsg(conn, 'NO VCD')
    conn.close()
    shutil.rmtree(tmp_conn_dir,ignore_errors=True)
    shutil.rmtree(work_dir,ignore_errors=True)


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

    workdir = ''
    if cmd == 'bit,bmc':
        workdir = f"{outs_dir}/bitbmc"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        verify_task(file_name, workdir, 'bitbmc',AIG_BMC_TASK)
    elif cmd == 'bit,prove':
        workdir = f"{outs_dir}/bitprove"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        verify_task(file_name, workdir, 'bitprove',AIG_PROVE_TASK)

    elif cmd == 'word,bmc':
        workdir = f"{outs_dir}/wordbmc"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        verify_task(file_name, workdir, 'wordbmc',BTOR_BMC_TASK)

    elif cmd == 'word,prove':
        workdir = f"{outs_dir}/wordprove"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        verify_task(file_name, workdir, 'wordprove',BTOR_PROVE_TASK)
    else:
        assert 0
    res = open(f"{workdir}/results.txt").read()
    sendmsg(conn, res)
    shutil.rmtree(tmp_conn_dir,ignore_errors=True)
    shutil.rmtree(workdir, ignore_errors=True)
        





def dir_task(conn, tmp_dir, outs_dir, conn_cnt):
    files_num,_,_ = recvmsg(conn)
    files_num = int(files_num)
    tmp_conn_dir = f'{tmp_dir}/{conn_cnt}'
    if not os.path.exists(tmp_conn_dir):
        os.mkdir(tmp_conn_dir)
    # file_name = f"{tmp_conn_dir}/{filename}"
    file_vec = []
    for i in range(files_num):
        filename,_,_ = recvmsg(conn)
        file_name = f"{tmp_conn_dir}/{filename}"
        file_vec.append((filename,file_name))
        file_context,_,_ = recvmsg_byte(conn)
        f = open(file_name,'wb')
        f.write(file_context)
        f.close()

    for name, path in file_vec:
        prefix_name, file_type = os.path.splitext(name)
        file_type = file_type[1:]
        workdir = f"{outs_dir}/{prefix_name}"
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        else:
            shutil.rmtree(workdir, ignore_errors=True)
            os.mkdir(workdir)
        file_name = path
        taskname = ''
        if os.cpu_count():
            p = Pool(os.cpu_count())
        else:
            p = Pool(1)
        workdir_bmc = f'{workdir}/bmc'
        workdir_prove = f'{workdir}/prove'
        if not os.path.exists(workdir_bmc):
            os.mkdir(workdir_bmc)

        if not os.path.exists(workdir_prove):
            os.mkdir(workdir_prove)

        # if file_type == 'aig':
        #     taskname = f'{prefix_name}_bmc'
        #     p.apply_async(verify_task, args=(file_name, workdir_bmc, taskname, AIG_BMC_TASK, ))
        #     taskname = f'{prefix_name}_prove'
        #     p.apply_async(verify_task, args=(file_name, workdir_prove, taskname, AIG_PROVE_TASK, ))
        # elif file_type == 'btor' or file_type == 'btor2':
        #     taskname = f'{prefix_name}_bmc'
        #     p.apply_async(verify_task, args=(file_name, workdir_bmc, taskname, BTOR_BMC_TASK, ))
        #     # verify_task(file_name, workdir, taskname, BTOR_BMC_TASK)
        #     taskname = f'{prefix_name}_prove'
        #     p.apply_async(verify_task, args=(file_name, workdir_prove, taskname, BTOR_PROVE_TASK, ))
        # else:
        #     assert 0

        if file_type == 'aig':
            muti_task(workdir, file_name, [AIG_BMC_TASK, AIG_PROVE_TASK])
        elif file_type == 'btor' or file_type == 'btor2':
            muti_task(workdir, file_name, [BTOR_BMC_TASK, BTOR_PROVE_TASK])

    for name, file_path in file_vec:
        prefix_name = os.path.splitext(name)[0]
        workdir = f"{outs_dir}/{prefix_name}"
        dst_res = f"{workdir}/results.txt"
        dst_vcd = f"{workdir}/dump.vcd"
        dst_trace = f"{workdir}/trace.txt"

        sendmsg(conn, f"{prefix_name}.txt")
        res_msg = open(dst_res, 'r').read()
        sendmsg(conn, res_msg)






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
        elif client_type == DIR_CLIENT:
            dir_task(conn,tmp_dir,outs_dir,conn_cnt)
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

