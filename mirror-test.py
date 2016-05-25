# sstate mirror test for Ostro
#
# Copyright (C) 2016 Intel Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import argparse
import subprocess
import itertools
import sys
import os
import signal
import logging

logger = logging.getLogger('mirror-test')
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser()

parser.add_argument("--numthreads", default="8", type=int,
                    help="number of simultaneous downloads")
parser.add_argument("--mirror",
                    default="http://download.ostroproject.org/sstate/ostro-os/",
                    help="url of the mirror")
parser.add_argument("--logfile",
                    default="mirror-test.log",
                    help="Log file to write to")
parser.add_argument("filelist", help="list of files to download")
parser.add_argument("dldir", help="directory to contain downloaded files")

args = parser.parse_args()

if not os.path.exists(args.dldir):
    os.mkdir(args.dldir)

# Just launches the wget and returns the pid
def wget(mirror, filepath, destdir):
    filename = os.path.join(destdir, os.path.basename(filepath))
    if os.path.exists(filename):
        os.remove(filename)

    url = mirror + '/' + filepath
    cmd = ('wget -t 2 -T 30 -nv --passive-ftp '
           '--no-check-certificate -P {} {}')
    cmd = cmd.format(destdir, url).split()
    
    p = subprocess.Popen(cmd)
    return p.pid

def next_wget(iterator, mirror, dldir):
    filepath = iterator.next()
    filename = os.path.join(dldir, os.path.basename(filepath))

    pid = wget(mirror, filepath, dldir)
    return (pid, filename)

# Create the circular list from the filelist file
with open(args.filelist) as f:
    filelist = [x.strip() for x in f.readlines()]
filelist = itertools.cycle(filelist)

sh = logging.FileHandler(args.logfile)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
sh.setFormatter(formatter)
logger.addHandler(sh)
sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s: %(message)s')
sh.setFormatter(formatter)
logger.addHandler(sh)
logger.info('Mirror test started for %s' % args.mirror)

# Start n wget and know that if we only start a new one each time one finishes
# we will never hit more than n
pids = {}
for i in range(args.numthreads):
    (pid, filename) = next_wget(filelist, args.mirror, args.dldir)
    pids[pid] = filename

totalfailures = 0
runcleanup = False
# Since the wget fetcher says wget will sometimes exit successfully even though
# it failed, mimic it and verify the file actually exists even on success.
try:
    while True:
        (pid, exitcode, res) = os.wait3(0)
        filename = pids.pop(pid)
    
        if exitcode != 0:
            totalfailures += 1
            print '\n'
            logger.error('wget exited with "{}" for file "{}"'.format(exitcode,
                                                            filename))
            print 'total failures: {}\n\n'.format(totalfailures)
    
        elif not os.path.exists(filename):
            totalfailures += 1
            print '\n'
            logger.error('wget failed for file "{}"'.format(filename))
            print 'total failures: {}\n\n'.format(totalfailures)
    
        (pid, filename) = next_wget(filelist, args.mirror, args.dldir)
        pids[pid] = filename
except KeyboardInterrupt:
    print '\n'
    logger.info('Interrupted - total failures: {}'.format(totalfailures))
    runcleanup = True

if runcleanup:
    # kill remaining children and wait for them
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

        try:
            os.waitpid(pid, 0)
        except OSError:
            pass
