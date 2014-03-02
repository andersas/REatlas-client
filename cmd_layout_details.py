#! /usr/bin/python
from __future__ import print_function
import decimal
import json
import os
import sys

import numpy

cwd = os.path.dirname(__file__)
		
message={}
resultarray = {}
limitextentObj = {}

def datatype_defaults(obj):
    print(type(obj))
    if isinstance(obj, numpy.uint8):
        return int(obj)
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError
layoutFile=sys.argv[1]
print(json.dumps(numpy.load(layoutFile).tolist(), default=datatype_defaults))