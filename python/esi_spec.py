"""
Code to take over after the calibration, etc., that is done by the code
in the esi directory.
"""

import numpy as np
from astropy.io import fits as pf
import spec_simple as ss
from matplotlib import pyplot as plt
from ccdredux import sigma_clip
from scipy import ndimage,interpolate
import special_functions as sf

class Esi2d(ss.Spec2d):
    """
    A class for ESI 2D spectra, for which Matt's / Lindsay's calibration
    code produces a multi-extension fits files containing 10 2D spectra,
    one for each of the 10 orders produced by the spectrograph
    """

    def __init__(self, infile, varfile=None):
        """

        Create an instance of this class by loading the data from the input
        file into 10 Spec2d instances.

        """

        """
        Start by setting up some default values
        Each order for ESI has a different plate scale in arcsec/pix 
        """
        self.arcsecperpix = np.array([
                0.120, # order 1
                0.127, # order 2
                0.134, # order 3
                0.137, # order 4
                0.144, # order 5
                0.149, # order 6
                0.153, # order 7
                0.158, # order 8
                0.163, # order 9
                0.168  # order 10
                ])
        self.extvar = None

        """ 
        Set the range of valid pixels for each order, expressed as 
        blue (start of good pixels) to red (end of good pixels) 
        """
        self.blue = [1500,1400,1300,1200,1100,900,600,200,0,0,0]
        self.red = [3000,3400,3700,-1,-1,-1,-1,-1,-1,-1]

        """ Open the multiextension fits file that contains the 10 orders """
        self.infile = infile
        self.hdu = pf.open(infile)
        print ''
        print self.infile

        """ If there is an external variance file, open that """
        if varfile is not None:
            self.extvar = pf.open(varfile)

        """ Load each order into its own Spec2d container """
        self.order = []
        print ''
        print 'Order  Shape    Dispaxis'
        print '----- --------- --------'
        for i in range(10):
            if self.extvar is not None:
                tmpspec = ss.Spec2d(None,hdulist=self.hdu,hext=i+1,
                                    extvar=self.extvar,verbose=False,
                                    logwav=True,fixnans=False)
            else:
                tmpspec = ss.Spec2d(None,hdulist=self.hdu,hext=i+1,verbose=False,
                                    logwav=True,fixnans=False)
            print ' %2d   %dx%d     %s' % \
                ((i+1),tmpspec.data.shape[1],tmpspec.data.shape[0],
                 tmpspec.dispaxis)
            self.order.append(tmpspec)

    #-----------------------------------------------------------------------

    def plot_profiles(self):
        """

        Plots, in one figure, the spatial profiles for all the 10 orders

        """

        for i in range(10):
            plt.subplot(2,5,(i+1))
            self.order[i].spatial_profile()

    #---------------------------------------------------------------------------

    def get_ap_oldham(self, slit, B, R, apcent, apnum, wid, order, 
                      doplot=True):
        """
        Defines a uniform aperture as in the example ESI extraction scripts
        from Lindsay
        """

        xproj = np.median(slit[:,B:R],1) 
        m,s = sigma_clip(xproj)
           
        smooth = ndimage.gaussian_filter(xproj,1)
        if order == 2: # NB: This was 3 in the original file, see note below
            smooth = ndimage.gaussian_filter(xproj[:-30],1)
        x = np.arange(xproj.size)*1. 

        """ 
        The four parameters immediately below are the initial guesses
        bkgd, amplitude, mean location, and sigma for a Gaussian fit
        """
        fit = np.array([0.,smooth.max(),smooth.argmax(),1.])
        fit = sf.ngaussfit(xproj,fit)[0] 

        cent = fit[2] + apcent[apnum]/self.arcsecperpix[order]
        print cent
        apmax = 0.1 * xproj.max()
        ap = np.where(abs(x-cent)<wid/self.arcsecperpix[order],1.,0.)

        if doplot & order<60:
            plt.subplot(2,5,(order+1))
            plt.plot(x,apmax*ap) # Scale the aperture to easily see it
            plt.plot(x,xproj)
            plt.ylim(-apmax,1.1*xproj.max())
    
        ap = ap.repeat(slit.shape[1]).reshape(slit.shape)
        return ap,fit

    #-----------------------------------------------------------------------

    def extract_oldham(self, order, apcent, apnum, wid):
        """
        Implements Lindsay Oldham's (or perhaps Matt Auger's) method
         for extracting the spectrum from an individual spectral order
         on ESI.

        Inputs:
          order  - the requested spectral order
        """

        """ 
        Make temporary copies of the science and variance spectra, and
        get information about their properties
        """
        spec  = self.order[order]
        slit  = spec.data.copy()
        vslit = spec.vardata.copy()
        vslit[vslit<=0.] = 1e9
        vslit[np.isnan(vslit)] = 1e9
        vslit[np.isnan(slit)] = 1e9
        h = spec.hdr
        x = np.arange(slit.shape[1])*1.
        w = 10**(h['CRVAL1']+x*h['CD1_1']) 

        """ Make the apertures """
        B = self.blue[order]
        R = self.red[order]
        ap,fit = self.get_ap_oldham(slit,B,R,apcent,apnum,wid,order)

        """ Set up to do the extraction, including by normalizing ap """
        ap[vslit>=1e8] = 0.
        ap = ap/ap.sum(0)
        ap[np.isnan(ap)] = 0.
        slit[np.isnan(slit)] = 0.

        """ Extract the spectrum (I do not understand the weighting here) """
        spec = (slit*ap**2).sum(0) 
        vspec = (vslit*ap**4).sum(0)

        """ 
        Normalize the spectrum and its associated variance 
        Need to do the variance first, or else you would incorrectly
        be using the normalized spectrum to normalize the variance
        """
        vspec /= np.median(spec)**2
        spec /= np.median(spec)

        """ Save the output in a Spec1d container """
        newspec = ss.Spec1d(wav=w,flux=spec,var=vspec)
        # scales.append(h['CD1_1'])
        return newspec

    #-----------------------------------------------------------------------

    def extract_all(self, method='oldham', doplot=True):
        """
        Goes through each of the 10 orders on the ESI spectrograph and
        extracts the spectrum via one of two procedures:
        1. Using the Spec2d class methods from spec_simple.py (method='cdf')
          This approach does the two-step extraction procedure using the
          relevant methods in the Spec2d class in spec_simple.py, namely
          (1) find_and_trace and (2) extract_spectrum.
          xxxxx
        2. Using the code from Lindsay Oldham (or perhaps Matt Auger) implemented
          above (method='oldham')
          In this approach, the two step procedure is (1) get_ap_oldham, and
          (2) extract_oldham
          xxxxx
        """

        """ First plot all the spatial profiles """
        plt.figure(1)
        plt.clf()
        self.plot_profiles()

        """ 
        Extract the spectra 
        EXPERIMENTAL VERSION RIGHT NOW
        """
        for i in range(10):
            if method == 'cdf':
                plt.figure(i+1)
                plt.clf()
                self.order[i].find_and_trace()
                self.order[i].extract_new()
