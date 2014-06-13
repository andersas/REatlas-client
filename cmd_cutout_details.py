#! /usr/bin/python
from __future__ import print_function
import decimal
import json
import os
import subprocess
import sys
import traceback
import argparse
import numpy
import reatlas_client

cwd = os.path.dirname(__file__)
		
message={}
resultarray = {}
limitextentObj = {}

def get_cutout_details(filename):
	try:
		loadedObject = numpy.load(filename);
		cutout_dim = numpy.array(loadedObject["longitudes"].shape).size;
		if cutout_dim == 1:
			resultarray['cutout_type'] = 'MultiPoint';
			resultarray['points'] = []
			numberOfPoints = numpy.array(loadedObject["longitudes"]).size;
			mpLongitudes = numpy.array(loadedObject["longitudes"]);
			mpLatitudes = numpy.array(loadedObject["latitudes"]);
			for index in range(numberOfPoints):
				pointarray = {}
				pointarray['latitude'] = mpLatitudes[index]
				pointarray['longitude'] = mpLongitudes[index]
				resultarray['points'].append(pointarray)
		elif cutout_dim == 2:
			resultarray['cutout_type']='Rectangle';
			resultarray['max_latitude'] = numpy.array(loadedObject["latitudes"])[numpy.array(loadedObject["latitudes"]).shape[0]-1][0];
			resultarray['min_latitude'] = numpy.array(loadedObject["latitudes"])[0][0];
			resultarray['min_longitude'] = numpy.array(loadedObject["longitudes"])[0][0];
			resultarray['max_longitude'] = numpy.array(loadedObject["longitudes"])[0][numpy.array(loadedObject["longitudes"]).shape[1]-1];
		else:
			print ('{"error":"Cutout type not supported"}')

				
	except IOError as e:
	    print ("I/O error({0}): {1} {2}".format(e.errno, e.strerror,filename))
	except ValueError:
	    print ("Could not convert data to an integer.")
	except:
	    print ("Unexpected error:", sys.exc_info()[0])
	    raise

        return resultarray;

def get_cutout_points(filename):
    resultpointarray = {}
    try:
            loadedObject = numpy.load(filename);
            cutout_dim = numpy.array(loadedObject["longitudes"].shape).size;
            mpLongitudes = numpy.array(loadedObject["longitudes"]);
            mpLatitudes = numpy.array(loadedObject["latitudes"]);
            mpOnshoremap = numpy.array(loadedObject["onshoremap"]);
            mpHeights = numpy.array(loadedObject["heights"]);
           
            if cutout_dim == 1:
                numberOfPoints = numpy.array(loadedObject["longitudes"]).size;
                for index in range(numberOfPoints):
                    pointarray = {}
                    pointarray["latitude"] = mpLatitudes[index]
                    pointarray["longitude"] = mpLongitudes[index]
                    pointarray["onshore"] = mpOnshoremap[index]
                    pointarray["height"] = mpHeights[index]
                    pointarray["capacity"] = 0.0;
                    if limitextentObj:
                         if ((pointarray["longitude"] >= limitextentObj["xmin"] and pointarray["longitude"] <= limitextentObj["xmax"])
                               or (pointarray["latitude"] >= limitextentObj["ymin"] and pointarray["latitude"] <= limitextentObj["ymax"])):
                                  resultpointarray[index]=pointarray;
                    else:
                        resultpointarray[index]=pointarray;
            elif cutout_dim == 2:
                dimSize = numpy.array(mpLongitudes.shape);
                xSize=dimSize[0];
                ySize=dimSize[1];
                for xIndex in range(xSize):
                    yArry = []
                    for yIndex in range(ySize):
                        pointarray = {}
                        pointarray["latitude"] = mpLatitudes[xIndex][yIndex]
                        pointarray["longitude"] = mpLongitudes[xIndex][yIndex]
                        pointarray["onshore"] = mpOnshoremap[xIndex][yIndex]
                        pointarray["height"] = mpHeights[xIndex][yIndex]
                        pointarray["capacity"] = 0.0;
                      #  print("long:"+str(pointarray["longitude"])+"xmin:"+str(limitextentObj["xmin"])+" xmax:"+str(limitextentObj["xmax"])+" ymin:"+str(limitextentObj["ymin"])+" ymax:"+str(limitextentObj["ymax"]));
                        if limitextentObj:
                            if ((pointarray["longitude"] >= limitextentObj["xmin"] and pointarray["longitude"] <= limitextentObj["xmax"])
                               and (pointarray["latitude"] >= limitextentObj["ymin"] and pointarray["latitude"] <= limitextentObj["ymax"])):
                                   yArry.append(pointarray);
                        else:
                            yArry.append(pointarray);
                   
                    if yArry:        
                        #resultpointarray.append(yArry)
                        resultpointarray[xIndex]=yArry;

            else:
                    print ('{"error":"Cutout type not supported"}')   

    except IOError as e:
        print ("I/O error({0}): {1} {2}".format(e.errno, e.strerror,filename))
    except ValueError:
        print ("Could not convert data to an integer.")
    except:
        print ("Unexpected error:", sys.exc_info()[0])
        raise
    return resultpointarray;

