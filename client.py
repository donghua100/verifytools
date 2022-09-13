import os
import socket
import argparse
from msg import sendmsg,recvmsg
from setting import HOST,PORT
import logging as log

descr = 'run bmc on a server'

def parser_cmd():
    # python3 client.py bmc 
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('-c', '--config', dest='c', required=True, help='config file')
    parser.add_argument('-s', '--src', dest='s', required=True, help='src verify file')
    parser.add_argument('-t', '--top', dest='t', default=None, help='top module for system verilog')
    args = parser.parse_args()
    return args.c, args.s, args.t


def client():
    cfg_path, src_path, top = parser_cmd()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.connect((HOST, PORT))

    cfg = open(cfg_path).read()
    log.info('upload config file')
    sendmsg(cfg, s)

    src = open(src_path).read()
    log.info('upload src verify file')
    sendmsg(src, s)

    srcname = os.path.basename(src_path)
    srcname = os.path.splitext(srcname)[0]
    sendmsg(srcname, s)

    if top is not None:
        sendmsg(top, s)
    else:
        sendmsg('NO TOP',s)

    res_data = recvmsg(s)
    outs_dir = 'tasks'
    if not os.path.exists(outs_dir):
        os.mkdir(outs_dir)
    res_dir = f'{outs_dir}/{srcname}'
    if not os.path.exists(res_dir):
        os.mkdir(res_dir)
    result = open(f'{res_dir}/result.txt','w')
    result.write(res_data)
    result.close()
    log.info(res_data)

    trace_data = recvmsg(s)
    if trace_data != 'NO TRACE':
        log.info(trace_data)
        trace = open(f'{res_dir}/trace.txt', 'w')
        trace.write(trace_data)
    s.close()


if __name__ == '__main__':
    client()
    #parser_cmd()

