#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import tempfile
import numpy
import datetime


choices = [".npy",".csv",".mat",".shp"];

def open_layout_as_npy(filename,shape):
     if (len(os.path.basename(filename)) < 4):
          print("File must end in .npy, .mat, .csv or shp.");
          exit(1);
     ending = filename[-4:];
     if (ending not in choices):
          print("Filename must end in one of " + str(choices) + ".");
          exit(1);

     if (ending == ".npy"):
          f = open(filename,"rb");
          layout=numpy.load(f);
          f.seek(0);
          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);

     if (ending == ".csv"):
          layout = numpy.loadtxt(filename,delimiter=",");
          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);

          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);
          return f;

     if (ending == ".mat"):
          try:
               import scipy.io;
          except ImportError:
               print("scipy must be installed in order to read matlab files.",file=sys.stderr);
               exit(1);

          matlayout = scipy.io.loadmat(filename);
          n_useful_keys = 0;
          thekey = None
          for key in matlayout.keys():
               if not key.startswith("__"):
                    n_useful_keys += 1;
                    thekey = key;
                    print("Found array: " + key + ".");
          if (n_useful_keys == 0):
               print("No arrays found in matlab file. Quitting.\n",file=sys.stderr);
               exit(1);
          if (n_useful_keys > 1):
               print("More than one array in " + filename + ". Too ambiguous.",file=sys.stderr);
               exit(1)
          print("Using layout " + key + " from " + filename + ".");

          layout = matlayout[thekey];
          if (len(layout.shape) == 2 and len(shape) == 1):
               if (layout.shape[0] == 1 or layout.shape[1] == 1):
                    layout = layout.flatten();

          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);
     
          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);
          return f;

     if (ending == ".shp"):
          try:
               import shapefile
          except ImportError:
               print("Shapefile (pyshp) must be installed to save to shapefiles.",file=sys.stderr);
               exit(1);

          sf = shapefile.Reader(filename);

          required_fields = ["IDX1", "IDX2", "CAPACITY"];
          idxes = dict();
          fields = sf.fields;
         
          i = 0;
          for field in fields:
               if field in required_fields:
                    required_fields.pop(required_fields.index(field));
                    idxes[field] = i;
               i+=1;
          if (len(required_fields) != 0):
               print("Required records fields missing: " + str(required_fields) + ".",file=sys.stderr);
               exit(1);

          records = sf.records();
          
          layout = numpy.zeros(shape);
          for rec in records:
               i,j = rec[idxes["IDX1"]], rec[idxes["IDX2"]];
               if (len(layout == 1)):
                    if (i != 0 or j < 0 or j >= shape[0]):
                         print("Point outside cutout: IDX1 = " + str(i) + " + IDX2 = "+  str(j) + ".",file=sys.stderr);
                         exit(1);
                    layout[j] = rec[idxes["capacity"]];
               else:
                    if (i < 0 or i >= shape[0] or j < 0 or j >= shape[1]):
                         print("Point outside cutout: IDX1 = " + str(i) + " + IDX2 = " + str(j) + ".",file=sys.stderr);
                         exit(1);
                    layout[rec[idxes["IDX1"]],rec[idxes["IDX2"]]] = rec[idxes["capacity"]];

          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);

          return f;
              
     raise Exception("Unimplemented file type "+ ending + " !");


parser = argparse.ArgumentParser(description="Convert and aggregate PV");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument("panelconf",nargs=1,type=str,help="Path to the solar panel config file");
parser.add_argument("orientationconf",nargs=1,type=str,help="Path to a file containing orientation specifications.");
parser.add_argument("capacitylayout",nargs="+",type=str,help="Path to capacity layout to use (.npy, .mat, .csv, .shp file)");


args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser

panelconf = reatlas_client.solarpanelconf_to_solar_panel_config_object(args.panelconf[0]);
orientationconf = args.orientationconf[0];
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

try:
     atlas.add_pv_orientations_by_config_file(orientationconf);
except ValueError as e:
     print("Value error: " + str(e));
     exit(1);

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
     layout_files.append(open_layout_as_npy(layout,shape))

conversion_name = atlas._get_unique_npy_file();
conversion_name_base = conversion_name[:-4];

print("Uploading layout(s)...");

i = 0;
names = [];
for layout in layout_files:
     name = conversion_name_base + "_layout_" + str(i).rjust(4,"0") + ".npy";
     atlas.upload_from_file_and_rename(local_file=layout,remote_file=name);
     i += 1;
     names.append(name);

print("Starting PV conversion...");


if (cutoutuser != None):
     atlas.select_cutout(cutoutname=cutoutname,username=cutoutuser);
else:
     atlas.select_cutout(cutoutname=cutoutname);

job_id = atlas.convert_and_aggregate_pv(result_name=conversion_name_base,solar_panel_config=panelconf,capacitylayouts=names);

ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
ETA = str(datetime.timedelta(seconds=ETA));

print("");
print("+--- Submitted wind conversion job. ---+")
print("| Job id: " + str(job_id).ljust(29) + "|");
print("| Result name: " + conversion_name_base.ljust(24) + "|");
print("| ETA: " + ETA.ljust(32) + "|");
print("+------------- cut here ---------------+");


atlas.disconnect();





