#!/usr/bin/python36

from __future__ import print_function
import glob

class mpath_device_simple(object):
    def __init__(self,attributes, debug=False):
        self.attributes = attributes
        self.debug = debug
        if self.debug: print('mpath simple class in debug mode')

        if self.attributes['dm_name'] is None or len(self.attributes) == 0:
            print("attempted to create an mpath device without unique identifier dm_name")
            exit(1)
        if self.attributes['dm_name'] != 'default':
            self.get_ancestors(str(self.attributes['dm_name']))


    def get_ancestors(self, child):
        if 'dm' in child:
            with open('/sys/block/' + child + '/dm/name', 'r') as f:
                name = f.read().strip()
            if 'mpath' in name and '1' not in name:
                self.attributes['mpath_name'] = name
            if 'mpath' in name and '1' in name:
                self.attributes['dm_partition'] = child
                self.attributes['dm_partition_name'] = name
        elif 'md' in child:
            self.attributes['md_parent'] = child
        parents = glob.glob('/sys/block/' + child + '/holders/*')
        if len(parents) != 0:
            parent = parents[0].split('/')[-1]
            self.get_ancestors(parent)
        return