def datatype_defaults(obj):
   # print(type(obj))
    if isinstance(obj, numpy.uint8):
        return int(obj)
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

parser = argparse.ArgumentParser(description="Download metadata for a REatlas cutout as either .npz,.csv,.mat or .shp format.");
parser.add_argument('server',nargs=1,type=str,help="Name or IP of REatlas server");
parser.add_argument('-p', '--port', nargs="?", type=int,help="Port number of REatlas server");
parser.add_argument("--username",nargs="?",type=str,help="REatlas user name");
parser.add_argument("--password",nargs="?",type=str,help="REatlas password");
parser.add_argument('cutoutname',nargs=1,type=str,help="Name of the cutout");
parser.add_argument('--cutoutuser',nargs="?",type=str,help="Name of the owner of the cutout")
parser.add_argument("filename", nargs=1, type=str,help="Name of the file to save to. If it has no ending or ends with .npz, a numpy file is saved. If it ends with csv, an ASCII csv file will be saved. If it ends in .mat, a matlab file will be saved, and if the filename ends with .shp, a shapefile (arcgis) will be saved.");
parser.add_argument("--withdata",action='store_true',help="Include grid points data.If not mentioned only summary details will be returned");
parser.add_argument("--output",nargs="?",type=str,help="output type (print/JSON) ");
parser.add_argument("--limitextent",nargs="?",type=str,help="Limit return data based on specified Extent data in JSON format.E.g. {\"xmin\":1002928.7248612981,\"ymin\":7578891.023036131,\"xmax\":1188670.7035943475,\"ymax\":7680858.018768595}");
parser.set_defaults(withdata=False)

choices=['.npz','.csv','.mat','.shp']

args = parser.parse_args();

cutoutname = args.cutoutname[0];
cutoutuser = args.cutoutuser
output = args.output;
filename = args.filename[0];
withdata=args.withdata;
limitextent=args.limitextent;

if (limitextent != None):
    limitextentObj=json.loads(args.limitextent);

if (filename.endswith(".mat")):
 try:
      import scipy.io
 except ImportError:
    if(returnstatus):
        message['type']='Error'
        message['text']='Module missing'
        message['desc']= "You must have scipy installed to save to matlab files."
        message['traceback']= ''
        print (json.dumps(message));
    else:	  
        print >> sys.stderr,"You must have scipy installed to save to matlab files."
    exit(1);
elif (filename.endswith(".shp")):
 try:
      import shapefile
 except ImportError:
    if(returnstatus):
	    message['type']='Error'
	    message['text']='Module missing'
	    message['desc']= "You must have the python library \"shapefile\" installed to save to shapefiles."
	    message['traceback']= ''
	    print (json.dumps(message));
    else:  
        print >> sys.stderr,"You must have the python library \"shapefile\" installed to save to shapefiles."
    exit(1);

server = args.server[0];
port = args.port
username = args.username;
password = args.password;

if (username == None):
     username = raw_input("username: ");

if (password == None):
     password = raw_input("password: ");

statusArray={}
try:
    # Fetch generated Cutout if it doesnt exists locally
    if not os.path.exists(filename):
        proc = subprocess.Popen("python "+cwd+"/cmd_get_cutout_metadata.py "+server+" "+cutoutname+" "+filename+" --username "+username+" --password "+password+" --cutoutuser "+cutoutuser+" --returnstatus", shell=True, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        statusArray=json.loads(out)
        #os.system("python "+cwd+"/cmd_get_cutout_metadata.py "+server+" "+cutoutname+" "+cwd+"/"+filename+" --username "+username+" --password "+password+" --cutoutuser "+cutoutuser+" > /dev/null 2>&1");
       
        #Fetch required details from Metadata file	
        if (statusArray['type'] == "Error"):
            if (output == "JSON"):
                resultArr={}
                resultArr['type']="Error"
                resultArr['text']="Error in getting cutout details"
                resultArr['desc']=statusArray['desc'];
                resultArr['traceback']= statusArray['traceback'];
                print (json.dumps(resultArr));
            else:
                print >> sys.stderr,"Error code "+str(out)
            exit(1);
            
    if os.path.exists(filename):
        resultArr=get_cutout_details(filename)
        if withdata:
            resultpointarray=get_cutout_points(filename)
        if (output == "JSON"):
            outArr={}
            outArr['type']="Success"
            outArr['text']="Cutout details"
            outArr['desc']="Details for cutout "+str(cutoutname)
            outArr['traceback']= ''
            outArr['summary'] = resultArr 
            if withdata:
                outArr['data'] = resultpointarray
                outArr['size'] = "{ \"rows\":"+str(len(resultpointarray))+",\"columns\":"+(str(len(resultpointarray.itervalues().next())) if len(resultpointarray)>0 else str(0))+"}"
           # print(str(len(resultpointarray))+" "+str(len(resultpointarray[0])))
            print (json.dumps(outArr, default=datatype_defaults));
        else:
            if withdata:
                print (json.dumps(resultpointarray, default=datatype_defaults));
            else:
                print (json.dumps(resultArr, default=datatype_defaults));
            
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
        print >> sys.stderr,"Error code "+str(e)


