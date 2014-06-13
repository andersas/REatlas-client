#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import socket, errno
import traceback,json


parser = argparse.ArgumentParser(description="Create a pointwise cutout");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("cutout_name", nargs=1,type=str,help="Name of the cutout");
parser.add_argument("-fy","--firstyear",nargs="?",type=int,help="First year to extract");
parser.add_argument("-ly","--lastyear",nargs="?",type=int,help="Last year to extract");
parser.add_argument("-fm","--firstmonth",nargs="?",type=int,help="First month in start year to extract");
parser.add_argument("-lm","--lastmonth",nargs="?",type=int,help="Last month in enyear to extract");
parser.add_argument("GPS_coordinate_pairs", nargs="+",type=str,help="A list of latitudes and longitudes in degrees of each point (e.g. 57.4,7.5 59,9)");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");


args = parser.parse_args();

cutout_args = dict();
cutout_args["name"] = args.cutout_name[0]
cutout_args["latitudes"] = [];
cutout_args["longitudes"] = [];

coordinates = args.GPS_coordinate_pairs;

for coordinate in coordinates:
     latlon = coordinate.split(",");
     if (len(latlon) != 2):
          print("Invalid coordinate \"" + coordinate + "\". Must be latitude,longitude in degrees.",file=sys.stderr);
          exit(1);
     try:
          lat,lon = float(latlon[0]),float(latlon[1])
     except ValueError:
          print("Invalid latitude, longitude pair \"" + coordinate + "\".",file=sys.stderr);
          exit(1);
     cutout_args["latitudes"].append(lat);
     cutout_args["longitudes"].append(lat);


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


idx1, idx2 = atlas.translate_GPS_coordinates_to_CFSR_index(latitudes=cutout_args["latitudes"],longitudes=cutout_args["longitudes"]);
points = []
for i in range(len(idx1)):
     points.append((idx1[i],idx2[i],i));

points.sort();

last = points[0];
for i in range(1,len(points)):
     if (last[0] == points[i][0] and last[1] == points[i][1]):
          k,l = last[2],points[i][2];
          
          print(coordinates[k] + " and " + coordinates[l] + " are in the same grid cell.",file=sys.stderr);
          exit(1);
try:     
    job_id = atlas.cutout_CFSR_individual_points_by_GPS_coordinates(**cutout_args);

    ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
    atlas.disconnect();

    if (ETA != None):
        ETA/=60.0*60.0;
        ETA = int(round(ETA))
        if (output == "JSON"):
            resultArr={}
            resultArr['type']="Success"
            resultArr['text']="Pointwise cutout job submitted"
            resultArr['desc']="Pointwise cutout job submitted to REatlas with job id " + str(job_id)+". Expected completion in " + str(ETA) + " hours."
            resultArr['data'] = '{"job_id":'+ str(job_id)+',"resultname":"'+ cutout_name +'","ETA":"'+ETA.ljust(32)+'"}'
            resultArr['traceback']= ''
            print (json.dumps(resultArr));
        else:
            print("Pointwise cutout job submitted to REatlas with job id " + str(job_id));
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



