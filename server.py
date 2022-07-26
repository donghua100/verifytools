import socket
import subprocess as sp
import os
import uuid

from msg import sendmsg,recvmsg
from setting import HOST,PORT,MSG_SEND_OK,MSG_RECV_OK,BMC,BMC_DONE
from setting import VCD_SEND


def server():
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    
    s.bind((HOST,PORT))
    
    s.listen()
    while True:
        conn,addr = s.accept()
        if  not os.path.exists('btor'):
            os.mkdir('btor')
        if not os.path.exists('vcd'):
            os.mkdir('vcd')
        fname = 'btor/' + uuid.uuid4().hex
        f = open(fname,'w',encoding='utf-8')
        
        data = recvmsg(conn)
        f.write(data)
        f.close()
        sendmsg(MSG_SEND_OK,conn)
        
        
        cmd = recvmsg(conn)
        
        sendmsg(MSG_SEND_OK,conn)
        vcdpath = 'vcd/' + uuid.uuid4().hex
        cmd = BMC + ' ' + fname +  ' ' + cmd + ' ' + '-vcdpath ' + vcdpath
        print(cmd)
        lcmd = cmd.split()
        proc = sp.Popen(lcmd,stdout=sp.PIPE,stderr=sp.PIPE,encoding='utf-8')
        flag = False
        try:
            outs,errs = proc.communicate(timeout=3600)
        except sp.TimeoutExpired:
            outs,errs = proc.communicate()
            flag = True
            proc.kill()
        if not outs: outs = 'no stdout'
        sendmsg(outs,conn)
        if not errs: errs = 'no stderr'
        sendmsg(errs,conn)
        if '-vcd' in lcmd and os.path.exists(vcdpath):
            f = open(vcdpath,'r',encoding='utf-8')
            sendmsg(VCD_SEND,conn)
            sendmsg(f.read(),conn)
        else:
            sendmsg('no vcd',conn)
        conn.close()

if __name__ == '__main__':
    server()

