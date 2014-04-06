#!/usr/bin/python

from __future__ import print_function
import datetime
import json
from socket import error as socket_error
import sys
import tempfile
import traceback

import argparse
import numpy
import open_layout
import reatlas_client

choices = open_layout.choices


parser = argparse.ArgumentParser(description="Convert and aggregate PV");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument('--name',nargs="?",type=str,help="Name of the conversion")
parser.add_argument("panelconf",nargs=1,type=str,help="Path to the solar panel config file");
parser.add_argument("orientationconf",nargs=1,type=str,help="Path to a file containing orientation specifications.");
parser.add_argument("capacitylayout",nargs="+",type=str,help="Path to capacity layout to use (.npy, .mat, .csv, .shp file)");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");

args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser
conversion_name = args.name;

panelconf = reatlas_client.solarpanelconf_to_solar_panel_config_object(args.panelconf[0]);
orientationconf = args.orientationconf[0];
capacitylayouts = args.capacitylayout;
output = args.output

if (username == None):
     username = raw_input("username: ");

if (password == None):
     password = raw_input("password: ");

try:
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
                  resultArr['data'] = ''
                  print (json.dumps(resultArr));
               #   var = traceback.format_exc().splitlines();
              else:
                  print("Invalid username or password",file=sys.stderr);

    try:
         atlas.add_pv_orientations_by_config_file(orientationconf);
    except ValueError as e:
        if (output == "JSON"):
            resultArr={}
            resultArr['type']="Error"
            resultArr['text']="Value error"
            resultArr['desc']=str(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
            resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb)
            resultArr['data'] = ''
            print (json.dumps(resultArr));
         #   var = traceback.format_exc().splitlines();
        else:
            print("Value error: " + str(e));
        exit(1);
        
    if (output != "JSON"): 
        print("Downloading cutout metadata...");

    f = tempfile.TemporaryFile()
    if (cutoutuser != None):
         atlas.prepare_cutout_metadata(cutoutname=cutoutname,username=cutoutuser)
    else:
         atlas.prepare_cutout_metadata(cutoutname=cutoutname)

    server_filename = "meta_"+cutoutname+".npz";
    atlas.download_file_and_rename(remote_file=server_filename,local_file=f);
    atlas.delete_file(filename=server_filename);
    f.seek(0);
    shape = numpy.load(f)["latitudes"].shape;
    
    if (output != "JSON"): 
        print("Opening and formatting layouts...");
    
    layout_files = [];
    for layout in capacitylayouts:
         layout_files.append(open_layout.open_layout_as_npy(layout,shape))

    if (conversion_name == None):
         conversion_name = atlas._get_unique_npy_file();
         

    else:
          name1 = "solar_"+username+"_"+cutoutname+"_"+conversion_name+".npy";
          conversion_name = name1;

    conversion_name_base = conversion_name[:-4];
    
    if (output != "JSON"): 
        print("Uploading layout(s)...");

    i = 0;
    names = [];
    for layout in layout_files:
         name = conversion_name_base + "_layout_" + str(i).rjust(4,"0") + ".npy";
         atlas.upload_from_file_and_rename(local_file=layout,remote_file=name);
         i += 1;
         names.append(name);

    if (output != "JSON"): 
        print("Starting PV conversion...");


    if (cutoutuser != None):
         atlas.select_cutout(cutoutname=cutoutname,username=cutoutuser);
    else:
         atlas.select_cutout(cutoutname=cutoutname);

    job_id = atlas.convert_and_aggregate_pv(result_name=conversion_name_base,solar_panel_config=panelconf,capacitylayouts=names);

    ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
    ETA = str(datetime.timedelta(seconds=ETA));
    if (output == "JSON"):
        outArr={}
        outArr['type']="Success"
        outArr['text']="Submitted solar conversion job."
        outArr['desc']=" Job id: " + str(job_id).ljust(29) + "<br/>"+\
                       " Result name: " + conversion_name_base.ljust(24) + "<br/>"+\
                       " ETA: " + ETA.ljust(32);
        outArr['traceback']= ''
        outArr['data'] = ''
        print (json.dumps(outArr));
    else:
        print("");
        print("+--- Submitted solar conversion job. ---+")
        print("| Job id: " + str(job_id).ljust(29) + "|");
        print("| Result name: " + conversion_name_base.ljust(24) + "|");
        print("| ETA: " + ETA.ljust(32) + "|");
        print("+------------- cut here ---------------+");

    atlas.disconnect();
    
except socket_error as serr:
 #   if serr.errno != errno.ECONNREFUSED:
    if (output == "JSON"):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']=str(serr.strerror)
        resultArr['desc']=str(serr);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(serr),file=sys.stderr);
except reatlas_client.REatlasError as e:
    # Handle the exception...
    if (output == "JSON"):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in getting cutout list"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);




