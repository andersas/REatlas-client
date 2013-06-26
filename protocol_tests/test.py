#!/usr/bin/python2

from __future__ import print_function
import socket
import json
import argparse
import struct
import time
import sys

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

request = dict();
request["jsonrpc"] = "2.0";
request["method"] = "login";
user = dict();
user["username"] = "user1";
user["password"] = "1234";
request["params"] = user;
request["id"] = "0";

toserver = json.dumps(request);
toserver = struct.pack("!BQ", 0,len(toserver)) + toserver;

s.sendall(toserver);

while True:
     msg = s.recv(1024*8);
     if len(msg) == 0:
          break;
     else:
          print("Received a message", len(msg),file=sys.stderr);
          print(msg,end="");

try:
     s.shutdown(socket.SHUT_RDWR);
except:
     pass;
s.close();

