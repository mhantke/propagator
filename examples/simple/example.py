import numpy
import matplotlib.pyplot as pypl

import condor

# Construct source, sample, detector instanec
src = condor.Source(wavelength=0.1E-9, pulse_energy=1E-3, focus_diameter=1E-6)
sam = condor.Sample()
det = condor.Detector(distance=0.05, pixel_size=110E-6, nx=1000, ny=1000)

# Construct particle instance
par = condor.ParticleSphere(diameter=1E-9, material_type="water")

# Add particle to sample
sam.append_particle(par, "sphere")

# Construct experiment instance
E = condor.Experiment(src, sam, det)

# Calculate diffraction pattern
res = E.propagate()

# Inspect output
data_fourier = res["entry_1"]["data_1"]["data_fourier"]
real_space = numpy.fft.fftshift(numpy.fft.ifftn(data_fourier))
