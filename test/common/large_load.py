#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import optparse
import sys
import time
import logging
import unittest
import os
import fileinput
import random


srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

from pulp.api.repo import RepoApi
from pulp.api.package import PackageApi
from pulp.api.consumer import ConsumerApi
from pulp.model import Package
from pulp.model import Consumer
from pulp.util import random_string
import pulp.util
from testutil import create_package

TEST_PACKAGE_ID = 'random-package'

class LargeLoad(unittest.TestCase):
    
    """
    Util for loading large amounts of data through our API
    """
    def __init__(self, dir_list_path, numconsumers, config):
        self.config = config
        self.rapi = RepoApi(self.config)
        self.papi = PackageApi(self.config)
        self.capi = ConsumerApi(self.config)
        self.numconsumers = numconsumers
        self.dirlist = []
        if (dir_list_path != None):
            for line in fileinput.input(dir_list_path):
                line = line.rstrip()
                self.dirlist.append(line)

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        db = self.rapi.db
        self.rapi.connection.drop_database(db)
        
    def create_repos(self):
        print "RPMDIRS: %s" % self.dirlist
        numrepos = 0
        for rdir in self.dirlist:
            id = rdir.replace('/', '.')
            repo = self.rapi.create(id,'test repo: %s' % rdir, \
                'i386', 'local:file://%s' % rdir)
            self.rapi.sync(repo.id)
            numrepos = numrepos + 1
        
        return numrepos
    
    def add_package(self, consumer, package):
        n = str(package['name'])
        v = str(package['version'])
        r = str(package['release'])
        a = str(package['arch'])
        nevra = '%s-%s-%s-%s' % (n,v,r,a)
        nevra = nevra.replace('.','_')
        consumer.packages[nevra]= package
        
    
    def create_consumers(self):
        last_desc = None
        last_id = None
        repos = self.rapi.repositories()
        consumers = []
        randomPackage = create_package(self.papi, TEST_PACKAGE_ID)
        for i in range(self.numconsumers):
            repo = random.choice(repos)
            c = Consumer(random_string(), random_string())
            packages = repo['packages']
            for p in packages.values():
                # c.packageids.append(p['id'])
                # c.packages.append(p)
                self.add_package(c, p)
            # self.capi.update(c)
            if (i % 100 == 0):
                print "created [%s] consumers" % i
                # c.packageids.append(randomPackage['id'])
                # c.packages.append(randomPackage)
                self.add_package(c, randomPackage)
            last_desc = c.description
            last_id = c.id
            consumers.append(c)
        print "BULK INSERTING size: %s" % str(sys.getsizeof(consumers))
        
        self.capi.bulkcreate(consumers)
        print "Done bulk inserting"
        
        return last_desc, last_id

    
    def find_consumer(self, last_id):
        # Get entire list.  Make sure its not too slow.
        # When we initially were storing the entire package in the 
        # consumer object this call would blow out all the ram on a 8GB box
        consumers = self.capi.consumers()
        c = consumers[0]
        assert(len(consumers) == self.numconsumers)
        randomPackage = random.choice(c['packages'])
        p = ll.papi.package(randomPackage['id'])
        assert(p != None)
        c2 = self.capi.consumer(last_id)
        assert(c2 != None)
        
        print "Searching for all consumers with %s package id" % TEST_PACKAGE_ID
        cwithp = ll.capi.consumers_with_package_name(TEST_PACKAGE_ID)
        print "Found [%s] consumers with packageid: [%s]" % (len(cwithp), TEST_PACKAGE_ID)


parser = optparse.OptionParser()
parser.add_option('--dirlist', dest='dirlist', 
                 action='store', help='File containing list of directories containing the repos you wish to use for this test')
parser.add_option('--numconsumers', dest='numconsumers', 
                 action='store', default=1000, help='Number of consumers you want to load')

parser.add_option('--clean', dest='clean', action='store_true', help='Clean db')
parser.add_option('--config', dest='config', action='store', help='Configuration file', default="../../etc/pulp/pulp.ini")
cmdoptions, args = parser.parse_args()
dirlist = cmdoptions.dirlist
clean = cmdoptions.clean
numconsumers = int(cmdoptions.numconsumers)
print "Attempting to load configuration from: %s" % (cmdoptions.config)
config = pulp.util.load_config(cmdoptions.config)

if (clean):
    ll = LargeLoad(None, None, dict())
    ll.clean()
    exit("cleaned the databases")

if (dirlist == None):
    exit("ERROR: --dirlist <path-to-txt-file> is required.  Specify a txt file with a list of dirs you wish to use.")


console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
# logging.getLogger('pulp.api').addHandler(console)
# logging.getLogger('pulp.api').setLevel(logging.DEBUG)

ll = LargeLoad(dirlist, numconsumers, config)
ll.clean()

numrepos = ll.create_repos()
repos = ll.rapi.repositories()
packages = ll.papi.packages()

print "number of repos: %s" % len(list(repos))
print "number of packages: %s" % len(packages)
last_desc, last_id = ll.create_consumers()
print "Done creating consumers.  Listing all of them"
ll.find_consumer(last_id)
# ll.find_repo()
# ll.find_consumers_with_package()

numpackages = len(ll.papi.packages())
print "Your database now has [%s] repositories with [%s] total packages and [%s] consumers" \
      % (numrepos, numpackages, numconsumers)
           

