#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys


parser = argparse.ArgumentParser(description="Cancel your, others or all jobs on the REatlas server.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("--all",action="store_true",help="Cancel _all_ REatlas jobs");
parser.add_argument("--cancel_user",nargs="?",type=str,help="REatlas user name of the user to cancel jobs for");


args = parser.parse_args();
print(args);
server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cancel_all = args.all;
cancel_user = args.cancel_user;


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

if (cancel_all):
     atlas.cancel_all_jobs();
else:
     if (cancel_user == None):
          atlas.cancel_jobs_of_user();
     else:
          atlas.cancel_jobs_of_user(username=cancel_user);
atlas.disconnect();

print("Jobs cancelled. Note that running jobs cannot be cancelled.");


