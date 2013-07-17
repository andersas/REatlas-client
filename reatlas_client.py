#!/usr/bin/python2

from __future__ import print_function
import socket
import json
import argparse
import struct
import time
import os,sys
import netutils
import ConfigParser
import numpy


JSON_MSG = netutils.htonb(74); # Ascii 'J'
SRV_MSG = netutils.htonb(83); # Ascii 'S'
BIN_REQUEST = netutils.htonb(66); # Ascii 'B'
BIN_FILE = netutils.htonb(70); # Ascii 'F'
BIN_ACK = netutils.htonb(65); # Ascii 'A'
KEEPALIVE = netutils.htonb(75); # Ascii 'K'


## General error for the RE atlas
class REatlasError(Exception):
     pass;

# Connection specific error with the atlas.
# When this is raised, the connection is always closed afterwards.
class ConnectionError(Exception):
     pass;


def turbineconf_to_powercurve_object(turbineconfigfile):
     """ Load a turbine config file for use in REatlas conversion.
     
     Arguments:
          turbineconfigfile: Name of the file to load.

     Returns an object that can be used in the on/offshorepowercurve argument
     for wind conversion.  """

     if (not os.path.exists(turbineconfigfile)):
          raise RuntimeError("File does not exist.");

     config = dict();
     parser = ConfigParser.ConfigParser();
     parser.read(turbineconfigfile);
     config["HUB_HEIGHT"] = parser.getfloat("windcfg","HUB_HEIGHT");
     config["V"] = [float(speed) for speed in parser.get("windcfg", "V").split(',')]
     config["POW"] = [float(power) for power in parser.get("windcfg", "POW").split(',')]

     if (len(config["V"]) != len(config["POW"])):
          raise ValueError("V and POW should have equal length.");
     if (len(config["V"]) < 3):
          raise ValueError("You should have at least 2 points on your power curve.");
     return config;
 
def solarpanelconf_to_solar_panel_config_object(panelconfigfile):
     """ Load a solar panel config file for use in REatlas PV conversion
     
     Arguments:
          panelconfigfile: Name of file to load
          
     Returns an object that can be used as the solar_panel_config argument
     in REatlas PV conversions.  """

     if (not os.path.exists(panelconfigfile)):
          raise RuntimeError("File does not exist.");

     config = dict();
     parser = ConfigParser.ConfigParser();
     parser.read(panelconfigfile);
     
     keys = ["A","B","C","D","NOCT","Tstd","Tamb","Intc","ta","threshold","inverter_efficiency"];

     for key in keys:
          config[key] = parser.getfloat("pvcfg",key);

     return config;

def translate_GPS_coordinates_to_array_indices(latitude,longitude,latitudes,longitudes):
     """ Translate a GPS coordinate to an index i,j,
     i.e. find the i,j that makes latitudes[i][j],longitudes[i][j]
     closest to latitude,longitude.

     Arguments:
          latitude, longitude: The GPS coordinate
          latitudes,longitudes: Two 2-D arrays of latitudes and longitudes.

     Returns the tuple (i,j).
     """

     distances = numpy.sqrt((latitudes - latitude)**2+(longitudes-longitude)**2);
     minimum = numpy.argmin(distances);

     arg = numpy.unravel_index(minimum,dims=distances.shape);

     ret = []

     for i in arg:
          ret.append(i);
     

     return tuple(ret);

