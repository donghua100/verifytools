import os
import socket
import argparse
from tomlkit import dumps, parse
from msg import sendmsg,recvmsg
import logging as log

descr = 'run verify tolls on a server'

def parser_cmd():
    # python3 client.py bmc 
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('config', help='config file')
    parser.add_argument('-o', '--output', help='output dir',type=str,default=None)
    args = parser.parse_args()
    return args.config,args.output


def client():
    cfg_path,outs_dir    = parser_cmd()
    cfg         = parse(open(cfg_path).read())
    ip          = cfg['server']['ip']
    port        = int(cfg['server']['port'])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    srcfile = cfg['file']['name']
    srcname = os.path.basename(srcfile)
    srcname = os.path.splitext(srcname)[0]
    cfg['file']['name'] = srcname

    log.info('upload config file')
    sendmsg(dumps(cfg), s)

    src = open(srcfile).read()

    log.info('upload src verify file')
    sendmsg(src, s)

    res_data = recvmsg(s)
    if outs_dir is None:
        outs_dir = f'{srcname}'
    if not os.path.exists(outs_dir):
        os.mkdir(outs_dir)
    result = open(f'{outs_dir}/results.txt','w')
    result.write(res_data)
    result.close()
    log.info(res_data)

    trace_data = recvmsg(s)
    if trace_data != 'NO TRACE':
        log.info(trace_data)
        trace = open(f'{outs_dir}/trace.txt', 'w')
        trace.write(trace_data)
    s.close()


if __name__ == '__main__':
    client()
    #parser_cmd()

