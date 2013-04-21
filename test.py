#!/usr/bin/python2

import socket
import json
import argparse
import struct

parser = argparse.ArgumentParser(description="");
parser.add_argument('host',nargs=1,help="Hostname of REatlas server");
parser.add_argument('--port',nargs=1,default=[65535],help="Port number of REatlas server",type=int);

args = parser.parse_args();

host = socket.gethostbyname(args.host[0]);
port = args.port[0];

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
s.connect((host,port));

msg = s.recv(11);
if (msg != "REatlas" + struct.pack('!l',1)):
     print("Bad server version!");
     s.shutdown(socket.SHUT_RDWR);
     s.close();

s.sendall(struct.pack('!H',0xAA55));


s.shutdown(socket.SHUT_RDWR);
s.close();

