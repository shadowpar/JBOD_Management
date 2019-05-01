#!/usr/bin/python36

from __future__ import print_function
import os, os.path, subprocess, re


class md_device_simple(object):
    def __init__(self,attributes,debug=False):
        self.attributes = attributes
        self.debug = debug
        if 'md_name' not in self.attributes:
            print('Failed to create md device')
            exit(1)
        self.name = str(self.attributes['md_name'])
        self.current_devices = []
        if not self.attributes['md_name'] == 'default': self.parse_mdadm_detail()

    def parse_mdadm_detail(self):
        try:
            command = ["mdadm","-D","/dev/"+self.name]
            stdout, stderr = subprocess.Popen(command,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE).communicate()
            output = stdout.decode("utf-8").splitlines()


            for line in output:
                mobj = re.search(r'^.*State\s*:\s*([a-zA-Z]+).*', line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_status'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Raid Level\s*:\s*(raid[0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_raid_level'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Raid Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_raid_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Total Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_present_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Active Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_active_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Working Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_working_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Failed Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_failed_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*Spare Devices\s*:\s*([0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.attributes['md_spare_devices'] = mobj.group(1).strip()

                mobj = re.search(r'^.*/dev/(dm-[0-9]+).*',line,flags=re.IGNORECASE)
                if mobj:
                    self.current_devices.append(mobj.group(1).strip())
        except Exception as e:
            print('There was a problem parsing mdadm_detail for this device:',self.name)
            print(e)
        device_status_list = ''
        try:
            for device in self.current_devices:
                if os.path.isfile('/sys/block/'+str(self.name)+'/md/dev-'+str(device)+'/state'):
                    with open('/sys/block/'+str(self.name)+'/md/dev-'+str(device)+'/state') as f:
                        state = f.read().strip()
                        device_status_list += str(device)+':'+str(state)+','
        except Exception as e:
            print('Failed to look at status for one of the devices in',self.name)
        self.attributes['md_device_status_list'] = device_status_list
        self.check_mounts()

    def check_mounts(self):
        if self.debug:print('inside check mounts for ',self.attributes['md_name'])
        for line in open('/proc/mounts','r'):
            if self.debug:print(line)
            if '/dev/'+str(self.attributes['md_name']) in line:
                data = line.split(' ')
                if len(data) < 4:
                    print('Something is wrong with the mount lookup for ',self.attributes['md_name'])
                    print(line)
                    exit(1)
                if self.debug:print(data[1])
                if self.debug:print(data[2])
                self.attributes['md_mount_point'] = str(data[1])
                self.attributes['md_filesystem'] = str(data[2])
                if self.debug:print('sucessfully stored data1 and data2')
                cmdargs = ['df', '-h']
                stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                output = stdout.decode("utf-8").splitlines()
                for line2 in output: # We are using regex expressions to pick out important information for the function to return.
                    mobj = re.search(r'^.*' + str(self.attributes['md_name']) + '\s+([0-9bBmMgGtTpP]+)\s+([0-9bBmMgGtTpP]+)\s+([0-9bBmMgGtTpP]+)\s+.*' +
                                     self.attributes['md_mount_point'] + '.*', line2, flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['md_size'] = mobj.group(1)
                        self.attributes['md_used'] = mobj.group(2)
                        self.attributes['md_free'] = mobj.group(3)
        if 'md_mount_point' not in self.attributes:
            self.attributes['md_mount_point'] = 'not mounted'
            self.attributes['md_filesystem'] = 'not mounted'
            self.attributes['md_size'] = 'not mounted'
            self.attributes['md_used'] = 'not mounted'
            self.attributes['md_free'] = 'not mounted'

