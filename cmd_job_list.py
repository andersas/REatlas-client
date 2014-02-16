#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import os, sys, traceback
import datetime
import json

import logging

# Log everything, and send it to stderr.
#logging.basicConfig(level=logging.DEBUG)


parser = argparse.ArgumentParser(description="Get estimated time left for jobs in the work queue.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");
parser.add_argument('--filterbyuser',nargs="?",type=str,help="Return result for only current user.")

args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
output = args.output;
filterbyuser=args.filterbyuser

if (username == None):
     username = raw_input("username: ");

if (password == None):
     password = raw_input("password: ");

if (port != None):
     atlas = reatlas_client.REatlas(server,port);
else:
     atlas = reatlas_client.REatlas(server);

var = ""

if (not atlas.connect_and_login(username=username,password=password)):
          atlas.disconnect()
          if (output == "JSON"):
              resultArr={}
              resultArr['type']="Error"
              resultArr['text']="Invalid username or password"
              resultArr['desc']="username '"+username+"' or password. Check parameters/settings."
              exc_type, exc_value, exc_tb = sys.exc_info()
              resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb)
              resultArr['data'] = ''
              print (json.dumps(resultArr));
           #   var = traceback.format_exc().splitlines();
          else:    
            print("Invalid username or password",file=sys.stderr);
          exit(1);

timings = atlas.get_queued_job_time();
jobs = atlas.list_queued_jobs();

atlas.disconnect();


total = str(datetime.timedelta(seconds=timings["TOTAL"]));


if (output == "JSON"):
    resultArr=[]
    myarray = {}
    myarray['total_jobs']=len(jobs)
    myarray['total_ETA']=total
    resultArr.append(myarray)
    jobsArr = {}
    
    if(filterbyuser != None):
        jobsArrFilter = []
        jobsArr['filterbyuser']=filterbyuser
        for job in jobs:
             if (job["user"] == filterbyuser):
                  ETA = str(datetime.timedelta(seconds=job["ETA"]));
                  job["ETA"] = ETA
                  jobsArrFilter.append(job)              
        jobsArr['jobs']=jobsArrFilter
    else:
        jobsArr['filterbyuser']='None'
        jobsArr['jobs']=jobs
        
    resultArr.append(jobsArr)
    outArr={}
    outArr['type']="Success"
    outArr['text']="Running Job list"
    outArr['desc']="Currently running job"
    outArr['traceback']= ''
    outArr['data'] = resultArr          
    print (json.dumps(outArr));
else:
    print("Note: The following estimates are quite rough.");
    print("All work currently in the queue is estimated to be done in " + total + ".");
    user_has_a_job_in_queue = False;
    for job in jobs:
        ETA = str(datetime.timedelta(seconds=job["ETA"]));
        if(filterbyuser != None):
            if (job["user"] == filterbyuser):
                user_has_a_job_in_queue = True;
                print("Your job " + str(job["job_id"]) + " (" + job["name"] + ") is expected done in " + ETA + ".");
        else:
            print("Job submitted by "+job["user"]+" : " + str(job["job_id"]) + " (" + job["name"] + ") is expected done in " + ETA + ".");
            
    if (not user_has_a_job_in_queue and filterbyuser != None):
         print(filterbyuser+" has no jobs waiting.");

