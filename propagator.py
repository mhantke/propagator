# ----------------------------------------------------------------------------------------------------- 
# PROPAGATOR: Scattering experiment simulator for spheres and customized object maps
# Please type 'help propagator()' for further information.
# -----------------------------------------------------------------------------------------------------
# Author:  Max Hantke - maxhantke@gmail.com
# -----------------------------------------------------------------------------------------------------

import pylab, sys, ConfigParser, numpy, types, pickle, time, math
from matplotlib import rc
import matplotlib.pyplot as mpy
rc('text', usetex=True)
rc('font', family='serif')
import imgutils,tools
from constants import *
from source import *
from sample import *
from detector import *

#import constants,source,sample,detector,tools
#reload(constants)
#reload(source)
#reload(sample)
#reload(detector)
#reload(tools)
#reload(imgutils)

def propagator(input_obj=False):
    """ MAIN FUNCTION of 'propagator.py': 'spow' calculates diffraction under defined conditions specified in the input object.
    Usage: output_obj = spow(input_obj)
    input_obj: configuration object of class 'Input' that sets simulation and program parameters.
    """

    if not isinstance(input_obj,Input):
        print "... ERROR: WRONG INPUT ...\n" 
        print "Usage: spow(input_obj)\n"
        print "   input_obj: configuration object that sets simulation parameters (instance: Input)"
        return
    
    wavelength = input_obj.source.photon.get_wavelength()
    I_0 = input_obj.source.energy / input_obj.source.photon._energy / input_obj.source.get_area() 
    Omega_p = input_obj.detector.get_effective_pixelsize()**2 / input_obj.detector.distance**2

    if isinstance(input_obj.sample,SampleSphere):    
        # scattering amplitude from homogeneous sphere: F = sqrt(I_0 Omega_p) 2pi/wavelength^2 [ 4/3 pi R^3  3 { sin(qR) - qR cos(qR) } / (qR)^3 ] dn_real
        dn_real = (1-input_obj.sample.material.get_n()).real
        R = input_obj.sample.radius
        q = input_obj.detector.write_qmap()
        F = pylab.sqrt(I_0*Omega_p)*2*pylab.pi/wavelength**2*4/3.0*pylab.pi*R**3*3*(pylab.sin(q*R)-q*R*pylab.cos(q*R))/(q*R)**3*dn_real
        F[q==0] = pylab.sqrt(I_0*Omega_p)*2*pylab.pi/wavelength**2*4/3.0*pylab.pi*R**3*dn_real

    if isinstance(input_obj.sample,SampleMap):    
        # scattering amplitude from dn-map: F = sqrt(I_0 Omega_p) 2pi/wavelength^2 [ DFT{dn_perp} ] dA
        dn_perp = input_obj.sample.project()
        dQ = 2*pylab.pi/wavelength*pylab.sqrt(Omega_p)
        dX = 2*pylab.pi/(dQ*max([input_obj.detector.mask.shape[0],input_obj.detector.mask.shape[1]]))
        if max([dn_perp.shape[0],dn_perp.shape[1]]) > input_obj.detector.mask.shape[0]:
            print "ERROR: Field of view in object domain too big for chosen detector pixel size."
            return
        if abs((input_obj.sample.dX-dX)/dX) > 1.0E-3:
            dn_perp = imgutils.resize2d(dn_perp,input_obj.sample.dX,dX)
        F = pylab.sqrt(I_0*Omega_p)*2*pylab.pi/wavelength**2*pylab.fftshift(pylab.fftn(dn_perp,(input_obj.detector.mask.shape[0],input_obj.detector.mask.shape[1])))*dX**2
    
    OUT.write("Propagation finished.\n")

    return Output(F,input_obj)

