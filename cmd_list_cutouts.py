#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys


parser = argparse.ArgumentParser(description="List all cutouts on the REatlas server");
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

cutouts = atlas.list_cutouts(all_users=True)
atlas.disconnect();

i = 0;
for cutout in cutouts:
     name = cutout[0];
     size = cutout[1];

     if (i%2 == 0):
          fill = " ";
     else:
          fill = ".";
     i += 1;
     if (name.find("/") == -1):
          print((name + " (Total):").ljust(30,fill) + str(size/(1024**3)).rjust(7,fill) + " GB");
     else:
          user,cutout = name.split("/");
          print((cutout + " (" + user + "): ").ljust(30,fill) + str(size/(1024**3)).rjust(7,fill) + " GB");



