import re
import shutil
import socket
import subprocess as sp
import os
import time

from msg import sendmsg, recvmsg
from setting import HOST, PORT


def server():
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    
    s.bind((HOST,PORT))
    
    s.listen()
    while True:
        conn,addr = s.accept()
        conn_cnt = 0

        # get config file
        # time.sleep(5)
        config_data = recvmsg(conn)
        verify_data = recvmsg(conn)
        srcname = recvmsg(conn)
        top = recvmsg(conn)
        if top == 'NO TOP':
            top = None
        tmp_dir = 'tmp'
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        tmp_conn_dir = f'{tmp_dir}/{conn_cnt}'
        if not os.path.exists(tmp_conn_dir):
            os.mkdir(tmp_conn_dir)
        config_name = f'{tmp_conn_dir}/{srcname}.cfg'
        with open(config_name, 'w') as config_file:
            config_file.write(config_data)
        verify_name = f'{tmp_conn_dir}/{srcname}'
        with open(verify_name, 'w') as verify_file:
            verify_file.write(verify_data)
        outs_dir = 'tasks'
        if not os.path.exists(outs_dir):
            os.mkdir(outs_dir)
        cur_dir = os.path.abspath(os.curdir)
        work_dir = f'{cur_dir}/{outs_dir}/task{conn_cnt}'
        if top == None:
            cmd = f"python3 core/task.py -s {verify_name} -d {work_dir} {config_name} -f"
        else:
            cmd = f"python3 core/task.py -s {verify_name} -t {top} -d {work_dir} {config_name} -f"
        proc = sp.Popen(['sh', '-c', cmd])
        print(cmd)
        while proc.poll() is None:
            pass
        res_data = open(f'{work_dir}/results.txt').read()
        sendmsg(res_data, conn)
        if len(re.findall(r'task return status: SAFE',res_data))!=0:
            inv_data = open(f'{work_dir}/trace/inv.txt').read()
            sendmsg(inv_data,conn)
        elif len(re.findall(r'task return status: UNSAFE',res_data))!=0:
            witness_data = open(f'{work_dir}/trace/witness.txt').read()
            sendmsg(witness_data,conn)
        else:
            sendmsg('NO TRACE',conn)
        conn.close()
        shutil.rmtree(tmp_conn_dir,ignore_errors=True)

if __name__ == '__main__':
    server()

