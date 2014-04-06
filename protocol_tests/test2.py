#!/usr/bin/python

import reatlas_client

atlas = reatlas_client.REatlas("localhost",65535);

atlas.connect();
atlas.build_functions();
print(atlas.login(username="user1",password="1234"));
print(atlas.get_available_methods());
print(atlas.secret());
print(atlas._call_atlas("handle_binary_request",dict()));
atlas.disconnect();

