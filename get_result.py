#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import tempfile
import numpy
import numbers
import datetime

parser = argparse.ArgumentParser(description="Download .npy,.csv or .mat format.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('job_id',nargs=1,type=int,help="Job id of the job to get the result from.");
parser.add_argument('result_name',nargs=1,type=str,help="Name of the result");
parser.add_argument("filename", nargs=1, type=str,help="Name of the file to save to. If it has no ending or ends with .npy, a numpy file is saved. If it ends with csv, an ASCII csv file will be saved. If it ends in .mat, a matlab file will be saved.");

choices=['.npy','.csv','.mat']

args = parser.parse_args();
job_id = args.job_id[0];
result_name = args.result_name[0];

filename = args.filename[0];

if (filename.endswith(".mat")):
     try:
          import scipy.io
     except ImportError:
          print("You must have scipy installed to save to matlab files.",file=sys.stderr);
          exit(1)

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

# Download the file. If it's a .npy file or one without any of the supported
# endings, download it to that file.
# Otherwise, download to a tempfile and convert.

if len(os.path.basename(filename)) < 4:
     print("Filename must end in one of " + str(choices) + ".",file=sys.stderr);
     exit(1);

ending = filename[-4:];
if (ending not in choices):
     print("Filename must end in one of " + str(choices) + ".");
     exit(1)


if (not atlas.connect_and_login(username=username,password=password)):
          atlas.disconnect()
          print("Invalid username or password",file=sys.stderr);


ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
if (ETA != None):
     print("Job not done yet. ETA: " + str(datetime.timedelta(seconds=ETA)));
     while (not atlas.wait_for_job(job_id=job_id,timeout=30)):
          ETA = atlas.get_estimated_time_before_completion_of_jobs(job_id=job_id);
          if (ETA != None):
               print("Job not done yet. ETA: " + str(datetime.timedelta(seconds=ETA)));
     print("Job done, downloading...");

server_filename = result_name + ".npy";
if (ending == ".npy"):
     print("Saving " + filename + ".");
     atlas.download_file_and_rename(remote_file=server_filename,local_file=filename);
else: #Ok, user does not want a .npy file...
 
     buf = tempfile.TemporaryFile();
     atlas.download_file_and_rename(remote_file=server_filename,local_file=buf);
     buf.seek(0);
    
     timeseries = numpy.load(buf);
 
     if (ending == ".csv"):
          print("Saving " +filename+"...");
          numpy.savetxt(filename,timeseries,delimiter=",");

     elif (ending == ".mat"):
          try:
               import scipy.io;
          except ImportError:
               print("Scipy must be installed to save matlab files.",file=sys.stderr);
               exit(1);

          print("Saving " + filename + ".");
          scipy.io.savemat(filename,mdict={'timeseries':timeseries},oned_as="column");

# Clean up layouts etc.:
files = atlas.list_files();
for f in files:
     name,size = f;
     if (name.startswith(result_name)):
          atlas.delete_file(filename=name);

atlas.disconnect();
