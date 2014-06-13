#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os,traceback
import json,re
import errno
from socket import error as socket_error

parser = argparse.ArgumentParser(description="List all layout on the REatlas server");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument("--layoutuser",nargs="?",type=str,help="Layout creator");
parser.add_argument("--cutout",nargs="?",type=str,help="Cutout");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");


args = parser.parse_args();

server = args.server[0];
port = args.port
username = args.username;
password = args.password;
layoutuser = args.layoutuser;
output = args.output;
cutout = args.cutout;

finalLayoutList = [];
           
           
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
    layouts = atlas.list_files()
    atlas.disconnect();
    for layout in layouts:
      if (layoutuser == None):
         myarray = {}
         myarray['layout']=layout[0]
         myarray['layoutSize']=layout[1]
         finalLayoutList.append(myarray)
      else:
         matchObj = re.match( r'^layout_'+layoutuser+'_(.*).npy$', layout[0], re.M|re.I)
         if matchObj:
            if cutout:
                matchObjCut = re.match( r'^layout_'+layoutuser+"_"+cutout+'_(.*).npy$', layout[0], re.M|re.I)
                if matchObj and matchObjCut:
                    myarray = {}
                    myarray['layout']=matchObjCut.group(1)
                    myarray['layoutSize']=layout[1]
                    finalLayoutList.append(myarray)
            else:
                if matchObj:
                    myarray = {}
                    myarray['layout']=matchObj.group(1)
                    myarray['layoutSize']=layout[1]
                    finalLayoutList.append(myarray)
    if (output == "JSON"):
            outArr={}
            outArr['type']="Success"
            outArr['text']="Layout list"
            outArr['desc']="Layout(s) for user:"+str(layoutuser)
            outArr['traceback']= ''
            outArr['data'] = sorted(finalLayoutList, key=lambda k: k['layout'], reverse=True)       
            print (json.dumps(outArr));
    else:
            i = 0;
            for layout in finalLayoutList:
                 name = layout["layout"];
                 size = layout["layoutSize"];

                 if (i%2 == 0):
                      fill = " ";
                 else:
                      fill = ".";
                 i += 1;
                 print((name + " (" + layoutuser + "): ").ljust(30,fill) + str(size/(1024**3)).rjust(7,fill) + " GB");
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
        resultArr['text']="Error in getting layout list"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);


