#!/usr/bin/python

import reatlas_client

atlas = reatlas_client.REatlas("localhost",65535);

atlas.connect();
print(atlas.login("user1","1234"));
atlas.disconnect();

