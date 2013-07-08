#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys


parser = argparse.ArgumentParser(description="Shut the REatlas server down.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");


args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;

if (username == None):
     username = raw_input("username: ");

if (password == None):
     password = raw_input("password: ");

if (port != None):
     atlas = reatlas_client.REatlas(server,port);
else:
     atlas = reatlas_client.REatlas(server);

if (not atlas.connect_and_login(username=username,password=password)):
          atlas.disconnect()
          print("Invalid username or password",file=sys.stderr);

cutouts = atlas.shutdown()
atlas.disconnect();

print("Shutdown request sent.")
print("The atlas process will first completely exit when all jobs are done.");

