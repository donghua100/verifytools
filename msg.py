import json
import struct
###########|------headers-------|data|
# packet: |data len .. head len|data|
##########|----4byte-----------|    |
def sendmsg(msg:str,conn):
    msgbyte = msg.encode('utf-8')
    headers = {'datalen':len(msgbyte)}
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
        contextb = b''
        clen = 0
        while clen < datalen:
            size = 1024
            if clen + 1024 > datalen:size = datalen - clen 
            tb = conn.recv(size)
            contextb += tb
            clen += len(tb)
        return contextb.decode('utf-8')
    r = recv()
    return r
    







