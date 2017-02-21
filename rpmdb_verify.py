#!/usr/bin/env python2

#  Copyright (c) 2017-present, Facebook, Inc.
#  All rights reserved.
#
#  This source code is licensed under the BSD-style license found in the
#  LICENSE file in the root directory of this source tree. An additional grant
#  of patent rights can be found in the PATENTS file in the same directory.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import rpm
import logging
import shlex
import os
import sys
import yum
import subprocess

# Mask output codes so we can report failure by type if needed
health_code = {
    'OK': 0x0,
    'GENERAL_PYTHON_FAILURE': 0x1,
    'GENERAL_CHECK_FAILURE': 0x2,
    'RPM_BAD_TRANSACTION_SET': 0x4,
    'RPM_BAD_DB_ENTRY': 0x8,
    'RPM_YUM_CHECK_DEPENDENCIES_FAILURE': 0x10,
    'RPM_YUM_CHECK_OBSOLETED_FAILURE': 0x20,
    'RPM_YUM_CHECK_PROVIDES_FAILURE': 0x40,
    'RPM_YUM_CHECK_DUPLICATES_FAILURE': 0x80,
    'YUM_BUILD_TRANSACTION_FAILURE': 0x100,
    'RPM_GENERAL_FAILURE': 0x200,
    'YUM_GENERAL_FAILURE': 0x400,
}


class RPMDBPackageSack(object):

    def __init__(self):
        self.sack = yum.rpmsack.RPMDBPackageSack()

    def check_dependencies(self):
        if self.sack.check_dependencies():
            return health_code['RPM_YUM_CHECK_DEPENDENCIES_FAILURE']
        return health_code['OK']

    def check_obsoleted(self):
        if self.sack.check_obsoleted():
            return health_code['RPM_YUM_CHECK_OBSOLETED_FAILURE']
        return health_code['OK']

    def check_provides(self):
        if self.sack.check_provides():
            return health_code['RPM_YUM_CHECK_PROVIDES_FAILURE']
        return health_code['OK']

    def check_duplicates(self):
        if self.sack.check_duplicates():
            return health_code['RPM_YUM_CHECK_DUPLICATES_FAILURE']
        return health_code['OK']


class RPMDB(object):

    def verify_transaction_set(self):
        try:
            transaction_set = rpm.TransactionSet()
            # Verify structure of db is valid
            rc = transaction_set.verifyDB()
            # Verify entries are intact
            if rc != 0 or transaction_set.check() or transaction_set.problems():
                return health_code['RPM_BAD_TRANSACTION_SET']
        except rpm._rpm.error:
            return health_code['RPM_BAD_TRANSACTION_SET']

        return health_code['OK']

    def verify_entries(self):
        try:
            transaction_set = rpm.TransactionSet()
            # Ensure each entry is readable
            transaction_set.dbMatch()
        except rpm._rpm.error:
            return health_code['RPM_BAD_DB_ENTRY']

        return health_code['OK']

    def check_rpm_stderr(self):
        '''
        Berkeley DB sometimes prints to stderr if there's a problem with the
        rpmdb. Unfortunately, BDB reports 'all clear' to rpm even if
        there's a DB issue. The easiest way to check for errors this way is to
        look if anything was printed to stderr. If there is, then we know
        something is wrong with the DB.
        '''
        cmd = shlex.split('rpm --query --all --verify --quiet')
        with open(os.devnull, 'w') as devnull:
            proc = subprocess.Popen(
                cmd, stdout=devnull, stderr=subprocess.PIPE)

        # Ignore stdout since we direct to /dev/null in Popen.
        stdout, stderr = proc.communicate()
        if stderr:
            return health_code['RPM_GENERAL_FAILURE']

        return health_code['OK']


class YumDB(object):

    def __init__(self):
        self.base = yum.YumBase()

    def build_transaction(self):
        result_code, _ = self.base.buildTransaction()
        if result_code:
            return health_code['YUM_BUILD_TRANSACTION_FAILURE']
        return health_code['OK']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-q',
        '--quiet',
        help='Only print status code',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '-f',
        '--fast',
        help='Only run fast checks',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '-s',
        '--skip-check',
        help='Skip check by method name',
        action='append',
        dest='skipped_checks',
        default=[],
    )
    args = parser.parse_args()

    log_format = ("[%(levelname)8s] %(message)s")
    logging.basicConfig(format=log_format, level=logging.INFO)

    # Disable logging if --quiet passed. Also disable stderr because Berkeley DB
    # logs to stderr from many of the calls in this script.
    if args.quiet:
        logging.disable(logging.CRITICAL)

    rpmdb = RPMDB()
    yumdb = YumDB()
    sack = RPMDBPackageSack()

    slow_checks = [
        rpmdb.check_rpm_stderr,
    ]

    checks = [
        rpmdb.verify_transaction_set,
        rpmdb.verify_entries,
        yumdb.build_transaction,
        sack.check_dependencies,
        sack.check_duplicates,
        sack.check_obsoleted,
        sack.check_provides,
    ]

    checks = [check for check in checks
              if check.__name__ not in args.skipped_checks]

    if not args.fast:
        checks.extend(slow_checks)

    # Bitwise OR check return values
    exit_code = 0
    for check in checks:
        return_code = 0
        try:
            return_code = check()
        except Exception as e:
            logging.error('check %s raised an exception: %s',
                          check.__name__, e)
            return_code = health_code['GENERAL_CHECK_FAILURE']

        rc_to_str = [key for key, value in health_code.items()
                     if value == return_code]
        logging.info(
            '%16s %25s: %10s', check.im_class.__name__, check.__name__,
            rc_to_str[0]
        )

        exit_code |= return_code

    return exit_code


if __name__ == '__main__':
    exit_code = main()
    print('{:016b}'.format(exit_code))
    sys.exit(1 if exit_code else 0)
