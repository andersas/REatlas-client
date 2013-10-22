#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import tempfile
import numpy
import datetime
import open_layout

choices = open_layout.choices;

parser = argparse.ArgumentParser(description="Convert and aggregate wind");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument('--name',nargs="?",type=str,help="Name of the conversion")
parser.add_argument("onshorepowercurve",nargs=1,type=str,help="Path to turbine config file for use onshore");
parser.add_argument("offshorepowercurve",nargs=1,type=str,help="Path to turbine config file for use offshore");
parser.add_argument("capacitylayout",nargs="+",type=str,help="Path to capacity layout to use (.npy, .mat, .csv, .shp file)");


args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser
conversion_name = args.name;

onshorecurve = reatlas_client.turbineconf_to_powercurve_object(args.onshorepowercurve[0]);
offshorecurve = reatlas_client.turbineconf_to_powercurve_object(args.offshorepowercurve[0]);
capacitylayouts = args.capacitylayout;

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
print("Opening and formatting layouts...");
layout_files = [];
for layout in capacitylayouts:
     layout_files.append(open_layout.open_layout_as_npy(layout,shape))


if (conversion_name == None):
     conversion_name = atlas._get_unique_npy_file();
else:
     conversion_name += ".npy"

conversion_name_base = conversion_name[:-4];

print("Uploading layout(s)...");

i = 0;
names = [];
for layout in layout_files:
     name = conversion_name_base + "_layout_" + str(i).rjust(4,"0") + ".npy";
     atlas.upload_from_file_and_rename(local_file=layout,remote_file=name);
     i += 1;
     names.append(name);

print("Starting wind conversion...");


if (cutoutuser != None):
     atlas.select_cutout(cutoutname=cutoutname,username=cutoutuser);
else:
     atlas.select_cutout(cutoutname=cutoutname);

job_id = atlas.convert_and_aggregate_wind(result_name=conversion_name_base,onshorepowercurve=onshorecurve,offshorepowercurve=offshorecurve,capacitylayouts=names);

ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
if ETA!=None:
     ETA = str(datetime.timedelta(seconds=ETA));

print("");
print("+--- Submitted wind conversion job. ---+")
print("| Job id: " + str(job_id).ljust(29) + "|");
print("| Result name: " + conversion_name_base.ljust(24) + "|");
print("| ETA: " + ETA.ljust(32) + "|");
print("+------------- cut here ---------------+");

atlas.disconnect();





