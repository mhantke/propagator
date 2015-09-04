# -----------------------------------------------------------------------------------------------------
# CONDOR
# Simulator for diffractive single-particle imaging experiments with X-ray lasers
# http://xfel.icm.uu.se/condor/
# -----------------------------------------------------------------------------------------------------
# Copyright 2014 Max Hantke, Filipe R.N.C. Maia, Tomas Ekeberg
# Condor is distributed under the terms of the GNU General Public License
# -----------------------------------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but without any warranty; without even the implied warranty of
# merchantability or fitness for a pariticular purpose. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
# -----------------------------------------------------------------------------------------------------
# General note:
# All variables are in SI units by default. Exceptions explicit by variable name.
# -----------------------------------------------------------------------------------------------------

import numpy

import scipy.constants as constants

import logging
logger = logging.getLogger(__name__)

from log import log_and_raise_error,log_warning,log_info,log_debug

class Photon:
    """
    Class for X-ray photon

    A Photon instance is initialised with one keyword argument - either with ``wavelength``, ``energy`` or ``energy_eV``.
    
    Kwargs:
      :wavelength (float): Photon wavelength in unit meter

      :energy (float): Photon energy in unit Joule

      :energy_eV (float): Photon energy in unit electron volt
    """
    def __init__(self, wavelength=None, energy=None, energy_eV=None):
        if (wavelength is not None and energy is not None) or (wavelength is not None and energy_eV is not None) or (energy is not None and energy_eV is not None):
            log_and_raise_error(logger, "Invalid arguments during initialisation of Photon instance. More than one of the arguments is not None.")
            return
        if wavelength is not None:
            self.set_wavelength(wavelength)
        elif energy is not None:
            self.set_energy(energy)
        elif energy_eV is not None:
            self.set_energy_eV(energy_eV)
        else:
            log_and_raise_error(logger, "Photon could not be initialized. It needs to be initialized with either the wavelength, the photon energy in unit Joule or the photon energy in unit eV.")

    def set_energy(self, energy):
        """
        Set photon energy in unit Joule

        Args:
          :energy (float): Photon energy in unit Joule
        """
        self._energy = energy

    def set_energy_eV(self, energy_eV):
        """
        Set photon energy in unit electron volt

        Args:
          :energy (float): Photon energy in unit electron volt
        """
        self._energy = energy_eV*constants.e


    def set_wavelength(self, wavelength):
        """
        Set photon wavelength

        Args:
          :wavelength (float): Photon wavelength in unit meter
        """
        self._energy = constants.c*constants.h/wavelength

            
    def get_energy(self):
        """
        Return photon energy in unit Joule
        """
        return self._energy

    def get_energy_eV(self):
        """
        Return photon energy in unit electron volt
        """
        return self._energy/constants.e


    def get_wavelength(self):
        """
        Return wavelength in unit meter
        """
        return constants.c*constants.h/self._energy

        
