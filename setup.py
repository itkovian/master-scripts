#!/usr/bin/env python
# -*- coding: latin-1 -*-
##
# Copyright 2009-2013 Ghent University
#
# Copyright 2009-2012 Ghent University
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# All rights reserved.
#
##
"""Basic setup.py for master scripts"""

from distutils.core import setup

import vsc.install.shared_setup as shared_setup
from vsc.install.shared_setup import ag, sdw, wdp, kh

def remove_bdist_rpm_source_file():
    """List of files to remove from the (source) RPM."""
    return ['lib/vsc/__init__.py', 'lib/vsc/utils/__init__.py']

shared_setup.remove_extra_bdist_rpm_files = remove_bdist_rpm_source_file
shared_setup.SHARED_TARGET.update({
    'url': 'https://github.ugent.be/hpcugent/master-scripts',
    'download_url': 'https://github.ugent.be/hpcugent/master-scripts',
})

PACKAGE = {
    'name': 'master_scripts',
    'version': '1.6',
    'author': [ag, kh, sdw, wdp],
    'description': 'UGent HPC scripts that should be deployed on the masters',
    'license': 'LGPL',
    'packages': ['vsc', 'vsc.utils'],
    'scripts': ['bin/dcheckjob.py', 'bin/pbs_check_inactive_user_jobs.py', 'bin/dshowq.py', 'bin/quota_check_user_notification.py'],
    'install_requires': [
        'python-vsc-administration >= 0.4',
        'python-vsc-base >= 1.2',
        'python-vsc-config',
        'python-lockfile',
        'python-vsc-ldap',
        'python-vsc-ldap-extension',
        'pbs_python >= 4.3',
        'python-vsc-filesystems',
        'python-vsc-jobs',
        'netifaces',
    ]
}


if __name__ == '__main__':
    shared_setup.action_target(PACKAGE)