class Input:
    """
    INPUT configuration for 'propagator()'\n\n
    The 'input'-object contains all the information about the experimental setup (objects 'source', 'sample', 'detector')\n\n
    Initialization of input-object:\n
    - <input> = Input() 
      -> creates an 'input'-object <input> and sets all values to predefined default values.\n
    - <input_obj> = Inout(<conffilename>)
      -> creates an 'input'-object <input> and sets all variables to the values specified in the given configuration file
    """
    
    def __init__(self,configfile=None):
        if configfile != None:
            self.read_configfile(configfile)
            OUT.write("... set configuration in accordance to given configuration-file: %s ...\n" % configfile)
        else:
            self.source = Source(self)
            self.sample = SampleSphere(self)
            self.detector = Detector(self)
            OUT.write("... initial values set to default values ...\n")
    
    def set_sample_empty_map(self):
        """
        Creates empty densitymap. Size in accordance to given detector geometry.
        Densitymap resolution is set according to the detector geometry.
        """
        self.sample = SampleMap(self)

    def set_sample_virus_map(self,radius,oversampling=1.0,eul_ang1=0.0,eul_ang2=0.0,eul_ang3=0.0,speedup_factor=1):
        """
        Creates virus of sphere-volume-equivalent given radius, rotates according to given Euler-angles euler_angle1, euler_angle2 and euler_angle3 [rad].
        Map resolution is set to highest resolution that can be achieved by the given detector geometry.
        For rough simulations the resolution can be changed by setting the optional argument 'speedup_factor' to an integer bigger than 1.
        """
        self.sample = SampleMap(self)
        self.sample.dX /= oversampling
        self.sample.put_virus(radius,eul_ang1,eul_ang2,eul_ang3,None,None,None,speedup_factor)
        if oversampling != 1.0:
            self.sample.map3d = imgutils.downsample3d_fourier(self.sample.map3d,1/oversampling)
            self.sample.dX *= oversampling

    def set_sample_sphere_map(self,radius=225E-09,oversampling=1.0,**materialargs):
        """
        Creates sphere of given radius.
        """
        self.sample = SampleMap(self)
        self.sample.dX /= oversampling
        self.sample.put_sphere(radius,**materialargs)
        if oversampling != 1.0:
            self.sample.map3d = imgutils.downsample3d_fourier(self.sample.map3d,1.0/oversampling)
            self.sample.dX *= oversampling

    def set_sample_homogeneous_sphere(self,radius=225E-09,**materialargs):
        """
        Sets sample object to homogeneous sphere having the given radius. Atomic composition values and massdensity are set according to the given material arguments.
        Examples for usage:
        - setting atomic composition values and massdensity manually:
          set_sample_homogeneous_sphere(radius,massdensity=1000,cH=2,cO=1)
        - setting atomic composition values and massdensity according to given materialtype:
          set_sample_homogeneous_sphere(radius,materialtype='protein')
        available materialtypes: 'protein', 'virus', 'cell', 'latexball', 'water', 'Au'
        """ 
        self.sample = SampleSphere(self,radius,**materialargs)

    def read_configfile(self,configfile):
        """ Reads given configuration file and sets configuration to the input-object """
        self.source = Source(self)
        self.sample = SampleSphere(self)
        self.source = Detector(self)
        config = ConfigParser.ConfigParser()
        try:
            config.readfp(open(configfile))
        except IOError:
            print "ERROR: Can't read configuration-file."
            return
        self.source.photon.set_wavelength(config.getfloat('source','wavelength'))
        self.source.sizex = config.getfloat('source','sizex')
        self.source.sizey = config.getfloat('source','sizey')
        self.source.energy = config.getfloat('source','energy')
        mat = config.get('sample','material')
        args = []
        if mat == 'custom':
            cX_list = config.items('sample')
            for cX_pair in cX_list:
                if cX_pair[0][0] == 'c':
                    el = cX_pair[0]
                    el = el[1:].capitalize()
                    val = float(cX_pair[1])
                    args.append(("'c%s'" % el,val))
            args.append(('massdensity',config.getfloat('sample','massdensity')))
        else:
            keys = ['cH','cN','cO','cP','cS']
            for i in range(0,len(keys)):
                args.append((keys[i],DICT_atomic_composition[mat][i]))
            args.append(('massdensity',DICT_massdensity[mat]))
        args= dict(args)
        self.sample = SampleSphere(config.getfloat('sample','radius'),self,**args)
        self.detector.distance = config.getfloat('detector','distance')
        self.detector.pixelsize = config.getfloat('detector','psize')
        self.detector.binning = config.getint('detector','binned')
        self.detector.Nx = config.getint('detector','Nx')
        self.detector.Ny = config.getint('detector','Ny')
        self.detector.set_mask(config.getfloat('detector','gapsize'),config.get('detector','gaporientation'))

