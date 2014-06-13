#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import socket, errno
import traceback,json
import datetime

parser = argparse.ArgumentParser(description="Create a rectangular cutout.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("cutout_name", nargs=1,type=str,help="Name of the cutout");
parser.add_argument("-fy","--firstyear",nargs="?",type=int,help="First year to extract");
parser.add_argument("-ly","--lastyear",nargs="?",type=int,help="Last year to extract");
parser.add_argument("-fm","--firstmonth",nargs="?",type=int,help="First month in start year to extract");
parser.add_argument("-lm","--lastmonth",nargs="?",type=int,help="Last month in enyear to extract");
parser.add_argument("southwest_latitude", nargs=1,type=float,help="Latitude (in degrees) of southwesternmost point in rectangle");
parser.add_argument("southwest_longitude", nargs=1,type=float,help="Longitude (in degrees) of southwesternmost point in rectangle");
parser.add_argument("northeast_latitude", nargs=1,type=float,help="Latitude (in degrees) of northeasternmost point in rectangle");
parser.add_argument("northeast_longitude", nargs=1,type=float,help="Longitude (in degrees) of northeasternmost point in rectangle");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");


args = parser.parse_args();

cutout_args = dict();
cutout_args["name"] = args.cutout_name[0]
cutout_args["southwest"] = [args.southwest_latitude[0], args.southwest_longitude[0]];
cutout_args["northeast"] = [args.northeast_latitude[0], args.northeast_longitude[0]];

for name in ["firstyear", "lastyear", "firstmonth", "lastmonth"]:
     if (getattr(args,name) != None):
          cutout_args[name] = getattr(args,name);

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
output = args.output;

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
          if (output == "JSON"):
               resultArr={}
               resultArr['type']="Error"
               resultArr['text']="Invalid username or password"
               resultArr['desc']="Invalid username or password"
               exc_type, exc_value, exc_tb = sys.exc_info()
               resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb)
               print (json.dumps(resultArr));
            #   var = traceback.format_exc().splitlines();
          else:
              print("Invalid username or password",file=sys.stderr);
          os._exit(1);
try:
    job_id = atlas.cutout_CFSR_rectangular_by_GPS_coordinates(**cutout_args);

    ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
    atlas.disconnect();
    if (ETA != None):
        ETA/=60.0*60.0;
        ETA = int(round(ETA))
        ETA = str(datetime.timedelta(seconds=ETA));
        if (output == "JSON"):
            resultArr={}
            resultArr['type']="Success"
            resultArr['text']="Rectangular cutout job submitted"
            resultArr['desc']="Rectangular cutout job submitted to REatlas with job id " + str(job_id)+". Expected completion in " + str(ETA) + " hours."
            resultArr['data'] = '{"job_id":'+ str(job_id)+',"resultname":"'+ cutout_args["name"] +'","ETA":"'+ETA.ljust(32)+'"}'
            resultArr['traceback']= ''
            print (json.dumps(resultArr));
        else:
            print("Rectangular cutout job submitted to REatlas with job id " + str(job_id));
            print("Expected completion in " + str(ETA) + " hours.");
            print("You will receive an email when the cutout is done.");
    else:
        if (output == "JSON"):
            resultArr={}
            resultArr['type']="Error"
            resultArr['text']="Error in job submission"
            resultArr['desc']="Something may have gone wrong..."
            exc_type, exc_value, exc_tb = sys.exc_info()
            resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb)
            print (json.dumps(resultArr));
        else:
            print("Something may have gone wrong...");

except reatlas_client.REatlasError as e:
    # Handle the exception...
    if (output == "JSON"):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in job submission"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
   




