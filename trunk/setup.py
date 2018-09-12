from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
from os import sys
import os
import re

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']


from imp import find_module
try:
    find_module('numpy')
except ImportError:
    sys.exit('### Error: python module numpy not found')
    
try:
    find_module('scipy')
except ImportError:
    sys.exit('### Error: python module scipy not found')
    
try:
    find_module('astropy')
except ImportError:
    sys.exit('### Error: Neither astropy nor pyfits found.')

try:
    find_module('matplotlib')
except ImportError:
    sys.exit('### Error: python module matplotlib not found')

try:
    find_module('CDFutils')
except ImportError:
    sys.exit('### Error: python module CDFutils not found. '
             'Download and install from github cdfassnacht/CDFutils')


#try: find_module('MySQLdb')
#except: sys.exit('### Error: python module MySQLdb not found')


verstr = "unknown"
try:
    parentdir = os.getcwd()+'/'
    verstrline = open(parentdir+'/src/_version.py', "rt").read()
except EnvironmentError:
    pass # Okay, there is no version file.
else:
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
    else:
        raise RuntimeError("unable to find version in " + parentdir + "+src/agnkey/_version.py")


setup(
    name = 'KeckCode',
    version = verstr,
    author = 'Chris Fassnacht',
    author_email = 'cdfassnacht@ucdavis.edu',
    scripts=[],
    #url = 'lcogt.net',
    license = 'LICENSE.txt',
    description = 'Code for analyzing data from various Keck instruments',
    long_description = open('README.txt').read(),
    requires = ['numpy','scipy','astropy','matplotlib'],
    packages = ['esi_redux', 'osiris'],
    package_dir = {'':'src'},
    package_data = {'esi_redux' : ['data/*']}
)