#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys
import datetime

parser = argparse.ArgumentParser(description="Get estimated time left for jobs in the work queue.");
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

timings = atlas.get_queued_job_time();
jobs = atlas.list_queued_jobs();

atlas.disconnect();


total = str(datetime.timedelta(seconds=timings["TOTAL"]));



print("Note: The following does not take into account time a job has been running so far.");
print("All work currently in the queue is estimated to be done in " + total + ".");
user_has_a_job_in_queue = False;
for job in jobs:
     if (job["user"] == username):
          user_has_a_job_in_queue = True;
          ETA = str(datetime.timedelta(seconds=job["ETA"]));
          print("Your job " + str(job["job_id"]) + " (" + job["name"] + ") is expected done in " + ETA + ".");

if (not user_has_a_job_in_queue):
     print("You have not jobs waiting.");

