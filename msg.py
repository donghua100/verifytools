import json
import struct
COMMAND = 'COMMAND'
MESSAGE = 'MESSAGE'
CONFIG = 'CONFIG FILE'
FILE = 'FILE'
CMD_CLIENT = 'COMMAND CLIENT'
CONFIG_CLIENT = 'CONFIG CLIENT'
DIR_CLIENT = 'DIR CLIENT'
###########|------headers-------|data|
# packet: |data len .. head len|data|
##########|----4byte-----------|    |
def sendmsg(conn, msg:str,kind = MESSAGE, cmd = 'word,prove'):
    msgbyte = msg.encode('utf-8')
    headers = {}
    headers['datalen'] = len(msgbyte)
    headers['type'] = kind
    if kind == COMMAND:
        headers[COMMAND] = cmd
    else:
        headers[COMMAND] = 'word,prove'
    hjson = json.dumps(headers)
    hbyte = hjson.encode('utf-8')
    hlen = len(hbyte)
    conn.send(struct.pack('i',hlen))
    conn.send(hbyte)
    conn.send(msgbyte)


def recvmsg(conn):
    def recv():
        hlenb = conn.recv(4)
        hlen = struct.unpack('i',hlenb)[0]
        hbyte = conn.recv(hlen)
        hjson = json.loads(hbyte.decode('utf-8'))
        datalen = hjson['datalen']
        kind = hjson['type']
        cmd = hjson[COMMAND]
        contextb = b''
        clen = 0
        while clen < datalen:
            size = 1024
            if clen + 1024 > datalen:size = datalen - clen 
            tb = conn.recv(size)
            contextb += tb
            clen += len(tb)
        return contextb.decode('utf-8'),kind,cmd
    r,kind,cmd = recv()
    return r,kind,cmd
    

def sendmsg_byte(conn, msg:bytes,kind = MESSAGE, cmd = 'word,prove'):
    msgbyte = msg
    headers = {}
    headers['datalen'] = len(msgbyte)
    headers['type'] = kind
    if kind == COMMAND:
        headers[COMMAND] = cmd
    else:
        headers[COMMAND] = 'word,prove'
    hjson = json.dumps(headers)
    hbyte = hjson.encode('utf-8')
    hlen = len(hbyte)
    conn.send(struct.pack('i',hlen))
    conn.send(hbyte)
    conn.send(msgbyte)




def recvmsg_byte(conn):
    def recv():
        hlenb = conn.recv(4)
        hlen = struct.unpack('i',hlenb)[0]
        hbyte = conn.recv(hlen)
        hjson = json.loads(hbyte.decode('utf-8'))
        datalen = hjson['datalen']
        kind = hjson['type']
        cmd = hjson[COMMAND]
        contextb = b''
        clen = 0
        while clen < datalen:
            size = 1024
            if clen + 1024 > datalen:size = datalen - clen 
            tb = conn.recv(size)
            contextb += tb
            clen += len(tb)
        return contextb,kind,cmd
    r,kind,cmd = recv()
    return r,kind,cmd


