import re
import shutil
import socket
import subprocess as sp
import os
import argparse
import tomlkit
from multiprocessing import Pool
from msg import sendmsg, recvmsg

def task(conn, tmp_dir, outs_dir, conn_cnt):
    config_data = recvmsg(conn)
    verify_data = recvmsg(conn)

    cfg = tomlkit.parse(config_data)
    srcname = cfg['file']['name']
    tmp_conn_dir = f'{tmp_dir}/{conn_cnt}'
    if not os.path.exists(tmp_conn_dir):
        os.mkdir(tmp_conn_dir)
    config_name = f'{tmp_conn_dir}/{srcname}.yaml'
    with open(config_name, 'w') as config_file:
        config_file.write(config_data)
    verify_name = f'{tmp_conn_dir}/{srcname}'
    with open(verify_name, 'w') as verify_file:
        verify_file.write(verify_data)
    work_dir = f'{outs_dir}/conn{conn_cnt}'
    cmd = f"python3 core/mutitask.py {config_name} -s {verify_name} -w {work_dir} -f"
    proc = sp.Popen(['sh', '-c', cmd])
    while proc.poll() is None:
        pass
    res_data = open(f'{work_dir}/results.txt').read()
    sendmsg(res_data, conn)
    if len(re.findall(r'task return status: SAFE',res_data))!=0:
        inv_data = open(f'{work_dir}/trace.txt').read()
        sendmsg(inv_data,conn)
    elif len(re.findall(r'task return status: UNSAFE',res_data))!=0:
        witness_data = open(f'{work_dir}/trace.txt').read()
        sendmsg(witness_data,conn)
    else:
        sendmsg('NO TRACE',conn)
    conn.close()
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
        p.apply_async(task,args=(conn,tmp_dir,outs_dir,conn_cnt,))
        conn_cnt += 1


if __name__ == '__main__':
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
    server(ip,port)

