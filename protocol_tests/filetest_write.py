#!/usr/bin/python

import reatlas_client
import netutils

atlas = reatlas_client.REatlas("localhost",65535);

atlas.connect();
atlas.build_functions();
print(atlas.login(username="anders",password="1234"));
print(atlas._get_available_methods());
print(atlas._select_current_file(filename="test"))

message = "HESTEHEST ! ! ! ! ! ! ! !"

atlas._socket.sendall(reatlas_client.BIN_FILE + netutils.htonll(len(message)));

atlas._socket.sendall(message);


packtype, closed = netutils.readall(atlas._socket,1);
l,closed = netutils.readall(atlas._socket,8);
l = netutils.ntohll(l);

#if (len(packtype) == 1 and len(l) == 8):
if True:
     print("Type: " + str(netutils.ntohb(packtype)) + " (" + packtype + ")");
     print("Length: " + str(l));
     if (l > 0):
          print(atlas._socket.recv(l));



atlas.disconnect();

