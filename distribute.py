import socket
from tomlkit import dumps
import os
import logging
from msg import sendmsg, recvmsg
import argparse


def client(ip, port, cfg,taskname, srcfile, outs_dir):
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

    res_data = recvmsg(s)
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

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-ip',required=True)
    p.add_argument('-port',required=True)

