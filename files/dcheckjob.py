#!/usr/bin/python
##
#
# Copyright 2013-2013 Ghent University
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
##
"""
dcheckjob.py requests all idle (blocked) jobs from Moab and stores the result in a JSON structure in each
users pickle directory.

@author Andy Georges
"""
import os
import sys
import time

import vsc.utils.fs_store as store
from vsc import fancylogger
from vsc.administration.user import MukUser
from vsc.jobs.moab.checkjob import Checkjob, CheckjobInfo
from vsc.utils.fs_store import UserStorageError, FileStoreError, FileMoveError
from vsc.utils.generaloption import simple_option
from vsc.utils.lock import lock_or_bork, release_or_bork
from vsc.utils.nagios import NagiosReporter, NagiosResult, NAGIOS_EXIT_OK
from vsc.utils.timestamp_pid_lockfile import TimestampedPidLockfile

#Constants
NAGIOS_CHECK_FILENAME = '/var/log/pickles/dcheckjob.nagios.pickle'
NAGIOS_HEADER = 'dcheckjob'
NAGIOS_CHECK_INTERVAL_THRESHOLD = 30 * 60  # 30 minutes

DCHECKJOB_LOCK_FILE = '/var/run/dcheckjob_tpid.lock'

logger = fancylogger.getLogger(__name__)
fancylogger.logToScreen(True)
fancylogger.setLogLevelInfo()


def get_pickle_path(location, user_id):
    """Determine the path (directory) where the pickle file qith the queue information should be stored.

    @type location: string
    @type user_id: string

    @param location: indication of the user accesible storage spot to use, e.g., home or scratch
    @param user_id: VSC user ID

    @returns: tuple of (string representing the directory where the pickle file should be stored,
                        the relevant storing function in vsc.utils.fs_store).
    """
    if location == 'home':
        return ('.showq.pickle', store.store_pickle_data_at_user_home)
    elif location == 'scratch':
        return (os.path.join(MukUser(user_id).pickle_path(), '.showq.pickle'), store.store_pickle_data_at_user)


def main():
    # Collect all info

    # Note: debug option is provided by generaloption
    # Note: other settings, e.g., ofr each cluster will be obtained from the configuration file
    options = {
        'nagios': ('print out nagios information', None, 'store_true', False, 'n'),
        'nagios_check_filename': ('filename of where the nagios check data is stored', str, 'store', NAGIOS_CHECK_FILENAME),
        'nagios_check_interval_threshold': ('threshold of nagios checks timing out', None, 'store', NAGIOS_CHECK_INTERVAL_THRESHOLD),
        'hosts': ('the hosts/clusters that should be contacted for job information', None, 'extend', []),
        'checkjob_path': ('the path to the real shpw executable',  None, 'store', ''),
        'location': ('the location for storing the pickle file: home, scratch', str, 'store', 'home'),
        'dry-run': ('do not make any updates whatsoever', None, 'store_true', False),
    }

    opts = simple_option(options)

    if opts.options.debug:
        fancylogger.setLogLevelDebug()

    nagios_reporter = NagiosReporter(NAGIOS_HEADER,
                                     opts.options.nagios_check_filename,
                                     opts.options.nagios_check_interval_threshold)
    if opts.options.nagios:
        logger.debug("Producing Nagios report and exiting.")
        nagios_reporter.report_and_exit()
        sys.exit(0)  # not reached

    lockfile = TimestampedPidLockfile(DCHECKJOB_LOCK_FILE)
    lock_or_bork(lockfile, nagios_reporter)

    tf = "%Y-%m-%d %H:%M:%S"

    logger.info("checkjob.py start time: %s" % time.strftime(tf, time.localtime(time.time())))

    clusters = {}
    for host in opts.options.hosts:
        master = opts.configfile_parser.get(host, "master")
        showq_path = opts.configfile_parser.get(host, "showq_path")
        clusters[host] = {
            'master': master,
            'path': showq_path
        }

    checkjob = Checkjob(clusters, opts.options.dry_run, cache_pickle=True)

    (job_information, reported_hosts, failed_hosts) = checkjob(opts)
    timeinfo = time.time()

    active_users = job_information.keys()

    logger.debug("Active users: %s" % (active_users))
    logger.debug("Checkjob information: %s" % (job_information))

    nagios_user_count = 0
    nagios_no_store = 0

    for user in active_users:
        if not opts.options.dry_run:
            try:
                (path, store) = get_pickle_path(opts.options.location, user)
                user_queue_information = CheckjobInfo({user: job_information[user]})
                store(user, path, (timeinfo, user_queue_information))
                nagios_user_count += 1
            except (UserStorageError, FileStoreError, FileMoveError), _:
                logger.error("Could not store pickle file for user %s" % (user))
                nagios_no_store += 1
        else:
            logger.info("Dry run, not actually storing data for user %s at path %s" % (user, get_pickle_path(opts.options.location, user)[0]))
            logger.debug("Dry run, queue information for user %s is %s" % (user, job_information[user]))

    logger.info("dcheckjob.py end time: %s" % time.strftime(tf, time.localtime(time.time())))

    #FIXME: this still looks fugly
    bork_result = NagiosResult("lock release failed",
                               hosts=len(reported_hosts),
                               hosts_critical=len(failed_hosts),
                               stored=nagios_user_count,
                               stored_critical=nagios_no_store)
    release_or_bork(lockfile, nagios_reporter, bork_result)

    nagios_reporter.cache(NAGIOS_EXIT_OK,
                          NagiosResult("run successful",
                                       hosts=len(reported_hosts),
                                       hosts_critical=len(failed_hosts),
                                       stored=nagios_user_count,
                                       stored_critical=nagios_no_store))

    sys.exit(0)

if __name__ == '__main__':
    main()
