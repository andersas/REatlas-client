#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import tempfile
import numpy
import numbers
import json
import traceback

message = {}
parser = argparse.ArgumentParser(description="Download metadata for a REatlas cutout as either .npz,.csv,.mat or .shp format.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument('--returnstatus',action='store_true',help="Return seccess /  error as response. Usefull if script is called from another script.")
parser.add_argument("filename", nargs=1, type=str,help="Name of the file to save to. If it has no ending or ends with .npz, a numpy file is saved. If it ends with csv, an ASCII csv file will be saved. If it ends in .mat, a matlab file will be saved, and if the filename ends with .shp, a shapefile (arcgis) will be saved.");

choices=['.npz','.csv','.mat','.shp']

args = parser.parse_args();

cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser
returnstatus = args.returnstatus

filename = args.filename[0];
outputFolder = 'shapeData'

if (filename.endswith(".mat")):
     try:
          import scipy.io
     except ImportError:
        if(returnstatus):
	        message['type']='Error'
	        message['text']='Module missing'
	        message['desc']= "You must have scipy installed to save to matlab files."
                exc_type, exc_value, exc_tb = sys.exc_info();
                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                print (json.dumps(message));
        else:	  
	        print("You must have scipy installed to save to matlab files.",file=sys.stderr);
        exit(1);
elif (filename.endswith(".shp")):
     try:
          import shapefile
     except ImportError:
        if(returnstatus):
		    message['type']='Error'
		    message['text']='Module missing'
		    message['desc']= "You must have the python library \"shapefile\" installed to save to shapefiles."
		    exc_type, exc_value, exc_tb = sys.exc_info();
                    message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                    print (json.dumps(message));
        else:  
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

# Download the file. If it's a .npz file or one without any of the supported
# endings, download it to that file.
# Otherwise, download to a tempfile and convert.

if len(os.path.basename(filename)) < 4:
    if(returnstatus):
		message['type']='Error'
		message['text']='File extension error'
		message['desc']= "Filename must end in one of " + str(choices) + "."
                exc_type, exc_value, exc_tb = sys.exc_info();
                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                print (json.dumps(message));
    else:	
	     print("Filename must end in one of " + str(choices) + ".",file=sys.stderr);
    exit(1);

ending = filename[-4:];
if (ending not in choices):
     if(returnstatus):
		message['type']='Error'
		message['text']='Filename error'
		message['desc']= "Filename must end in one of " + str(choices) + "."
                exc_type, exc_value, exc_tb = sys.exc_info();
                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                print (json.dumps(message));
     else:	  
          print("Filename must end in one of " + str(choices) + ".",file=sys.stderr);
     exit(1)

if (not atlas.connect_and_login(username=username,password=password)):
          atlas.disconnect()
	  if(returnstatus):
		message['type']='Error'
		message['text']='Authentication Failure'
		message['desc']= "Invalid username or password"
		exc_type, exc_value, exc_tb = sys.exc_info();
                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                print (json.dumps(message));
          else:	  
               print("Invalid username or password.",file=sys.stderr);
	  exit(1);
try:
    if (cutoutuser != None):
         atlas.prepare_cutout_metadata(cutoutname=cutoutname,username=cutoutuser);
    else:
         atlas.prepare_cutout_metadata(cutoutname=cutoutname);
except reatlas_client.REatlasError as e:
    # Handle the exception...
    if (returnstatus):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in getting cutout metadata"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
    exit(1);
    
server_filename = "meta_"+cutoutname+".npz";
try:
    if (ending == ".npz"):
        if(returnstatus != True):
            print("Saving " + filename + ".");
        atlas.download_file_and_rename(remote_file=server_filename,local_file=filename);
        atlas.delete_file(filename=server_filename);
        atlas.disconnect();
    else: #Ok, user does not want a .npz file...

         buf = tempfile.TemporaryFile();
         atlas.download_file_and_rename(remote_file=server_filename,local_file=buf);
         atlas.delete_file(filename=server_filename);
         atlas.disconnect();
         buf.seek(0);

         meta_npz = numpy.load(buf);
         meta = dict();
         for key in meta_npz.files:
              meta[key] = meta_npz[key];
         meta["dates"] = numpy.array([date.isoformat() for date in meta["dates"]]);

         if (ending == ".csv"):

              for key in meta.iterkeys():
                   curr_filename = filename[0:-4] + "_" + key + ".csv";
                   if(returnstatus != True):
                      print("Saving " +outputFolder+"/"+curr_filename+"...");
                   if (isinstance(meta[key].flatten()[0],numbers.Number)):
                        numpy.savetxt(outputFolder+"/"+curr_filename,meta[key],delimiter=",");
                   else:
                        numpy.savetxt(outputFolder+"/"+curr_filename,meta[key],delimiter=",",fmt="%s");



         elif (ending == ".mat"):
              try:
                   import scipy.io;
              except ImportError:
                if(returnstatus):
                                message['type']='Error'
                                message['text']='Module missing'
                                message['desc']= "Scipy must be installed to save matlab files."
                                exc_type, exc_value, exc_tb = sys.exc_info();
                                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                                print (json.dumps(message));
                else:	  
                    print("Scipy must be installed to save matlab files.",file=sys.stderr);
                exit(1);
              if(returnstatus != True):
                  print("Saving " + outputFolder+"/"+filename + ".");
              scipy.io.savemat(outputFolder+"/"+filename,mdict=meta,oned_as="column");

         elif (ending == ".shp"):
              try:
                   import shapefile;
              except ImportError:
                if(returnstatus):
                            message['type']='Error'
                            message['text']='Module missing'
                            message['desc']= "Shapefile (pyshp) must be installed to save to shapefiles."
                            exc_type, exc_value, exc_tb = sys.exc_info();
                            message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                            print (json.dumps(message));
                else:	
                        print("Shapefile (pyshp) must be installed to save to shapefiles.",file=sys.stderr);
                exit(1);


              sf = shapefile.Writer(shapefile.POINT);
              sf.field("LATITUDE",'O',8,0);
              sf.field("LONGITUDE",'O',8,0);
              sf.field("IDX1",'N',8,0);
              sf.field("IDX2",'N',8,0);
              sf.field("ONSHORE",'L',1);
              sf.field("HEIGHT",'O',8);
              sf.field("CAPACITY",'O',8,0);

              latitudes = meta["latitudes"];
              longitudes = meta["longitudes"];

              if (len(latitudes.shape) > 2):
                if(returnstatus):
                                message['type']='Error'
                                message['text']='Cutout support error'
                                message['desc']= "Supports only 1 or 2D cutouts."
                                exc_type, exc_value, exc_tb = sys.exc_info();
                                message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
                                print (json.dumps(message));
                else:	
                        print("Supports only 1 or 2D cutouts",file=sys.stderr);
                exit(1);
              if (len(latitudes.shape) == 2):
                   I,J = latitudes.shape;
                   for i in range(I):
                        for j in range(J):
                             lat, lon = latitudes[i][j],longitudes[i][j];
                             onshore = bool(meta["onshoremap"][i][j]);
                             height = meta["heights"][i][j];
                             capacity = 0.0;
                             sf.point(lon,lat);
                             rec = [lat,lon,i,j,onshore,height,capacity];
                             sf.record(*rec);
              else:
                   I = latitudes.shape[0];
                   for i in range(I):
                        lat, lon = latitudes[i],longitudes[i];
                        onshore = bool(meta["onshoremap"][i]);
                        height = meta["heights"][i];
                        capacity = 0.0;
                        sf.point(lon,lat);
                        rec = [lat,lon,0,i,onshore,height,capacity];
                        sf.record(*rec);
              if(returnstatus):
                 print("Saving " + outputFolder+"/"+filename + "...");
              sf.save(outputFolder+"/"+filename);
              # Add info about projections (otherwise ArcGis refuses to open the file) (generated by qgis, i.e. open file and save it back):
              open(outputFolder+"/"+filename[0:-4] + ".prj","w+").write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]');
              open(outputFolder+"/"+filename[0:-4] + ".qpj","w+").write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]]');
              # Dates
              dates_filename = filename[0:-4] + "_dates.csv";
              if(returnstatus):
                 print("Saving " + outputFolder+"/"+dates_filename + ".");
              numpy.savetxt(outputFolder+"/"+dates_filename,meta["dates"],delimiter=",",fmt="%s");
    if(returnstatus):
        message['type']='Success'
        message['text']='Cutout metadata generated successfully'
        message['desc']= "Metadata '"+filename+"' for cutout: '"+cutoutname+"' generated successfully"
        exc_type, exc_value, exc_tb = sys.exc_info();
        message['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(message));
    else:	
        print("Success");
except OSError as e:
     # Handle the exception...
    if (returnstatus):
        resultArr={}
        resultArr['type']="OS Error"
        resultArr['text']="Error code:"+str(e.errno)
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
except reatlas_client.REatlasError as e:
    # Handle the exception...
    if (returnstatus):
        resultArr={}
        resultArr['type']="Error"
        resultArr['text']="Error in getting cutout metadata"
        resultArr['desc']=str(e);
        exc_type, exc_value, exc_tb = sys.exc_info();
        resultArr['traceback']= traceback.format_exception(exc_type, exc_value, exc_tb);
        print (json.dumps(resultArr));
    else:
        print("Error code "+str(e),file=sys.stderr);
