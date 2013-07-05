#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys
import tempfile

parser = argparse.ArgumentParser(description="List all cutouts on the REatlas server");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument("filename", nargs=1, type=str,help="Name of the file to save to. If it has no ending or ends with .npz, a numpy file is saved. If it ends with csv, an ASCII csv file will be saved. If it ends in .mat, a matlab file will be saved, and if the filename ends with .shp, a shapefile (arcgis) will be saved.");

choices=['.npz','.csv','.mat','.shp']

args = parser.parse_args();

cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser

filename = args.filename[0];

if (filename.endswidth(".mat")):
     try:
          import scipy.io
     except ImportError:
          print("You must have scipy installed to save to matlab files.",file=sys.stderr);
          exit(1)
elif (filename.endswith(".shp")):
     try:
          import shapefile
     except ImportError:
          print("You must have the python library \"shapefile\" installed to save to shapefiles.",file=sys.stderr);
          exit(1);

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

if (cutoutuser != None):
     atlas.prepare_cutout_metadata(cutoutname=cutoutname,username=cutoutuser);
else:
     atlas.prepare_cutout_metadata(cutoutname=cutoutname);

# Download the file. If it's a .npz file or one without any of the supported
# endings, download it to that file.
# Otherwise, download to a tempfile and convert.

if len(filename) < 4:
     filename += ".npz";

ending = filename[-4:];
if (ending not in choices or ending == ".npz"):
     if ending != ".npz":
          filename += ".npz"
     atlas.download_file_and_rename(remote_file="meta_"+cutoutname+".npz",local_file=filename);
else: #Ok, user does not want a .npz file...
     





atlas.disconnect();



