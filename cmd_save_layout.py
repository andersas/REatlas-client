#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys
import os
import os.path
import tempfile
import numpy
import open_layout
import json
import traceback
import datetime

cwd = os.path.dirname(__file__)

choices = open_layout.choices;

parser = argparse.ArgumentParser(description="Convert and aggregate wind");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument('--name',nargs="?",type=str,help="Name of layout")
parser.add_argument("--metadata",nargs="?",type=str,help="Path to local metadata file(.npz file)");
parser.add_argument("capacitylayout",nargs=1,type=str,help="Path to capacity layout to use (JSON text file)");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");

args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser
layout_name = args.name;
output = args.output;

metadata_file = args.metadata;
capacitylayout = args.capacitylayout[0];

capacitylayoutObj = {}
message={}

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
              resultArr['data'] = ''
              print (json.dumps(resultArr));
           #   var = traceback.format_exc().splitlines();
          else:    
            print("Invalid username or password",file=sys.stderr);
          
if (metadata_file == None):
    if (output != "JSON"):
        print("Downloading cutout metadata...");

    metadata_file = tempfile.NamedTemporaryFile(suffix='.npz')
    if (output != "JSON"):
        print("Tmp cutout file:"+metadata_file.name);
    if (cutoutuser != None):
         atlas.prepare_cutout_metadata(cutoutname=cutoutname,username=cutoutuser)
    else:
         atlas.prepare_cutout_metadata(cutoutname=cutoutname)

    server_filename = "meta_"+cutoutname+".npz";
    atlas.download_file_and_rename(remote_file=server_filename,local_file=metadata_file);
    atlas.delete_file(filename=server_filename);
    f.seek(0);
shape = numpy.load(metadata_file)["latitudes"].shape;

# Make a capacity layout with 0 everywhere but in (i,j)
layoutTmp = numpy.zeros(shape);

if (capacitylayout != None and os.path.isfile(capacitylayout)):
    file = open(capacitylayout, 'r')
    capacitylayoutObj=json.loads(file.read());
else:
    if (output == "JSON"):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in getting cutout details"
        resultArr['desc']=statusArray['desc'];
        resultArr['traceback']= statusArray['traceback'];
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(out), file=sys.stderr, end='');
    exit(1);
    
for idx, val in enumerate(capacitylayoutObj):
    if(val == None):
      continue;
    for idx1, val1 in enumerate(val):
        if(val1 == None):
            continue;
        layoutTmp[idx,idx1] = val1;

i=0

if (layout_name == None):
    # layout_name = atlas._get_unique_npy_file();
    layout_name = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")+".npy"
    layout_name_base = layout_name[:-4];
    name = "layout_"+username+"_"+cutoutname+"_" +layout_name_base +"_"+ str(i).rjust(4,"0") + ".npy";
else:
     layout_name += ".npy"
     name = layout_name;

if (output != "JSON"):
    print("Opening and formatting layouts...");

if (output != "JSON"):
    print("Uploading layout...");

numpy.save(cwd+"/data/"+username+"/"+name,layoutTmp);
layout_file=open_layout.open_layout_as_npy(cwd+"/data/"+username+"/"+name,shape)
atlas.upload_from_file_and_rename(local_file=layout_file,remote_file=name);
     
if (output == "JSON"):
        outArr={}
        outArr['type']="Success"
        outArr['text']="Layout uploaded"
        outArr['desc']="Layout for user:"+str(username)+" LayoutName:"+name
        outArr['traceback']= ''
        outArr['data'] = ''
        print (json.dumps(outArr));
else:
    print("");
    print("+--- Uploaded layout. --------------------+")
    print("| Result name: " + str(name).ljust(24) + "|");
    print("+------------- cut here ------------------+");

atlas.disconnect();