class Output:
    """
    OUTPUT of propagator provides user with results and functions for plotting.
    """
    def __init__(self,amplitudes,input_object):
        self.amplitudes = amplitudes.copy()
        self.input_object = input_object 
    
    def get_intensity_pattern(self):
        """
        Returns 2-dimensional array with intensity values in photons per pixel (binned).
        """
        return abs(self.amplitudes)**2

    def get_intensity_radial_average(self):
        """
        Returns 1-dimensional array with intensity average in photons per pixel (binned). x-coordinate sampling is pixel (binned). 
        """
        I = self.get_intensities_pattern()
        return imgutils.radial_pixel_average(I)

    def get_intensity_radial_average(self,noise=None):
        """
        Returns 1-dimensional array with intensity sum in photons. x-coordinate sampling is pixel (binned). 
        """
        I = self.get_intensities_pattern()
        return imgutils.radial_pixel_sum(I)
            
    def plot_radial_distribution(self,scaling="binned pixel and nyquist pixel",mode="all",noise=None):
        """
        Creates 1-dimensional plot(s) showing radial distribution of scattered photons.
        Usage: plot_radial_distribution([scaling],[mode],[noise])
        Arguments:
        - scaling: Specifies spatial scaling.
                   Can be set to 'binned pixel', 'nyquist pixel', 'binned pixel and nyquist pixel' or 'meter'.
                   'binned pixel and nyquist pixel' leads to creation of two plots in one figure using pixel- and Nyquist-pixel-scaling.
        - mode:    Mode specifies whether the radial average or the radial sum will be plotted.
                   Can be set to 'radial average', 'radial sum' or 'all'.
        - noise:   Specifies noise and can be set to 'poisson'.
        """
        if noise == 'poisson':
            def noise(data): return pylab.poisson(data)
        else:
            def noise(data): return data
        def get_arguments(sc):
            if mode == "all":
                legend_args = [('Radial sum', 'Radial average'),'upper right']
                if sc == "binned pixel":
                    r = numpy.arange(0,len(self.intensity_radial_sum),1)
                elif sc == "nyquist pixel":
                    r = numpy.arange(0,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2/len(self.intensity_radial_sum))
                plot_args = [r,noise(self.get_radial_distribution(sc,'radial sum')),'k',r,noise(self.get_radial_distribution(sc,'radial average')),'k:']
            else:
                if sc == "binned pixel":
                    r = numpy.arange(0,len(self.intensity_radial_sum),1)
                elif sc == "nyquist pixel":
                    r = numpy.arange(0,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2/len(self.intensity_radial_sum))
                elif sc == "meter":
                    r = numpy.arange(0,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2*self.pixel_size,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2*self.pixel_size/len(self.intensity_radial_sum))
                if mode == "radial sum":
                    legend_args = [('Radial sum'),'upper right']
                    plot_args = [r,noise(self.get_radial_distribution(sc,mode)),'k']
                elif mode == "radial average":
                    legend_args = [('Radial average'),'upper right']
                    plot_args = [r,noise(self.get_radial_distribution(sc,mode)),'k']
            return [plot_args,legend_args]

        if scaling == "binned pixel and nyquist pixel":
            f1d = pylab.figure(figsize=(10,5))
            f1d.suptitle("\nRadial distribution of scattered photons in detector plane", fontsize=16)
            str_scaling = "binned pixel"
            f1d_ax_left = f1d.add_axes([0.1, 0.1, 0.35, 0.7],title='Radial scaling:' + str_scaling,xlabel="r [" + str_scaling + "]",ylabel="I(r) [photons/" + str_scaling + "]")
            str_scaling = "nyquist pixel"
            f1d_ax_right = f1d.add_axes([0.55, 0.1, 0.35, 0.7],title='Radial scaling:' + str_scaling,xlabel="r [" + str_scaling + "]",ylabel="I(r) [photons/" + str_scaling + "]")
            [plot_args,legend_args] = get_arguments('binned pixel')
            f1d_ax_left.semilogy(*plot_args)
            f1d_ax_left.legend(*legend_args)
            [plot_args,legend_args] = get_arguments('nyquist pixel')
            f1d_ax_right.semilogy(*plot_args)
            f1d_ax_right.legend(*legend_args)
            f1d.show()
            return
        elif scaling == "binned pixel":
            str_scaling = "binned pixel"
            r = numpy.arange(0,len(self.intensity_radial_sum),1)
        elif scaling == "nyquist pixel":
            str_scaling == "nyquist pixel"
            r = numpy.arange(0,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2,min([self.nyquistpixel_number_x,self.nyquistpixel_number_y])/2/len(self.intensity_radial_sum))
        elif scaling == "meter":
            str_scaling = "meter"
            r = numpy.arange(0,min([self.pixel_number_x,self.pixel_number_y])/2*self.pixel_size,min([self.pixel_number_x,self.pixel_number_y])/2*self.pixel_size/len(self.intensity_radial_sum))
        else:
            print "ERROR: %s is no valid scaling" % scaling
            return
        [plot_args,legend_args] = get_arguments(r,scaling)
        f1d = pylab.figure(figsize=(5,5))
        f1d.suptitle("\nRadial distribution of scattered photons in detector plane", fontsize=16)
        f1d_ax = f1d.add_axes([0.2, 0.1, 0.7, 0.7],title='Radial scaling:' + str_scaling,xlabel="r [" + str_scaling + "]",ylabel="I(r) [photons/" + str_scaling + "]")
        f1d_ax.semilogy(*plot_args)
        f1d_ax.legend(*legend_args)
        f1d.show()

    def readout_pattern(self):
        return 0
            
    def _get_gapsize(self,X_min,X_max,Y_min,Y_max):
        """
        Returns gapsize of pattern in pixels (binned)
        """
        gapsize = 0
        M = self.input_object.detector.mask
        for i in pylab.arange(X_min,X_max+1,1):
            if (M[:,i]==0).all():
                for j in pylab.arange(i,X_max+1,1):
                    if (M[:,j]==1).any():
                        gapsize = j-i
                        break
                break
        for i in pylab.arange(Y_min,Y_max+1,1):
            if (M[i,:]==0).all():
                for j in pylab.arange(i,Y_max+1,1):
                    if (M[j,:]==1).any():
                        gapsize = j-i
                        break
                break
        return gapsize

    def _get_pattern_limits(self):
        """
        Returns spatial limits of pattern in pixels (binned)
        """
        X_min = 0
        Y_min = 0
        X_max = self.amplitudes.shape[1]
        Y_max = self.amplitudes.shape[0]
        M = self.input_object.detector.mask
        for i in pylab.arange(0,M.shape[1],1):
            if (M[:,i]==1).any():
                X_min = i
                break
        for i in M.shape[1]-pylab.arange(1,M.shape[1],1):
            if (M[:,i]==1).any():
                X_max = i
                break
        for i in pylab.arange(0,M.shape[0],1):
            if (M[i,:]==1).any():
                Y_min = i
                break
        for i in M.shape[0]-pylab.arange(1,M.shape[0],1):
            if (M[i,:]==1).any():
                Y_max = i
                break
        return [X_min,X_max,Y_min,Y_max]

    def plot_pattern(self,**kwargs):
        """
        Creates 2-dimensional plot(s) of the distribution of scattered photons.
        Usage: plot_pattern([scaling],[poissonnoise],[logscale],[saturationlevel])
        Keyword arguments:
        - scaling:          'nyquist', 'meter', 'binned pixel' or 'pixel' (default)
        - noise:            'poisson' or 'none' (default)
        - logscale:         False or True (default)
        - saturationlevel:  True or False (default)
        - use_gapmask:      False or True (default)
        """

        scaling = 'pixel'
        scalingargs = ['nyquist','meter','binned pixel','pixel']
        noise = 'none'
        noiseargs = ['poisson','none']
        logscale = True
        logscaleargs = [False,True]
        saturationlevel = False
        saturationlevelargs = [False,True]
        use_gapmask = True
        use_gapmaskargs = [False,True]
        outfile = False
        outfileargs = [True,False]

        I = self.get_intensity_pattern()

        optionkeys = ["scaling","noise","logscale","saturationlevel","use_gapmask","outfile"]
        options = [scaling,noise,logscale,saturationlevel,use_gapmask]
        optionargs = [scalingargs,noiseargs,logscaleargs,saturationlevelargs,use_gapmaskargs,outfileargs]
        keys = kwargs.keys()
        for i in range(0,len(keys)):
            key = keys[i]
            if not key in optionkeys:
                print "ERROR: %s is not a proper key." % key
                return
            keyarg = kwargs[key]
            j = optionkeys.index(key)
            if not keyarg in optionargs[j]:
                print "ERROR: %s is not a proper argument for %s." % (keyarg,key)
                return
            exec "%s = '%s'" % (key,keyarg)
        
        eff_pixelsize_detector = self.input_object.detector.get_effective_pixelsize()
        pixelsize_detector = self.input_object.detector.pixelsize
        pixelsize_nyquist = tools.get_nyquist_pixelsize(self.input_object.detector.distance,self.input_object.source.photon.get_wavelength(),self.input_object.sample.get_area())
        if scaling == "nyquist":
            I *= eff_pixelsize_nyquist**2/pixelsize_detector**2
            u = eff_pixelsize_detector/pixelsize_nyquist
            str_scaling = "Nyquist pixel"
        elif scaling == "meter":
            I /= eff_pixelsize_detector**2
            u = eff_pixelsize_detector
            str_scaling = "m^2"
        elif scaling == "pixel":
            I /= 1.0*self.input_object.detector.binning**2
            u = self.input_object.detector.binning
            str_scaling = scaling
        elif scaling == "binned pixel":
            u = 1.0
            str_scaling = scaling

        I /= u**2

        if noise == "poisson":
            I = pylab.poisson(I)

        if saturationlevel and self.input_object.detector.saturationlevel > 0:
            I *= u**2/(1.0*self.input_object.detector.binning**2)
            I[I>self.input_object.detector.saturationlevel] = self.input_object.detector.saturationlevel
            I /= u**2/(1.0*self.input_object.detector.binning**2)

        [X_min,X_max,Y_min,Y_max] = self._get_pattern_limits()
        xlimit = u*(X_max-X_min)
        ylimit = u*(Y_max-Y_min)
        gapsize = self._get_gapsize(X_min,X_max,Y_min,Y_max)

        I = I[Y_min:Y_max+1,X_min:X_max+1]

        if str_scaling == "binned pixel":
            if self.input_object.detector.binning == 1:
                str_scaling_label = "pixel"
            else:
                str_scaling_label = "%ix%i binned pixel" % (self.input_object.detector.binning,self.input_object.detector.binning)
        else:
            str_scaling_label = str_scaling

        if use_gapmask:
            M = self.input_object.detector.mask.copy()
            if saturationlevel and self.input_object.detector.saturationlevel > 0:
                M[I>=self.input_object.detector.saturationlevel] = 0
            M[M==0] *= pylab.nan

        if logscale:
            I = pylab.log10(I)
            I[I==-pylab.Inf] = I[I!=-pylab.Inf].min()-1.0
            I *= M
            str_Iscaling = r"$\log\left( I \left[ \frac{\mbox{photons}}{\mbox{%s}} \right] \right)$" % str_scaling
        else:
            str_Iscaling = r"$I \left[ \frac{\mbox{photons}}{\mbox{%s}} \right]$" % str_scaling

        Wsizey = 9#10
        Wsizex = 9#8 # 7.5
        fsize = 12
        pylab.clf()
        fig = mpy.figure(1,figsize=(Wsizex,Wsizey))
        mpy.rcParams['figure.figsize'] = Wsizex,Wsizey
        fig.suptitle(r"\n - PROPAGATOR -", fontsize=fsize+2)
        alignment = {'horizontalalignment':'center','verticalalignment':'center'}

        fig.text(0.5,(16.75/18.0),r"$E_{\mbox{photon}} = %.0f$ eV ; $\lambda = %.2f$ nm ; $N_{\mbox{photons}} = %.1e$ ; $D_{\mbox{detector}} = %0.3f$ mm" %  (self.input_object.source.photon.get_energy("eV"),self.input_object.source.photon.get_wavelength()/1.0E-09,self.input_object.source.energy/self.input_object.source.photon.get_energy(),self.input_object.detector.distance/1.0E-03),fontsize=fsize,bbox=dict(fc='0.9',ec="0.9",linewidth=10.0),**alignment) 

        ax = fig.add_axes([3/15.0,5/18.0,10/15.0,10/18.0],title=r'Simulated intensity readout')
        ax.set_xlabel(r"$x$ [" + str_scaling_label + "]",fontsize=fsize)
        ax.set_ylabel(r"$y$ [" + str_scaling_label + "]",fontsize=fsize)

        axcolor = fig.add_axes([3/15.0,3.5/18.0,10/15.0,0.5/18.0])
        for a in [ax,axcolor]:
            for label in a.xaxis.get_ticklabels():
                label.set_fontsize(fsize)
            for label in a.yaxis.get_ticklabels():
                label.set_fontsize(fsize)

        im = ax.matshow(I,extent=[-xlimit/2,xlimit/2,-ylimit/2,ylimit/2],interpolation="nearest",)
        cb = fig.colorbar(im, cax=axcolor,orientation='horizontal')
        cb.set_label(str_Iscaling,fontsize=fsize)

        oversampling_ratio = pixelsize_nyquist/eff_pixelsize_detector
        oversampling_ratio_wo_binning = pixelsize_nyquist/pixelsize_detector
        D = self.input_object.detector.distance
        A =  self.input_object.sample.get_area()
        wavelength = self.input_object.source.photon.get_wavelength()
        res_horizontally = tools.get_max_crystallographic_resolution(wavelength,
                                                                     I.shape[1]/2.0*eff_pixelsize_detector,
                                                                     self.input_object.detector.distance)
        res_vertically = tools.get_max_crystallographic_resolution(wavelength,
                                                                   I.shape[0]/2.0*eff_pixelsize_detector,
                                                                   self.input_object.detector.distance)
        res_corner = tools.get_max_crystallographic_resolution(wavelength,
                                                               pylab.sqrt((I.shape[1]/2.0)**2+(I.shape[0]/2.0)**2)*eff_pixelsize_detector,
                                                               self.input_object.detector.distance)
        miss_Ny = gapsize*eff_pixelsize_detector/pixelsize_nyquist
        fig.text(0.5,(1./18.0),r"\textbf{Properties}\\ Linear oversampling ratio: $%.2f$ (binning $%i\times%i$) ; $%.2f$ (no pixel binning)\\" % (oversampling_ratio,self.input_object.detector.binning,self.input_object.detector.binning,oversampling_ratio_wo_binning)+
                 r"Crystallographic resolution (full period): $%.1f$ nm (horizontal) ; $%.1f$ nm (vertical) ; $%.1f$ nm (corner)\\" % (res_horizontally/1.0E-09,res_vertically/1.0E-09,res_corner/1.0E-09)+
                 r"Gap width: $g=%.2f\mbox{ mm}=%.1f$ Nyquist pixels" % (gapsize*eff_pixelsize_detector/1.0E-03,miss_Ny),fontsize=fsize,bbox=dict(fc='0.9',ec="0.9",linewidth=10.0),**alignment)
        #if miss_Ny>2.8:
        #    print "\n!!!\nMissing mode(s) expected (gap width: %.1f Nyquist pixels) \n\nTweaking of one of the parameters recommended:\n- Wavelength w = %.2f nm\n- Sample radius r = %.0f nm\n- Gap size g = %.1f mm\n- Detector distance d = %.0f mm" % (miss_Ny,(rec_wavelength+0.01E-9)*1.0E9,(rec_r-1.0E-9)*1.0E9,(rec_gapsize-0.1E-3)*1.0E3,(rec_d+1.0E-3)*1.0E3)

        if outfile:
            mpy.savefig("intensity_pattern.png",dpi=300)
        else:
            fig.show()
   
    def save_pattern_to_file(self,filename,scaling="binned pixel",*arguments):
        """
        Saves dataset to file of specified format.
        Usage: fo_file(filename,[scaling],[colorscale])
        Arguments:
        - filename: The file-format is specified using one of the following file-endings:
                    - '.h5'
                    - '.png'
        - scaling:  Specifies spatial scaling.
                    Can be set to 'pixel' (default), 'nyquist pixel' or 'meter'.
        - colorscale (only for png-files):
                    - Jet
                    - Gray (default)
                    - Log (can be combined with the others)
        """
        import spimage,h5py
        pattern = self.get_pattern(scaling)
        if filename[-3:]=='.h5':
            color = 0
        elif filename[-3:]=='.png':
            color = 16
            for flag in arguments:
                if flag == 'Jet':
                    color = 16
                elif flag == 'Gray':
                    color = 1
                elif flag == 'Log':
                    color += 128
                else:
                    print "unknown flag %s" % flag
                    return
        else:
            print "ERROR: %s is not a valid fileformat for this function." % filename[-3:]
            return
        tmp_data = spimage.sp_image_alloc(len(pattern[0]),len(pattern),color)
        tmp_data.image[:,:] = pattern[:,:]
        spimage.sp_image_write(tmp_data,filename,0)
        spimage.sp_image_free(tmp_data)