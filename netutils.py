#!/usr/bin/python2
import socket
import struct


# the *to*[sl] (* = h for host, n for network) functions pack or unpack
# a network byte order (i.e. big endian) short (16 bit) or long (32 bit)
# or long long (64 bit) integer.
def htonb(number):
     return struct.pack('!B',number);
def htons(number):
     return struct.pack('!H',number);
def htonl(number):
     return struct.pack('!L',number);
def htonll(number):
     return struct.pack('!Q',number);
def ntohb(string):
     return struct.unpack('!B',string)[0];
def ntohs(string):
     return struct.unpack('!H',string)[0];
def ntohl(string):
     return struct.unpack('!L',string)[0];
def ntohll(string):
     return struct.unpack('!Q',string)[0];


# Read length bytes from a socket,
# return the read bytes and True if the socket closed while reading.
def readall(sock,length):
     closed = False;
     read = 0;
     msg = "";
     while (read != length):
          try:
               buf = sock.recv(length - read);
          except socket.error as e:
               # An error probably means the connection is closed.
               # However, if it's a timeout, this is not the case.
               if (type(e) == socket.timeout):
                    raise e;
               closed = True;
               break;
          if (buf == ''):
               closed = True;
               break;
          msg += buf;
          read += len(buf);
     return (msg,closed);
          

