#!/usr/bin/python

import numpy
import reatlas_client
import datetime
import matplotlib.pyplot as plt


### Solution to the exercices

server_name = "pepsimax.imf.au.dk"
username = "anders"
password = "Chung9Quah"


# Exercice 1:


print("##################");
print("### Exercice 1 ###");
print("##################");
print("");

atlas = reatlas_client.REatlas(server_name);

atlas.connect_and_login(username=username,password=password)

# Use the echo function:

print(atlas.echo(message="Hello, world"))


# Get an example error message
# Errors either REatlasError or ConnectionError exceptions.
# The connection is closed whenever a ConnectionError exception is generated.

try:
     atlas.generate_error();
     print("No error");
except reatlas_client.REatlasError as e:
     print("Got error: " + str(e));

# Get a list of the cutouts that are available on the server,
# and see how much space Europe and DK takes up:

cutout_list = atlas.list_cutouts(all_users=True)

print(cutout_list);

for cutout in cutout_list:
     if cutout[0].endswith("Europe"):
          print("Europe: " + str(cutout[1]/1024.0**3) + " GB");
     elif cutout[0].endswith("Denmark"):
          print("Denmark: " + str(cutout[1]/1024.0**3) + " GB");

# Download metadata

atlas.prepare_cutout_metadata(cutoutname="Denmark",username="auesg");
atlas.prepare_cutout_metadata(cutoutname="Europe",username="auesg");
atlas.download_file(filename="meta_Denmark.npz");
atlas.download_file(filename="meta_Europe.npz");
atlas.delete_file(filename="meta_Denmark.npz");
atlas.delete_file(filename="meta_Europe.npz");

# Find out the number of points in a cutout

Europe = numpy.load("meta_Europe.npz");
Denmark = numpy.load("meta_Denmark.npz");

Europe_points = numpy.array(Europe["latitudes"].shape).cumprod()[-1];
Denmark_points = numpy.array(Denmark["latitudes"].shape).cumprod()[-1];

print("There are " + str(Europe_points) + " points in Europe");
print("There are " + str(Denmark_points) + " points in Denmark");


# Submit a dummy job

#atlas.submit_dummy_job()

# Submit a dummy job without being notified by mail when it's done:

atlas.notify_by_mail(notify=False)
#dummy_job_id = atlas.submit_dummy_job();

# Reset notification setting

atlas.notify_by_mail(notify=True);

# Wait for the last dummy job to finish

print("Waiting for dummy_job")
#atlas.wait_for_job(job_id=dummy_job_id);
print("Job is done");





# Exercice 2:

print("");
print("##################");
print("### Exercice 2 ###");
print("##################");
print("");



# First figure out where 56.9 degrees latitude, 7.5 degrees longitude is
# in the Denmark cutout:


(i,j) = reatlas_client.translate_GPS_coordinates_to_array_indices(56.9,7.5,Denmark["latitudes"],Denmark["longitudes"]);

print("56.9,7.5 degrees has index " + str((i,j)) +".");

# Prepare for wind conversion:

# Make a capacity layout with 0 everywhere but in (i,j)
layout = numpy.zeros(Denmark["latitudes"].shape);
layout[i,j] = 1.0;

# Upload it

numpy.save("layout.npy",layout);
atlas.upload_file(filename="layout.npy");

# Load the power curve
Vestas90 = reatlas_client.turbineconf_to_powercurve_object("TurbineConfig/Vestas_V90_3MW.cfg");

# Start a wind conversion on Denmark:

atlas.select_cutout(cutoutname="Denmark",username="auesg");

wind_job = atlas.convert_and_aggregate_wind(result_name="myresult",onshorepowercurve=Vestas90,offshorepowercurve=Vestas90,capacitylayouts=["layout.npy"]);

# Find the temporal index for January 13, 1992 at 05.00 UTC

idx = numpy.where(Denmark["dates"] == datetime.datetime(1992,1,13,5,0))[0][0];

print("January 13, 1992 at 05.00 UTC has index " + str(idx) + ".");

print("Waiting for the wind conversion to finish...");
atlas.wait_for_job(job_id=wind_job);

print("Downloading result")
atlas.download_file("myresult.npy");

print("A Vestas V90 3MW placed in 56.9,7.5 degrees produced " + str(numpy.load("myresult.npy")[idx][0]) + " MW on January 13, 1992, 05.00 UTC, ");

if (Denmark["onshoremap"][i,j]):
     print("This is onshore");