class REatlas(object):
     _protocol_version = 2; # Protocol version, not client version.

     def __init__(s,host,port=65535):
          """ Build a new REatlas object.
          
          Arguments:
               host: hostname or ip address of RE atlas server.
               port=65535: TCP port used by server.
               
          To make the server functions available, call the build_functions() method.
          You can also call connect_and_login method if you're e.g. using IPython. """
          s.hostname = host;
          s.host = socket.gethostbyname(host);
          s.port = port;
          s._socket = None;
          s._request_count = 0;
          s._is_connected = False;

     def _setup_socket(s):
          s.disconnect(); # Close any open connection
          s._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);

     def disconnect(s):
          if (s._socket):
               try:
                    s.shutdown(socket.SHUT_RDWR);
               except:
                    pass;
               s._socket.close();
          s._is_connected = False;

     def _json_rpc_request(s,method,params,request_id):
          """ Factory function for JSON-RPC 2.0 rpc requests. 
          Returns a string that can be directly sent over the network
          connection to the RE atlas. """
          msg = dict();
          msg["jsonrpc"] = "2.0";
          msg["method"] = method;
          if (params):
               msg["params"] = params;
          msg["id"] = request_id;

          json_string = json.dumps(msg);
          # Prepend the json string with a header
          request_string = JSON_MSG + netutils.htonll(len(json_string)) + json_string;    
          return request_string;


     def _send_string(s,string):
          """ Send the string supplied as argument to the RE atlas server. """
          if (not s._is_connected):
               raise ConnectionError("Not connected to RE atlas server.");
          try:
               s._socket.sendall(string);
          except socket.error:
               s.disconnect();
               raise ConnectionError("Error sending request to server.");

     def _get_next_header(s):
          """ Read the header of the next message from the server.
          Assumes that the next data sent from the server is a completely
          new message. """
          (header, closed) = netutils.readall(s._socket,9);
          if (closed):
               s.disconnect();
               if (len(header) > 0):
                    raise ConnectionError("Connection closed when reading message.");
               else:
                    raise ConnectionError("Trying to read from closed connection.");
          msgtype, msglen = struct.unpack("!BQ", header);
          msgtype = netutils.htonb(msgtype);
          
          return (msgtype, msglen);
         
     def _get_next_nonkeepalive_packet_of_type(s,thetype):
          """ Call this instead of get next header to skip
          keepalives and to catch server errors. """

          (msgtype, msglen) = s._get_next_header();
          while (msgtype == KEEPALIVE): # Get any keepalive packets out
               if (msglen != 0):
                    s.disconnect();
                    raise ConnectionError("Received invalid keepalive packet.");
               (msgtype, msglen) = s._get_next_header();
          
          if (msgtype == SRV_MSG):
               msg, closed = netutils.readall(s._socket,msglen);
               s.disconnect();
               raise ConnectionError(msg);

          if (msgtype != thetype): # Catch all 
               s.disconnect();
               msgtype_int = netutils.ntohb(msgtype);
               expected_int = netutils.ntohb(thetype);
               raise ConnectionError("Got unexpected reply message (" + str(msgtype_int) + "), expected " + str(expected_int) + ".");

          return (msgtype,msglen);


     def _get_json_reply(s):
          """ Attempt to receive a JSON-RPC reply string from the server. 
          If the next message is not a JSON-RPC reply, throw an exception
          and close the connection. Skips keepalive messages. """

          (msgtype,msglen) = s._get_next_nonkeepalive_packet_of_type(JSON_MSG);

          (json_msg, closed) = netutils.readall(s._socket,msglen);
          if (closed):
               s.disconnect();
               raise ConnectionError("Connection closed before entire JSON reply was received.");
          
          return json_msg;

     def _parse_json_rpc_reply(s,json_reply_string):
          """ Translate the given json reply string into a reply object.
          Throws an REatlasError exception if the reply is an error message. """

          try:
               return_object = json.loads(json_reply_string);
          except ValueError:
               s.disconnect();
               raise ConnectionError("Received invalid JSON reply.");
          if (return_object.has_key("error")):
               try:
                    code = return_object["error"]["code"];
                    message = return_object["error"]["message"];
                    ExceptionMessage = "Received error code " + str(code) + \
                    " with message \"" + str(message.encode('utf-8')) + "\"";
               except KeyError:
                    ExceptionMessage = "Received unspecified error.";
               raise REatlasError(ExceptionMessage);

          if (return_object["id"] != s._request_count):
               s.disconnect();
               raise ConnectionError("Response ID did not match request ID.");

          return return_object;



     def _call_atlas(s,method,params=None):
          """ Do a remote procedure call to the atlas.
          
          _call_atlas(method,params=dict())
          
          method: name of the RPC method.
          params: dictionary of arguments. """
          msg = s._json_rpc_request(method,params,s._request_count);
          s._send_string(msg);

          json_reply = s._get_json_reply();

          response = s._parse_json_rpc_reply(json_reply);
          
          s._request_count += 1;

          return response["result"];

     def _notify_atlas(s,method,params=None):
          """ Do a remote procedure call to the atlas without expecting a return value.
          
          _notify_atlas(method,params=dict())
          
          method: name of the RPC method.
          params: dictionary of arguments. 
          
          Note: Does not return anything. Don't invoke remote methods
          that return anything. """

          msg = s._json_rpc_request(method,params,None);
          s._send_string(msg);

     def build_functions(s):
          """ Call this function to make the server defined RPC functions
          available as local class methods. Requires a connection to be set up first. """
          func_names = s._call_atlas("_get_available_methods");
          func_docstrings = s._call_atlas("_get_method_docstrings");

          # Constants in lambda functions are a bit weird.
          # They are only references to the named variable
          # within its curent scope. So to get a constant that's the same
          # everywhere, we set up a one-use-only scope with this function:
          def make_RPC_function(method):
               func = lambda **kwargs: s._call_atlas(method,kwargs);
               func.__doc__ = func_docstrings[name];
               return func;

          # And expand our object with the functions available
          # from the server:
          for name in func_names:
               setattr(s,name,make_RPC_function(name));



     def connect(s):
          """ Establish a connection with the RE atlas. """
          s._setup_socket();
          s._socket.connect((s.host,s.port));
          # Shake hands with server
          msg, closed = netutils.readall(s._socket,11);
          if (closed):
               raise ConnectionError("Could not connect to RE atlas server. ");
          if (msg != "REatlas" + struct.pack('!l',s._protocol_version)):
               if (msg[0] == SRV_MSG):
                    lenrest = netutils.ntohll(msg[1:9]);
                    msg2,closed = netutils.readall(s._socket,lenrest-2);
                    msg = msg[9:] + msg2
                    s.disconnect();
                    raise ConnectionError("Received error message from server: " + msg);
               else:
                    s.disconnect();
                    raise ConnectionError("Bad handshake from server or unsupported server version.");
          try:
               s._socket.sendall(netutils.htonl(428344082)); # Send our handshake to the server
          except socket.error:
               s.disconnect();
               raise ConnectionError("Could not connect to RE atlas server.");

          s._is_connected = True;
          s._request_count = 0;

     def connect_and_login(s,**kwargs):
          """
          New connections time out very fast. If you're using the REatlas
          object from interactive python, use this method to 
          connect and login instead of doing it in separate calls.
          The connection times out before you can type in your user name
          and password.

          Keyword arguments:
               username
               password
          as strings.

          Note: This function also calls build_functions in order to have the
          login method available.
          """

          s.connect();
          s.build_functions(); # s.login should get defined here
          return s.login(**kwargs);


     def add_pv_orientations_by_config_file(s,filename):
          """ add_pv_orientations_by_config_file(filename):
               
               Given a orientation configuration file, add the
               orientations within it to the current atlas session. """
          parser = ConfigParser.ConfigParser();
          parser.read(filename);
          
          if (parser.has_section("constant")):
               slopes = parser.get("constant","slope").split(",");
               azimuths = parser.get("constant","azimuth").split(",");
               weights = parser.get("constant","weight").split(",");
     
               if (len(slopes)!=len(azimuths) or len(azimuths)!=len(weights)):
                   raise ValueError("Malformed config file " + filename);
               slopes = [float(slope) for slope in slopes];
               azimuths = [float(azimuth) for azimuth in azimuths];
               weights = [float(weight) for weight in weights];
               
               for i in range(len(weights)):
                    s.add_constant_orientation_function(slope=slopes[i],azimuth=azimuths[i],weight=weights[i]);
          
          if (parser.has_section("vertical_tracking")):
               azimuths = parser.get("vertical_tracking","azimuth").split(",");
               weights = parser.get("vertical_tracking","weight").split(",");
               if (len(azimuths) != len(weights)):
                   raise ValueError("Malformed config file " + filename);
               azimuths = [float(azimuth) for azimuth in azimuths];
               weights = [float(weight) for weight in weights];
               for i in range(len(weights)):
                    s.add_vertical_axis_tracking_orientation_function(azimuth=azimuths[i],weight=weights[i]);
 
          if (parser.has_section("horizontal_tracking")):
               slopes = parser.get("horizontal_tracking","slope").split(",");
               weights = parser.get("horizontal_tracking","weight").split(",");
               if (len(slopes) != len(weights)):
                   raise ValueError("Malformed config file " + filename);
               slopes = [float(slope) for slope in slopes];
               weights = [float(weight) for weight in weights];
               for i in range(len(weights)):
                    s.add_horizontal_axis_tracking_orientation_function(slope=slopes[i],weight=weights[i]);

          if (parser.has_section("full_tracking")):
               weights = parser.get("full_tracking","weight").split(",");
               weights = [float(weight) for weight in weights];
               for i in range(len(weights)):
                    s.add_full_tracking_orientation_function(weight=weights[i]);


     def download_file(s,filename,username=""):
          """ download_file(filename,username="")
          
          Downloads a file from the server.
          
          Arguments:
               filename: Name of file to download.
               username: If given, download this users file instead
                    of your own.  """

          s.download_file_and_rename(filename,filename,username);

     def download_file_and_rename(s,local_file,remote_file,username=""):
          """ download_file_and_rename(local_file,remote_file,username=""):

          Download a file from the server by name.

          Arguments:
               local_file: file-like object, filename or None.
               The downloaded file will be written to this file.
               If None, the entire file contents will be returned as a string.

               remote_file: Name of file on server.

               username: If given, download this users file instead
                    of your own.  """

          if (hasattr(local_file,"write")):
               return s._download_to_file(local_file,remote_file,username);
          elif (type(local_file) is str):
               try:
                    with open(local_file,"wb") as f:
                         return s._download_to_file(f,remote_file,username);
               except:
                    try:
                         os.unlink(local_file);
                    except:
                         pass;
                    raise;

          else:
              return s._download_to_string(remote_file,username);

     def upload_file(s,filename,username=""):
          """ upload_file(filename,username="")
          
          Upload a file to the REatlas server.

          Arguments:
               filename: Name of file to upload.
               username: If given, upload to this users folder instead of your own.  """
          s.upload_from_file_and_rename(filename,filename,username);
     
     def upload_from_file_and_rename(s,local_file,remote_file,username=""):
          """ upload_from_file(local_file,remote_file,username=""):

          Upload a file to the REatlas server.

          Arguments:
               local_file: file handle or filename (as a string) of the file to upload.
               remote_file: Name to give the file on the server.
               username: If given, upload to this users folder instead of your own.
          """

          if (hasattr(local_file,"read")):
               return s._upload_from_file(local_file,remote_file,username);
          else:
               with open(local_file,"rb") as f:
                    return s._upload_from_file(f,remote_file,username);


     def upload_from_string(s,string,remote_file,username=""):
          """ upload_from_string(string,remote_file,username=""):
    
          Upload a file from a string to the REatlas server.

          Arguments:
               string: Contents of the file as a string
               remote_file: Name to give the file on the server.
               username: If give, upload to this users folder instead of your own.
          """


          size = len(string);

          s._select_current_file(filename=tofile,username=username);
          header = BIN_FILE + netutils.htonll(size);
          s._send_string(header);
          s._send_string(string);

          s._wait_for_bin_ack(); # The server sends an acknowledgment packet
                                 # after having saved the file.

     def _upload_from_file(s,fp,tofile,username):
          
          #filesize = os.path.getsize(fp.name);
          #filesize = os.fstat(fp.fileno()).st_size;
          #fp.seek(0);
          
          curr_pos = fp.tell()
          fp.seek(0,2); # Seek to end of file
          end_pos = fp.tell();
          fp.seek(curr_pos);

          filesize = end_pos - curr_pos;

          # Select current file on server:
          s._select_current_file(filename=tofile,username=username);

          header = BIN_FILE + netutils.htonll(filesize);

          s._send_string(header);

          while (filesize > 0):
               buf = fp.read(min(filesize,16384));
               l = len(buf);
               filesize -= l;
               if (l > 0):
                    s._send_string(buf);
               else:
                    s.disconnect();
                    raise IOError("Could not read remaining " + str(filesize) + " bytes of " + fp.name + ".");

          s._wait_for_bin_ack(); # The server sends an acknowledgment packet
                                 # after having saved the file.
          
     def _wait_for_bin_ack(s):
          s._get_next_nonkeepalive_packet_of_type(BIN_ACK)


     def _request_file(s,filename,username,intent=""):

          # Select current file on server:
          s._select_current_file(filename=filename,username=username,intent=intent);

          # Send a BIN_REQ packet to request a file transfer:
  
          packet = BIN_REQUEST + netutils.htonll(0);
          s._send_string(packet);
     

     def _download_to_string(s,filename,username):
          s._request_file(filename,username,intent="download");
          (msgtype,msglen) = s._get_next_nonkeepalive_packet_of_type(BIN_FILE);

          buf,closed = netutils.readall(s._socket,msglen);

          if (len(buf) != msglen):
               s.disconnect();
               raise ConnectionError("Server closed connection before file was transferred.");

          return buf;

     def _download_to_file(s,fp,filename,username):

          s._request_file(filename,username,intent="download");

          (msgtype,msglen) = s._get_next_nonkeepalive_packet_of_type(BIN_FILE);

          while (msglen > 0):
               buf,closed = netutils.readall(s._socket, min(msglen,16384));
               l = len(buf);
               if (l > 0):
                    fp.write(buf);
               msglen -= l;
               if (closed and msglen > 0):
                    s.disconnect();
                    raise ConnectionError("Server closed connection before file was transferred.");
               
