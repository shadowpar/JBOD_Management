#!/usr/bin/python36

from pathlib import Path
import re, os


class hardware_raid_simple(object):
    def __init__(self,attributes,debug=False):
        self.debug = debug
        self.attributes = attributes
        self.hba_port_path = ''
        self.hba_path = ''
        self.gather_attributes()
        self.get_port_path()

    def get_port_path(self):
        if self.debug: print('------entering get port path function inside encl_simple_Device class')
        full_path = Path(self.attributes['device_path']).resolve()
        if self.debug:print("Full path for encl_simple is",full_path)
        mobj = re.search(r'^(.*/host[0-9])+/.*',str(full_path),flags=re.IGNORECASE)
        if mobj:
            if self.debug: print('I am the enclosure',self.attributes['device_path'])
            hba_path = mobj.group(1)
            if self.debug: print('I have found the hba path',hba_path)
            self.hba_path = hba_path

        mobj = re.search(r'^(.*/host[0-9]+/port-[^/]+)/.*', str(full_path), flags=re.IGNORECASE)
        if mobj:
            if self.debug: print('I am the enclosure',self.attributes['device_path'])
            port_path = mobj.group(1)
            if self.debug: print('I have found the hba port path',port_path)
            self.hba_port_path = port_path
        else:
            print('I was unable to find port path for ',self.attributes['device_path'])
            exit(1)
        if self.debug:
            print('------leaving get port path function inside encl_simple_Device class',self.hba_port_path)
    def gather_attributes(self):
        try:
            self.attributes['raid_sg_name'] = os.listdir(self.attributes['device_path']+'/scsi_generic')[0]
        except IndexError as e:
            print('I failed to find a generic scsi name for:',self.attributes['device_path'])
            print('This hardware raid simple class relies on the scsi generic name to function.')
            print(e)
            exit(1)