else:
     print("This is offshore");

print("The depth here is " + str(-Denmark["heights"][i,j]) + " meters.");


# Get normalized timeseries for onshore Denmark

numpy.save("onshorelayout.npy", Denmark["onshoremap"]);
atlas.upload_file(filename="onshorelayout.npy");

atlas.select_cutout(cutoutname="Denmark",username="auesg");
wind_job = atlas.convert_and_aggregate_wind(result_name="onshoreresult",onshorepowercurve=Vestas90,offshorepowercurve=Vestas90,capacitylayouts=["onshorelayout.npy"]);

print("Waiting for onshore wind conversion");
atlas.wait_for_job(job_id=wind_job);

atlas.download_file(filename="onshoreresult.npy")

timeseries = numpy.load("onshoreresult.npy");

plt.ion()
plt.xlabel("Date");
plt.ylabel("Production");
plt.title("Uniform onshore DK");
plt.plot(Denmark["dates"],timeseries[:,0]);


# Now get both timeseries in one conversion:
wind_job = atlas.convert_and_aggregate_wind(result_name="combinedresult",onshorepowercurve=Vestas90,offshorepowercurve=Vestas90,capacitylayouts=["layout.npy","onshorelayout.npy"]);

print("Waiting for combined conversion..");
atlas.wait_for_job(job_id=wind_job);

atlas.download_file(filename="combinedresult.npy")
timeseries = numpy.load("combinedresult.npy");

single_point_timeseries = timeseries[:,0];
uniform_onshore_timeseries = timeseries[:,1];

plt.figure()
plt.xlabel("Date");
plt.ylabel("Production");
plt.plot(Denmark["dates"],single_point_timeseries/numpy.max(single_point_timeseries),label="Single point");
plt.plot(Denmark["dates"],uniform_onshore_timeseries/numpy.max(uniform_onshore_timeseries),label="Uniform onshore");
plt.legend();


# Clean up:
atlas.delete_file(filename="combinedresult.npy");
atlas.delete_file(filename="onshoreresult.npy");
atlas.delete_file(filename="myresult.npy");
atlas.delete_file(filename="layout.npy");


# Exercice 3:

print("");
print("##################");
print("### Exercice 3 ###");
print("##################");
print("");


Scheuten = reatlas_client.solarpanelconf_to_solar_panel_config_object("SolarPanelData/Scheuten215IG.cfg");

atlas.add_constant_orientation_function(slope=45,azimuth=90,weight=0.33);
atlas.add_constant_orientation_function(slope=45,azimuth=-90,weight=0.33);
atlas.add_constant_orientation_function(slope=45,azimuth=0,weight=0.34);

atlas.select_cutout(cutoutname="Denmark",username="auesg");

sun_conversion = atlas.convert_and_aggregate_pv(result_name="PV_dist",solar_panel_config=Scheuten,capacitylayouts=["onshorelayout.npy"]);

print("Waiting for PV conversion");
atlas.wait_for_job(job_id=sun_conversion);

atlas.download_file(filename="PV_dist.npy");
atlas.delete_file(filename="PV_dist.npy");

atlas.add_constant_orientation_function(slope=32,azimuth=0,weight=1.0);
first_job = atlas.convert_and_aggregate_pv(result_name="PV_const",solar_panel_config=Scheuten,capacitylayouts=["onshorelayout.npy"]);

atlas.add_full_tracking_orientation_function(weight=1.0);
last_job = atlas.convert_and_aggregate_pv(result_name="PV_track",solar_panel_config=Scheuten,capacitylayouts=["onshorelayout.npy"]);

print("Waiting for PV conversions");

atlas.wait_for_job(job_id=first_job);
atlas.download_file(filename="PV_const.npy");
atlas.delete_file(filename="PV_const.npy");

atlas.wait_for_job(job_id=last_job);
atlas.download_file(filename="PV_track.npy");
atlas.delete_file(filename="PV_track.npy");

plt.figure()
plt.xlabel("Date");
plt.ylabel("Production");
plt.plot(Denmark["dates"],numpy.load("PV_dist.npy")[:,0],label="Distribution");
plt.plot(Denmark["dates"],numpy.load("PV_const.npy")[:,0],label="Constant");
plt.plot(Denmark["dates"],numpy.load("PV_track.npy")[:,0],label="Tracking");
plt.legend();


# Cleanup
atlas.delete_file(filename="onshorelayout.npy");
atlas.disconnect();

print("Done!");

plt.ioff()
plt.show()
