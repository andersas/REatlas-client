#!/usr/bin/python

from __future__ import print_function
import reatlas_client
import argparse
import sys,os
import tempfile
import numpy
import datetime


choices = [".npy",".csv",".mat",".shp"];

def open_layout_as_npy(filename,shape):
     if (len(os.path.basename(filename)) < 4):
          print("File must end in .npy, .mat, .csv or shp.");
          exit(1);
     ending = filename[-4:];
     if (ending not in choices):
          print("Filename must end in one of " + str(choices) + ".");
          exit(1);

     if (ending == ".npy"):
          f = open(filename,"rb");
          layout=numpy.load(f);
          f.seek(0);
          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);

     if (ending == ".csv"):
          layout = numpy.loadtxt(filename,delimiter=",");
          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);

          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);
          return f;

     if (ending == ".mat"):
          try:
               import scipy.io;
          except ImportError:
               print("scipy must be installed in order to read matlab files.",file=sys.stderr);
               exit(1);

          matlayout = scipy.io.loadmat(filename);
          n_useful_keys = 0;
          thekey = None
          for key in matlayout.keys():
               if not key.startswith("__"):
                    n_useful_keys += 1;
                    thekey = key;
                    print("Found array: " + key + ".");
          if (n_useful_keys == 0):
               print("No arrays found in matlab file. Quitting.\n",file=sys.stderr);
               exit(1);
          if (n_useful_keys > 1):
               print("More than one array in " + filename + ". Too ambiguous.",file=sys.stderr);
               exit(1)
          print("Using layout " + key + " from " + filename + ".");

          layout = matlayout[thekey];
          if (len(layout.shape) == 2 and len(shape) == 1):
               if (layout.shape[0] == 1 or layout.shape[1] == 1):
                    layout = layout.flatten();

          if (layout.shape != shape):
               print("Arrays must have the shape " + str(shape) +". Supplied array " + filename + " has shape " + str(layout.shape) + ".",file=sys.stderr);
               exit(1);
     
          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);
          return f;

     if (ending == ".shp"):
          try:
               import shapefile
          except ImportError:
               print("Shapefile (pyshp) must be installed to save to shapefiles.",file=sys.stderr);
               exit(1);

          sf = shapefile.Reader(filename);

          required_fields = ["IDX1", "IDX2", "CAPACITY"];
          idxes = dict();
          fields = sf.fields;
         
          for i in range(len(fields)):
               #print("Field " + str(i) + ": " + str(fields[i][0]));
               if fields[i][0] in required_fields:
                    required_fields.pop(required_fields.index(fields[i][0]));
                    ## DeletionFlag has record 0 and is omitted (therefore -1)
                    idxes[fields[i][0]] = i - 1;
          if (len(required_fields) != 0):
               print("Required records fields missing: " + str(required_fields) + ".",file=sys.stderr);
               exit(1);

          records = sf.records();
          
          layout = numpy.zeros(shape);
          for rec in records:
               i,j = rec[idxes["IDX1"]], rec[idxes["IDX2"]];
               if (len(shape) == 1):
                    if (i != 0 or j < 0 or j >= shape[0]):
                         print("Point outside cutout: IDX1 = " + str(i) + ", IDX2 = "+  str(j) + ".",file=sys.stderr);
                         exit(1);
                    layout[j] = rec[idxes["CAPACITY"]];
               else:
                    if (i < 0 or i >= shape[0] or j < 0 or j >= shape[1]):
                         print("Point outside cutout: IDX1 = " + str(i) + ", IDX2 = " + str(j) + ".",file=sys.stderr);
                         print(idxes["IDX1"],idxes["IDX2"],rec[idxes["IDX1"]], rec[idxes["IDX2"]])
                         exit(1);
                    layout[rec[idxes["IDX1"]],rec[idxes["IDX2"]]] = rec[idxes["CAPACITY"]];

          f = tempfile.TemporaryFile();
          numpy.save(f,layout);
          f.seek(0);

          return f;
              
     raise Exception("Unimplemented file type "+ ending + " !");


