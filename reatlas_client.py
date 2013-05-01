#!/usr/bin/python2

from __future__ import print_function
import socket
import json
import argparse
import struct
import time
import sys
import netutils


JSON_MSG = netutils.htonb(0);
SRV_MSG = netutils.htonb(1);
BIN_FILE = netutils.htonb(2);
KEEPALIVE = netutils.htonb(3);


## General error for the RE atlas
class REatlasError(Exception):
     pass;

# Connection specific error with the atlas.
# When this is raised, the connection is always closed afterwards.
class ConnectionError(Exception):
     pass;


class REatlas(object):
     version = 1; # Protocol version, not client version.

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
          s.request_count = 0;
          s.is_connected = False;

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
          s.is_connected = False;

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
          if (not s.is_connected):
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
          

     def _get_json_reply(s):
          """ Attempt to receive a JSON-RPC reply string from the server. 
          If the next message is not a JSON-RPC reply, throw an exception
          and close the connection. Skips keepalive messages. """

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
          
          if (msgtype != JSON_MSG): # Catch all 
               s.disconnect();
               msgtype_int = netutils.ntohb(msgtype);
               raise ConnectionError("Got unexpected reply message (" + str(msgtype_int) + "), expected JSON_MSG.");

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
                    " with message \"" + message + "\"";
               except KeyError:
                    ExceptionMessage = "Received unspecified error.";
               raise REatlasError(ExceptionMessage);

          if (return_object["id"] != s.request_count):
               s.disconnect();
               raise ConnectionError("Response ID did not match request ID.");

          return return_object;



     def _call_atlas(s,method,params=None):
          """ Do a remote procedure call to the atlas.
          
          _call_atlas(method,params=dict())
          
          method: name of the RPC method.
          params: dictionary of arguments. """
          msg = s._json_rpc_request(method,params,s.request_count);
          s._send_string(msg);

          json_reply = s._get_json_reply();

          response = s._parse_json_rpc_reply(json_reply);
          
          s.request_count += 1;

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
          func_names = s._call_atlas("get_available_methods");
          func_docstrings = s._call_atlas("get_method_docstrings");

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
          if (msg != "REatlas" + struct.pack('!l',1)):
               s.disconnect();
               raise ConnectionError("Bad handshake from server or unsupported server version.");
          try:
               s._socket.sendall(struct.pack('!H',0xAA55)); # Send our handshake to the server
          except socket.error:
               s.disconnect();
               raise ConnectionError("Could not connect to RE atlas server.");

          s.is_connected = True;
          s.request_count = 0;

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




