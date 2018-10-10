"""

osiris_funcs.py

"""

import numpy as np
from matplotlib import pyplot as plt
from astropy.io import fits as pf
from SpecIm import imfuncs as imf
from SpecIm import spec_simple as ss

# ===========================================================================

class osCube(imf.Image):
    """
    A class used to visualize and analyze OSIRIS data
    """

    def __init__(self, infile, verbose=True):
        """
        Loads in an OSIRIS data cube that was processed through the
        standard data reduction pipeline and, possibly, has had some
        additional processing done.
        """

        """ Read the data into an Image structure """
        imf.Image.__init__(self, infile, verbose=verbose)

        """ Set a default image plane to plot """
        self.set_imslice(0, display=False)

        """ Set up the wavelength vector based on the header information """
        hdr = self.hdu[0].header
        nwav = hdr['naxis1']
        self.wav = np.arange(nwav)
        self.wav = hdr['crval1'] + self.wav * hdr['cdelt1']

        """ Convert from nm to angstroms, including in the header """
        self.wav *= 10.
        hdr['crval1'] *= 10.
        hdr['cdelt1'] *= 10.

        """ Save the sizes of the array in easily accessible form """
        self.xsize = self.hdu[0].data.shape[0]
        self.ysize = self.hdu[0].data.shape[1]
        self.wsize = self.hdu[0].data.shape[2]

        """ Set default values """
        self.cube = None

    # -----------------------------------------------------------------------

    def set_imslice(self, imslice=0, hext=0, display=True, mode='xy',
                    **kwargs):
        """
        Sets the 2-dimension slice to use for the display functions.

        Inputs:
          imslice - which image slice to use.
        """

        """ Get the number of dimensions in the input image """
        hdr = self.hdu[hext].header
        if 'NAXIS' in hdr.keys():
            ndim = hdr['naxis']
        else:
            raise KeyError

        """
        The OSIRIS data-reduction pipeline produces a 3-dimensional data cube.
        Check this
        """
        if ndim != 3:
            print('')
            print('ERROR: Expected a 3-dimensional data cube but found '
                  '%d dimensions' % ndim)
            print('')
            raise ValueError

        """
        Select the image slice to use.  Right now this assumes the standard
        axis order produced by the pipeline, namely that CTYPE1 is WAVE,
        CTYPE2 is RA, and CTYPE3 is DEC.  This means that the data array
        structure is hard-wired to this assumption
        """

        nwave = hdr['naxis1']
        if imslice >= nwave:
            print('')
            print('ERROR: Requested an image slice outside the available '
                  'range')
            print('Maximum available slice value is %d' % (nwave-1))
            print('')
            raise IndexError

        self.data = np.transpose(self.hdu[hext].data[:, :, imslice].copy())

        """ Display the image slice if requested """
        self.found_rms = False
        if display:
            self.display(title='Image Plane %d (zero-indexed)' % imslice,
                         mode=mode, **kwargs)

    # -----------------------------------------------------------------------

    def compress_spec(self, wmin, wmax, wmode='slice', combmode='sum',
                      hext=0, display=True, **kwargs):
        """
        Compresses the data cube along the spectral dimension, but only
        for image slices between some minimum and maximum wavelengths.
        These wavelength limits (wmin, wmax) can be set either by the slice
        number or the actual wavelength in Angstrom [wavelength mode is NOT
        yet implemented].

        The compression can be done either as a sum or as a median.

        The result is a 2-dimensional spatial image, which is stored in the
        data container and, thus, can be easily displayed.
        """

        """ First select the image slices to use """
        if wmode == 'wavelength':
            print('NOTE: wavelength mode has not yet been implemented')
            return
        else:
            minslice = wmin
            maxslice = wmax
            wavmin = self.wav[minslice]
            wavmax = self.wav[maxslice]
        print('')
        print('Data cube will be compressed along the spectral direction')
        print('  Image slice range: %d - %d' % (minslice, maxslice))
        print('  Corresponding wavelength range: %8.2f - %8.2f'
              % (wavmin, wavmax))

        """ Create a temporary cube container """
        cube = self.hdu[hext].data[:, :, minslice:(maxslice+1)].copy()

        """ Compress the temporary cube along the spectral axis """
        if combmode == 'median':
            self.data = np.transpose(np.median(cube, axis=2))
        else:
            self.data = np.transpose(cube.sum(axis=2))

        """ Display the result if requested """
        if display:
            self.display(**kwargs)

        """ Clean up """
        del(cube)

    # -----------------------------------------------------------------------

    def whitelight(self, combmode='sum', hext=0, display=True, verbose=True,
                   **kwargs):
        """
        Creates, and displays if requested, the "white light" image.
        This is a specialized version of the compress_spec method, which
        compresses the cube along the spectral direction, but for the full
        data cube.
        """

        if verbose:
            print('Creating white light image')

        """ Set up for running compress_spec on the full data cube """
        wmax = self.hdu[hext].data.shape[2] - 1
        self.compress_spec(wmin=0, wmax=wmax, wmode='slice', combmode=combmode,
                           hext=hext, display=display, **kwargs)

    # -----------------------------------------------------------------------

    def set_1dspec(self, x, y, hext=0, display=True, **kwargs):
        """
        Takes a spaxel designated by its (x, y) coordinates and extracts the
        spectral information into a Spec1d container.
        Also plot the 1d spectrum if requested.
        """

        flux = self.hdu[hext].data[x, y, :]
        print(self.wav.size, flux.size)
        spec = ss.Spec1d(wav=self.wav, flux=flux)

        if display:
            fnum = max(plt.get_fignums()) + 1
            plt.figure(fnum)
            spec.plot(**kwargs)

        self.spec = spec

    # -----------------------------------------------------------------------

    def click_1dspec(self, hext=0, xysmooth=1, **kwargs):
        """
        An interactive interface to set_1dspec.  Produces the 1D spectrum
        associated with the spaxel that is clicked.
        """

        self.start_interactive()
        self.set_1dspec(int(self.xclick), int(self.yclick), **kwargs)

    # -----------------------------------------------------------------------

    def select_cube(self, wmin=None, wmax=None, xmin=None, xmax=None,
                    ymin=None, ymax=None, wmode='slice', hext=0,
                    verbose=False):
        """
        Creates a cube to analyze, defined by ranges in x, y, and wavelength.
        """

        """ Use default values if none are requested """
        if xmin == None:
            xmin = 0
        if xmax == None:
            xmax = self.xsize
        if ymin == None:
            ymin = 0
        if ymax == None:
            ymax = self.ysize
        if wmin == None:
            wmin = 0
        if wmax == None:
            wmax = self.wsize

        if verbose:
            print('')
            print('Creating a cube from original data with ranges:')
            print('  x:      %d - %d' % (xmin,xmax))
            print('  y:      %d - %d' % (ymin,ymax))
            print('  lambda: %d - %d (slice number)' % (wmin,wmax))

        """ Select the cube """
        self.cube = self.hdu[0].data[xmin:xmax, ymin:ymax, wmin:wmax]
        self.cubehdr = self.hdu[0].header.copy()
        self.cubehdr['crpix1'] -= wmin
        self.cubehdr['crpix2'] -= ymin
        self.cubehdr['crpix3'] -= xmin

    # -----------------------------------------------------------------------

    def save_xyl(self, outfits, outtext=None, **kwargs):
        """
        
        Saves the data cube as a fits file but with the spectral axis
         as axis 3 (in fits parlance) rather than axis 1.
         The OSIRIS data reduction pipeline produces a data cube with
         FITS data axis order of (lambda, y, x).  This method produces
         an output cube with a FITS data axis order of (x, y, lambda)
        If the optional outtext parameter is set to a filename, then an
         output text file will be created in the format expected by
         Francesca Rizzo's modeling code

        Required inputs:
          outfits - name of output fits file

        Optional inputs:
          outtext - if set to a string value, then save an output text file
                    in the format expected by Francesca Rizzo's modeling code.
                    The default value (None) means that no output file is
                    created.
        """

        """
        Create a copy of the data cube and swap the axes
        """

        self.select_cube(verbose=True, **kwargs)
        tmp = self.cube.copy()
        tmp2 = np.swapaxes(tmp, 0, 2)

        """
        Create a new header and write the output file
        """
        hdr0 = self.cubehdr
        tmphdu = pf.PrimaryHDU(tmp2)
        hdr = tmphdu.header
        """ Non-coordinate keywords """
        klist = ['bunit', 'bscale', 'bzero', 'itime', 'coadds', 'sampmode',
                 'numreads', 'saturate', 'instr', 'pscale', 'object',
                 'pa_spec', 'sfilter', 'telescop', 'instrume', 'targwave',
                 'airmass', 'wcsaxes']
        for k in klist:
            try:
                hdr[k] = hdr0[k]
            except KeyError:
                continue
        """
        Coordinate keywords.
        For now we're assuming that the input was (Wavelength, Dec, RA) and
         the output will be (RA, Dec, Wavelength)
        """
        crlist = ['ctype', 'cunit', 'crval', 'crpix', 'cdelt']
        for k in crlist:
            hdr['%s1' % k] = hdr0['%s3' % k]
            hdr['%s2' % k] = hdr0['%s2' % k]
            hdr['%s3' % k] = hdr0['%s1' % k]
        hdr['cunit3'] = 'Ang'
        """ PC matrix """
        hdr['pc1_1'] = hdr0['pc%d_%d' % (self.raaxis, self.raaxis)]
        hdr['pc1_2'] = hdr0['pc%d_%d' % (self.raaxis, self.decaxis)]
        hdr['pc2_1'] = hdr0['pc%d_%d' % (self.decaxis, self.raaxis)]
        hdr['pc2_2'] = hdr0['pc%d_%d' % (self.decaxis, self.decaxis)]

        print('')
        print('Saving to output file %s' % outfits)
        tmphdu.writeto(outfits, overwrite=True)

        """ Create an output text file if requested """
        if outtext is not None:
            print('Creating kinematics data file %s' % outtext)
            f = open(outtext, 'w')
            f.write('#Cube\n')
            f.write('nch %d\n' % tmp2.shape[0])
            f.write('ctype wave\n')
            f.write('cunit angstrom\n')
            f.write('cd3 %f\n' % hdr['cdelt3'])
            f.write('cv3 %f\n' % hdr['crval3'])
            f.write('crpix3 %d\n' % hdr['crpix3'])
            f.write('crota %7.2f\n' % self.impa)
            f.close()

        """ Clean up before exiting """
        del(tmp, tmphdu)
