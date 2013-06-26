#!/usr/bin/python

import reatlas_client
import netutils

atlas = reatlas_client.REatlas("localhost",65535);

atlas.connect();
atlas.build_functions();
#print(atlas.login(username="anders",password="1234"));
#print(atlas._get_available_methods());
#print(atlas._select_current_file(filename="test"))

atlas._socket.sendall(reatlas_client.BIN_REQUEST + netutils.htonll(0));

packtype = atlas._socket.recv(1);
l = netutils.ntohll(atlas._socket.recv(8));

print("Type: " + str(netutils.ntohb(packtype)) + " (" + packtype + ")");
print("Length: " + str(l));
print(atlas._socket.recv(l));



atlas.disconnect();

