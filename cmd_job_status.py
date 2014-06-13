#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import json
import traceback

parser = argparse.ArgumentParser(description="Status of a job on the REatlas server.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("jobid",nargs=1,type=int,help="REatlas job ID");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");


args = parser.parse_args();
server = args.server[0];
port = args.port
username = args.username;
password = args.password;
jobid = args.jobid[0];
output = args.output


message={}
resultarray = {}

if (output == "JSON"):
    returnstatus = True
else:
    returnstatus = False

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
          if(returnstatus):
		message['type']='Error'
		message['text']='Authentication Failure'
		message['desc']= "Invalid username or password"
		exc_type, exc_value, exc_tb = sys.exc_info();
                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                print (json.dumps(message));
          else:
                print("Invalid username or password",file=sys.stderr);
          exit(1);
try:          
    wait_for_job = atlas.wait_for_job(job_id=jobid);
    if (wait_for_job == "Success"):
        if(returnstatus):
            message['type']='Success'
            message['text']='Job finished successfully'
            message['desc']= "A job with '"+str(jobid)+"' done successfully"
            message['traceback']= '';
            print (json.dumps(message));
        else:	
            print("Success");
    elif (wait_for_job == "Failure"):
        if(returnstatus):
            message['type']='Failure'
            message['text']='Job finished with error'
            message['desc']= "Some error occured while processing job with id"+str(jobid)
            exc_type, exc_value, exc_tb = sys.exc_info();
            message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
            print (json.dumps(message));
        else:	  
            print("Some error occured while processing job with id"+str(jobid),file=sys.stderr);
    elif (wait_for_job == "Waiting"):
        if(returnstatus):
            message['type']='Waiting'
            message['text']='Job is still running'
            message['desc']= "A job with id"+str(jobid)+" is still running."
            message['traceback']= '';
            print (json.dumps(message));
        else:	  
            print("A job with id"+str(jobid)+" is still running.",file=sys.stderr);
    else:
        if(returnstatus):
            message['type']='Error'
            message['text']='Job status not found'
            message['desc']= "No status found for job with id: "+str(jobid)
            exc_type, exc_value, exc_tb = sys.exc_info();
            message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
            print (json.dumps(message));
        else:	  
            print("No status found for job with id: "+str(jobid),file=sys.stderr);
except OSError as e:
     # Handle the exception...
    if (returnstatus):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error code:"+str(e.errno)
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
except reatlas_client.REatlasError as e:
    # Handle the exception...
    if (returnstatus):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in getting cutout metadata"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
        
atlas.disconnect();


