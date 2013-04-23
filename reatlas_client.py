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
     version = 1;
     def __init__(s,host,port):
          s.hostname = host;
          s.host = socket.gethostbyname(host);
          s.port = port;
          s.socket = None;
          s.request_count = 0;

     def setup_socket(s):
          s.disconnect(); # Close any open connection
          s.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);

     def disconnect(s):
          if (s.socket):
               try:
                    s.shutdown(socket.SHUT_RDWR);
               except:
                    pass;
               s.socket.close();
          s.connected = False;

     def json_rpc_request(s,method,params,request_id):
          msg = dict();
          msg["jsonrpc"] = "2.0";
          msg["method"] = method;
          if (params):
               msg["params"] = params;
          msg["id"] = request_id;

          json_string = json.dumps(msg);
          request_string = JSON_MSG + netutils.htonll(len(json_string)) + json_string;    
          return request_string;


     def send_string(s,string):
          if (not s.connected):
               raise REatlasError("Not connected to RE atlas server.");
          try:
               s.socket.sendall(string);
          except socket.error:
               s.disconnect();
               raise ConnectionError("Error sending request to server.");

     def get_next_header(s):
          (header, closed) = netutils.readall(s.socket,9);
          if (closed):
               s.disconnect();
               raise ConnectionError("Connection closed when reading message.");
          msgtype, msglen = struct.unpack("!BQ", header);
          msgtype = netutils.htonb(msgtype);
          
          return (msgtype, msglen);
          

     def get_json_reply(s):
          (msgtype, msglen) = s.get_next_header();
          while (msgtype == KEEPALIVE): # Get any keepalive packets out
               if (msglen != 0):
                    s.disconnect();
                    raise ConnectionError("Received invalid keepalive packet.");
               (msgtype, msglen) = s.get_next_header();
          
          if (msgtype == SRV_MSG):
               msg, closed = netutils.readall(s.socket,msglen);
               s.disconnect();
               raise ConnectionError("Connection error, server says " + msg);
          
          if (msgtype != JSON_MSG):
               s.disconnect();
               msgtype_int = netutils.ntohb(msgtype);
               raise ConnectionError("Got unexpected reply message (" + str(msgtype_int) + "), expected JSON_MSG.");

          (json_msg, closed) = netutils.readall(s.socket,msglen);
          if (closed):
               s.disconnect();
               raise ConnectionError("Connection closed before entire JSON reply was received.");
          
          return json_msg;

     def call_atlas(s,method,params):

          msg = s.json_rpc_request(method,params,s.request_count);
          s.send_string(msg);

          json_reply = s.get_json_reply();

          response = s.parse_json_rpc_reply(json_reply);
          
          s.request_count += 1;

          return response["result"];

     def notify_atlas(s,method,params):
          msg = s.json_rpc_request(method,params,None);
          s.send_string(msg);



     def parse_json_rpc_reply(s,json_reply_string):

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


     
     def connect(s):
          if (not s.socket):
               s.setup_socket();
          s.socket.connect((s.host,s.port));
          # Shake hands with server
          msg, closed = netutils.readall(s.socket,11);
          if (closed):
               raise ConnectionError("Could not connect to RE atlas server.");
          if (msg != "REatlas" + struct.pack('!l',1)):
               s.disconnect();
               raise ConnectionError("Bad handshake from server or unsupported server version.");
          try:
               s.socket.sendall(struct.pack('!H',0xAA55)); # Send our handshake to the server
          except socket.error:
               s.disconnect();
               raise ConnectionError("Could not connect to RE atlas server.");

          s.connected = True;
          s.request_count = 0;

     def login(s,username,password):
          """
          Log in to the server with supplied credentials. Returns True
          on success, and False on invalid credentials.

          It is a good idea to login immediately after a connection is made,
          as the server times out very quickly if no user is logged in.
          """
          user = dict();
          user["username"] = username;
          user["password"] = password;

          return s.call_atlas("login",user);




