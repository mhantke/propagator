#!/usr/bin/env python

# ----------------------------------------------------------------------------------------------------- 
# CONDOR 
# Simulator for diffractive single-particle imaging experiments with X-ray lasers
# http://xfel.icm.uu.se/condor/
# ----------------------------------------------------------------------------------------------------- 
# Copyright 2014 Max Hantke, Filipe R.N.C. Maia, Tomas Ekeberg
# Condor is distributed under the terms of the GNU General Public License
# ----------------------------------------------------------------------------------------------------- 
# General note:
#  All variables are in SI units by default. Exceptions explicit by variable name.
# ----------------------------------------------------------------------------------------------------- 

import condor as condor
import pylab,os,numpy,sys
from python_tools import gentools

condor.logger.setLevel("INFO")
import python_tools
python_tools.gentools.logger.setLevel("INFO")

pdir = os.path.abspath(os.path.dirname(__file__))+"/../"
odir = os.path.abspath(os.path.dirname(__file__))+"/example_out/"
os.system("mkdir -p %s" % odir)

numpy.random.seed(0)

if len(sys.argv) < 2:
    sample = "all"
else:
    sample = sys.argv[1]

if sample == "all":
    samples = ["icosahedron","sphere","spheroid","uniform_sphere","uniform_spheroid"]
else:
    samples = []
    for i in range(1,len(sys.argv)):
        samples.append(sys.argv[i])

Cs = {}

for s in samples:
    print s
    C = gentools.read_configfile(pdir+"/default.conf")

    N = 1         
    C["sample_species"] = {}
    C["sample_species"]["diameter"] = 450E-09
    C["sample_species"]["material_type"] = "virus"

    if s in ["icosahedron","sphere","spheroid","cube","multiple"]:
        C["sample_species"]["sample_type"] = "map3d"
        C["sample_species"]["geometries"] = ["icosahedron"]
        if s in ["icosahedron","multiple"]:
            N = 2
            C["sample_species"]["alignment"] = "random"
            C["sample_species"]["euler_angle_0"] = None
            C["sample_species"]["euler_angle_1"] = None
            C["sample_species"]["euler_angle_2"] = None
            if s == "multiple":
                C["sample"]["number_of_particles"] = 2
                C["sample_species"]["position_variation"] = "uniform"
                C["sample_species"]["position_spread"] = [2000E-9,2000E-9,2000E-9]
            
        C["sample"]["number_of_images"] = N
        if s == "spheroid":
            C["sample_species"]["flattening"] = 0.5

    elif s == "uniform_sphere":
        C["sample_species"]["sample_type"] = s
        
    elif s == "uniform_spheroid":
        C["sample_species"]["sample_type"] = s
        C["sample_species"]["flattening"] = 0.5

    else:
        print "ERROR: INVALID SAMPLE: %s" % s

    I = condor.Input(C)
    O = condor.Output(I)
    O.write("%s/%s.cxi" % (odir,s))

    for i in range(N):
        pylab.imsave('%s/example_%s_%i_intensities.png' % (odir,s,i) ,numpy.log10(O.intensity_pattern[i]),vmin=0,vmax=8)
        pylab.imsave('%s/example_%s_%i_real_space.png' % (odir,s,i) ,abs(O.get_real_space_image(i)))