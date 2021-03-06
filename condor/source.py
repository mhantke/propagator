# -----------------------------------------------------------------------------------------------------
# CONDOR
# Simulator for diffractive single-particle imaging experiments with X-ray lasers
# http://xfel.icm.uu.se/condor/
# -----------------------------------------------------------------------------------------------------
# Copyright 2016 Max Hantke, Filipe R.N.C. Maia, Tomas Ekeberg
# Condor is distributed under the terms of the BSD 2-Clause License
# -----------------------------------------------------------------------------------------------------
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------------------------------
# General note:
# All variables are in SI units by default. Exceptions explicit by variable name.
# -----------------------------------------------------------------------------------------------------

from __future__ import print_function, absolute_import # Compatibility with python 2 and 3
import sys,os
import numpy

import scipy.constants as constants

import logging
logger = logging.getLogger(__name__)

import condor.utils.log
from condor.utils.log import log_and_raise_error,log_warning,log_info,log_debug
from condor.utils.variation import Variation
from condor.utils.photon import Photon
from condor.utils.profile import Profile
 
class Source:
    """
    Class for an X-ray source

    Args:
      :wavelength (float): X-ray wavelength in unit meter

      :focus_diameter (float): Focus diameter (characteristic transverse dimension) in unit meter

      :pulse_energy (float): (Statistical mean of) pulse energy in unit Joule

    Kwargs:
      :profile_model (str): Model for the spatial illumination profile (default `None`)
    
      .. note:: The (keyword) arguments ``focus_diameter`` and ``profile_model`` are passed on to the constructor of :class:`condor.utils.profile.Profile`. For more detailed information read the documentation of the initialisation function.
    
      :pulse_energy_variation (str): Statistical variation of the pulse energy (default ``None``)
      
      :pulse_energy_spread (float): Statistical spread of the pulse energy in unit Joule (default ``None``)
      
      :pulse_energy_variation_n (int): Number of samples within the specified range (default ``None``)

      :polarization (str): Type of polarization can be either *vertical*, *horizontal*, *unpolarized*, or *ignore*  (default ``ignore``)

      .. note:: The keyword arguments ``pulse_energy_variation``, ``pulse_energy_spread``, and ``pulse_energy_variation_n`` are passed on to :meth:`condor.source.Source.set_pulse_energy_variation` during initialisation. For more detailed information read the documentation of the method.

    """
    def __init__(self, wavelength, focus_diameter, pulse_energy, profile_model=None, pulse_energy_variation=None, pulse_energy_spread=None, pulse_energy_variation_n=None, polarization="ignore"):
        self.photon = Photon(wavelength=wavelength)
        self.pulse_energy_mean = pulse_energy
        self.set_pulse_energy_variation(pulse_energy_variation, pulse_energy_spread, pulse_energy_variation_n)
        self.profile = Profile(model=profile_model, focus_diameter=focus_diameter)
        if polarization not in ["vertical", "horizontal", "unpolarized", "ignore"]:
            log_and_raise_error(logger, "polarization = \"%s\" is an invalid input for initialization of Source instance.")
            return
        self.polarization = polarization
        log_debug(logger, "Source configured")

    def get_conf(self):
        """
        Get configuration in form of a dictionary. Another identically configured Source instance can be initialised by:

        .. code-block:: python

          conf = S0.get_conf()         # S0: already existing Source instance
          S1 = condor.Source(**conf)   # S1: new Source instance with the same configuration as S0
        """
        conf = {}
        conf["source"] = {}
        conf["source"]["wavelength"]               = self.photon.get_wavelength()
        conf["source"]["focus_diameter"]           = self.profile.focus_diameter
        conf["source"]["pulse_energy"]             = self.pulse_energy_mean
        conf["source"]["profile_model"]            = self.profile.get_model()
        pevar = self._pulse_energy_variation.get_conf()
        conf["source"]["pulse_energy_variation"]   = pevar["mode"]
        conf["source"]["pulse_energy_spread"]      = pevar["spread"]
        conf["source"]["pulse_energy_variation_n"] = pevar["n"]
        conf["source"]["polarization"]             = self.polarization
        return conf
        
    def set_pulse_energy_variation(self, pulse_energy_variation = None, pulse_energy_spread = None, pulse_energy_variation_n = None):
        """
        Set variation of the pulse energy

        Kwargs:
          :pulse_energy_variation (str): Statistical variation of the pulse energy (default ``None``)

            *Choose one of the following options:*

              - ``\'normal\'`` - random normal (Gaussian) distribution

              - ``\'uniform\'`` - random uniform distribution

              - ``\'range\'`` - equispaced pulse energies around ``pulse_energy``

              - ``None`` - no variation of the pulse energy
      
          :pulse_energy_spread (float): Statistical spread of the pulse energy in unit Joule (default ``None``)
      
          :pulse_energy_variation_n (int): Number of samples within the specified range

            .. note:: The argument ``pulse_energy_variation_n`` takes effect only in combination with ``pulse_energy_variation=\'range\'``
        """
        self._pulse_energy_variation = Variation(pulse_energy_variation, pulse_energy_spread, pulse_energy_variation_n, number_of_dimensions=1)

    def get_intensity(self, position, unit = "ph/m2", pulse_energy = None):
        """
        Calculate the intensity at a given position in the focus

        Args:
          :position: Coordinates [*x*, *y*, *z*] of the position where the intensity shall be calculated
           
        Kwargs:
          :unit (str): Intensity unit (default ``\'ph/m2\'``)

            *Choose one of the following options:*
        
              - ``\'ph/m2\'``

              - ``\'J/m2\'``

              - ``\'J/um2\'``

              - ``\'mJ/um2\'``

              - ``\'ph/um2\'``

           :pulse_energy (float): Pulse energy of that particular pulse in unit Joule. If ``None`` the mean of the pulse energy will be used (default ``None``)
        """
        # Assuming
        # 1) Radially symmetric profile that is invariant along the beam axis within the sample volume
        # 2) The variation of intensity are on much larger scale than the dimension of the particle size (i.e. flat wavefront)
        r = numpy.sqrt(position[1]**2 + position[2]**2)
        I = (self.profile.get_radial())(r) * (pulse_energy if pulse_energy is not None else self.pulse_energy_mean)
        if unit == "J/m2":
            pass
        elif unit == "ph/m2":
            I /= self.photon.get_energy() 
        elif unit == "J/um2":
            I *= 1.E-12
        elif unit == "mJ/um2":
            I *= 1.E-9
        elif unit == "ph/um2":
            I /= self.photon.get_energy()
            I *= 1.E-12
        else:
            log_and_raise_error(logger, "%s is not a valid unit." % unit)
            return
        return I

    def get_next(self):
        """
        Iterate the parameters of the Source instance and return them as a dictionary
        """
        return {"pulse_energy":self._get_next_pulse_energy(),
                "wavelength":self.photon.get_wavelength(),
                "photon_energy":self.photon.get_energy(),
                "photon_energy_eV":self.photon.get_energy_eV()}

    def _get_next_pulse_energy(self):
        p = self._pulse_energy_variation.get(self.pulse_energy_mean)
        # Non-random
        if self._pulse_energy_variation._mode in [None,"range"]:
            if p <= 0:
                log_and_raise_error(logger, "Pulse energy smaller-equals zero. Change your configuration.")
            else:
                return p
        # Random
        else:
            if p <= 0.:
                log_warning(logger, "Pulse energy smaller-equals zero. Try again.")
                self._get_next_pulse_energy()
            else:
                return p

