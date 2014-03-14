#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os,traceback
import json,re
import errno
from socket import error as socket_error

parser = argparse.ArgumentParser(description="Remove a file on the REatlas server");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('filename',nargs=1,type=str,help="Name of file");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");

args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
infilename = args.filename[0];
output = args.output;

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

          os._exit(1);
    atlas.delete_file(filename=infilename,username=username)
    atlas.disconnect();
    if (output == "JSON"):
            outArr={}
            outArr['type']="Success"
            outArr['text']="File deleted"
            outArr['desc']="File name:"+infilename
            outArr['traceback']= ''
            outArr['data'] = ''       
            print (json.dumps(outArr));
    else:
            print("File deleted. File name:"+infilename);
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
        resultArr['text']="Error in deleting file"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);


