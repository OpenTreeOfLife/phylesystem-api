#!/usr/bin/env python
import sys
import os
# setup.py largely based on
#   http://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
# Also see Jeet Sukumaran's DendroPy

###############################################################################
# setuptools/distutils/etc. import and configuration
try:
    import ez_setup
    try:
        ez_setup_path = " ('" + os.path.abspath(ez_setup.__file__) + "')"
    except OSError:
        ez_setup_path = ""
    sys.stderr.write("using ez_setup%s\n" %  ez_setup_path)
    ez_setup.use_setuptools()
    import setuptools
    try:
        setuptools_path = " ('" +  os.path.abspath(setuptools.__file__) + "')"
    except OSError:
        setuptools_path = ""
    sys.stderr.write("using setuptools%s\n" % setuptools_path)
    from setuptools import setup, find_packages
except ImportError, e:
    sys.stderr.write("using distutils\n")
    from distutils.core import setup
    EXTRA_KWARGS = {}
else:
    EXTRA_KWARGS = dict(
        install_requires = ['setuptools'],
    )
EXTRA_KWARGS["zip_safe"] = True

c = 'Configuration file needed to be used across web2py apps in OpenTreeOfLife'
setup(
    name='celeryconfig',
    version='0.0.0a',
    description=c,
    long_description=c,
    url='https://github.com/OpenTreeOfLife',
    license='BSD',
    author='Mark T. Holder and Celery documentation',
    py_modules=['celeryconfig', 'open_tree_tasks'],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
    **EXTRA_KWARGS
)