#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os,traceback
import json,re
import errno
from socket import error as socket_error

parser = argparse.ArgumentParser(description="List all cutouts on the REatlas server");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("--cutoutuser",nargs="?",type=str,help="Cutout creator");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");


args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
cutoutuser = args.cutoutuser;
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
    cutouts = atlas.list_cutouts(all_users=True)
    atlas.disconnect();
    if (output == "JSON"):
            finalCutoutList = []
            for cutout in cutouts:
              if (cutoutuser == None):
                 myarray = {}
                 myarray['cutout']=cutout[0]
                 myarray['cutoutSize']=cutout[1]
                 finalCutoutList.append(myarray)
              else:
                 matchObj = re.match( r'^'+cutoutuser+'/(.*$)', cutout[0], re.M|re.I)
                 if matchObj:
                    myarray = {}
                    myarray['cutout']=matchObj.group(1)
                    myarray['cutoutSize']=cutout[1]
                    finalCutoutList.append(myarray)
            outArr={}
            outArr['type']="Success"
            outArr['text']="Cutout list"
            outArr['desc']="Cutouts for user:"+str(cutoutuser)
            outArr['traceback']= ''
            outArr['data'] = finalCutoutList      
            print (json.dumps(outArr));
    else:
            i = 0;
            for cutout in cutouts:
                 name = cutout[0];
                 size = cutout[1];

                 if (i%2 == 0):
                      fill = " ";
                 else:
                      fill = ".";
                 i += 1;
                 if (name.find("/") == -1):
                      print((name + " (Total):").ljust(30,fill) + str(size/(1024**3)).rjust(7,fill) + " GB");
                 else:
                      user,cutout = name.split("/");
                      print((cutout + " (" + user + "): ").ljust(30,fill) + str(size/(1024**3)).rjust(7,fill) + " GB");
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


