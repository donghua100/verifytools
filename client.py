import socket
import argparse
from msg import sendmsg,recvmsg
from setting import BMC_DONE, HOST,PORT,MSG_SEND_OK,MSG_RECV_OK,BMC_DONE, VCD_SEND

descr = 'run bmc on a server'

def parser_cmd():
    # python3 client.py bmc 
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument('-k','--ksteps',dest='k',metavar='N',type=int,default=10,help='run bmc N steps')
    parser.add_argument('--inv',action='store_true',default=False,help='use inverse bmc')
    parser.add_argument('--vcd',action='store_true',default=False,help='print vcd file if find counterexample')
    parser.add_argument('--smt-slover',dest='solver',metavar='solver' ,type=str,default='btor',help='available solver: btor cvc5 z3')
    parser.add_argument('file',metavar='file',type=str,help='btor files')
    args = parser.parse_args()
    solvers = {'btor':0,'cvc5':1,'z3':2}
    if args.solver not in solvers:
        print('not availbale,see help')
        exit(-1)
    cmd = '-k {} -s {}'.format(args.k,solvers[args.solver])
    if args.inv:cmd += ' -inv'
    if args.vcd: cmd += ' -vcd'

    print(cmd)
    return args.file,cmd


def client():
    file,cmd = parser_cmd()
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    s.connect((HOST,PORT))
    f = open(file,'r',encoding='utf-8')
    print('upload the btor file...')
    sendmsg(f.read(),s)
    
    sucess = recvmsg(s)
    if sucess == MSG_SEND_OK:
        print('upload sucess.')
    else:
        exit(-1)
    print('send cmd to server...')
    sendmsg(cmd,s)
    sucess = recvmsg(s)
    if sucess == MSG_SEND_OK:
        print('send cmd to server sucess.')
    else:
        exit(-1)
    outs = recvmsg(s)
    print(outs)
    errs = recvmsg(s)
    if errs != 'no stderr':
        print(errs)
    sucess = recvmsg(s)
    if sucess == VCD_SEND:
        vcd = recvmsg(s)
        f = open('dump.vcd','w',encoding='utf-8')
        f.write(vcd)
    s.close()


if __name__ == '__main__':
    client()

