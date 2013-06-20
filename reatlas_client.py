#!/usr/bin/python2

from __future__ import print_function
import socket
import json
import argparse
import struct
import time
import os,sys
import netutils


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


class REatlas(object):
     _protocol_version = 2; # Protocol version, not client version.

     def __init__(s,host,port):
          """ Build a new REatlas object.
          
          Arguments:
               host: hostname or ip address of RE atlas server.
               port: TCP port used by server.
               
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
               raise ConnectionError("Could not connect to RE atlas server.");
          if (msg != "REatlas" + struct.pack('!l',s._protocol_version)):
               s.disconnect();
               raise ConnectionError("Bad handshake from server or unsupported server version.");
          try:
               s._socket.sendall(struct.pack('!H',0xAA55)); # Send our handshake to the server
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


     def download_file(s,fp, filename,username=""):
          """ download_file(fp,filename,username=""):

          Downloads a file from the server by name.

          Arguments:
               fp: file-like object, filename or None.
               The downloaded file will be written to this file.
               If None, the entire file contents will be returned.

               filename: Name of file on server.

               username: If given, download this users file instead
                    of your own.  """

          if (hasattr(fp,"write")):
               return s._download_to_file(fp,filename,username);
          elif (type(fp) is str):
               with open(fp,"w") as f:
                    return s._download_to_file(f,filename,username);
          else:
              return s._download_to_string(filename,username);

     def upload_from_file(s,fp,tofile,username=""):

          if (hasattr(fp,"read")):
               return s._upload_from_file(fp,tofile,username);
          else:
               with open(fp,"r") as f:
                    return s._upload_from_file(f,tofile,username);


     def upload_from_string(s,string,tofile,username=""):

          size = len(string);

          s._select_current_file(filename=tofile,username=username);
          header = BIN_FILE + netutils.htonll(size);
          s._send_string(header);
          s._send_string(string);

          s._wait_for_bin_ack(); # The server sends an acknowledgment packet
                                 # after having saved the file.

     def _upload_from_file(s,fp,tofile,username):
          
          filesize = os.path.getsize(fp.name);
          
          fp.seek(0);

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


     def _request_file(s,filename,username):

          # Select current file on server:
          s._select_current_file(filename=filename,username=username);

          # Send a BIN_REQ packet to request a file transfer:
  
          packet = BIN_REQUEST + netutils.htonll(0);
          s._send_string(packet);
     

     def _download_to_string(s,filename,username):
          s._request_file(filename,username);
          (msgtype,msglen) = s._get_next_nonkeepalive_packet_of_type(BIN_FILE);

          buf,closed = netutils.readall(s._socket,msglen);

          if (len(buf) != msglen):
               s.disconnect();
               raise ConnectionError("Server closed connection before file was transferred.");

          return buf;

     def _download_to_file(s,fp,filename,username):

          s._request_file(filename,username);

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
               

