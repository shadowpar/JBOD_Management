#!/usr/bin/python36

import os, subprocess, re, glob
import random
from pathlib import Path

class scsi_disk(object):
    def __init__(self,attributes,debug=False,quick_scan=False):
        self.attributes = attributes
        self.quick_scan = quick_scan
        self.debug = debug
        self.hba_port_path = ''
        if self.debug: print('I am trying to gatther attributes for ', self.attributes['device_path'])
        self.scsi_addr = self.attributes['device_path'].split('/')[-1]
        self.scsi_addr = self.attributes['device_path'].split('/')[-1]
        self.hba_addr = self.scsi_addr.split(':')[0]
        if 'device_path' not in self.attributes:
            print('Unable to create scsi_disk object, no valid path given')
        if os.path.isdir(self.attributes['device_path']):
            self.gather_attributes()
            self.get_port_path()


    def get_port_path(self):
        full_path = Path(self.attributes['device_path']).resolve()
        mobj = re.search(r'^(.*/host[0-9]+/port-[^/]+)/.*', str(full_path), flags=re.IGNORECASE)
        if mobj:
            if self.debug:print('I am the enclosure',self.attributes['device_path'])
            port_path = mobj.group(1)
            if self.debug:print('I have found the port path',port_path)
            self.hba_port_path = port_path
        else:
            if self.debug: print('I was unable to find a system path with a port ',self.attributes['device_path'])
            mobj = re.search(r'^(.*/host[0-9]+)/.*', str(full_path), flags=re.IGNORECASE)
            if mobj:
                if self.debug: print('I am the raid controller', self.attributes['device_path'])
                hba_port_path = mobj.group(1)
                if self.debug: print('I have found the hba path', hba_port_path)
                self.hba_port_path = hba_port_path
            else:
                print('I was unable to find hba path or hba port path. I must be attached to a device that is not enclosure or hardware raid controller', self.attributes['device_path'])
                exit(1)


    def gather_attributes(self):
        if self.debug: print('I am trying to gatther attributes for ',self.attributes['device_path'])

        try:
            self.attributes['sd_name'] = os.listdir(self.attributes['device_path']+'/block')[0]
        except IndexError as e:
            print('I failed to find the block sd name for:',self.attributes['device_path'])
            print('This scsi_disk class relies on this to function.')
            exit(1)

        try:
            block_files = os.listdir(self.attributes['device_path']+'/block/'+self.attributes['sd_name'])
            for file in block_files:
                if self.attributes['sd_name'] in file:
                    self.attributes['partition_dev_name'] = file
        except IndexError as e:
            print('I failed to find the partition dev name for:',self.attributes['device_path'])
            self.attributes['partition_dev_name'] = 'unknown'
        except Exception as e:
            self.attributes['partition_dev_name'] = 'unknown'
            print(e)

        try:
            with open(self.attributes['device_path']+'/block/'+self.attributes['sd_name']+'/dev') as f:
                self.attributes['major_minor_num'] = str(f.read().strip())
        except FileNotFoundError as e:
            print('I failed to find the dev file for major_minor_num from ',self.attributes['sd_name'])
            self.attributes['major_minor_num'] = 'unknown'
        except Exception as e:
            self.attributes['major_minor_num'] = 'unknown'
            print(e)

        try:
            with open(self.attributes['device_path']+'/vendor','r') as f:
                self.attributes['vendor'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a vendor name for:',self.attributes['device_path'])
            self.attributes['vendor'] = 'unknown'
        except Exception as e:
            self.attributes['vendor'] = 'unknown'
            print(e)

        try:
            with open(self.attributes['device_path']+'/model','r') as f:
                self.attributes['model'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a model name for:',self.attributes['device_path'])
            self.attributes['model'] = 'unknown'
        except Exception as e:
            self.attributes['model'] = 'unknown'
            print(e)

        try:
            with open(self.attributes['device_path']+'/sas_address','r') as f:
                self.attributes['sas_address'] = f.read().lstrip('0x').strip()
        except FileNotFoundError as e:
            print('I failed to find a sas_address for:',self.attributes['device_path'])
            self.attributes['sas_address'] = 'default'
        except Exception as e:
            self.attributes['sas_address'] = 'default'
            print(e)

        try:
            with open(self.attributes['device_path']+'/state','r') as f:
                self.attributes['state'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a state for:',self.attributes['device_path'])
            self.attributes['state'] = 'unknown'
        except Exception as e:
            self.attributes['state'] = 'unknown'
            print(e)

        self.get_parents(self.attributes['sd_name'])
        if 'dm_parent' not in self.attributes:
            self.attributes['dm_parent'] = 'default'
        if 'md_parent' not in self.attributes:
            self.attributes['md_parent'] = 'default'
        if self.quick_scan is False:
            self.populate_smart_attrs()
        else:
            self.get_serial_num()


    def populate_smart_attrs(self):
        if not self.quick_scan:
            try:
                cmdargs = ['smartctl', '-i','/dev/' + str(self.attributes['sd_name'])]  # Using smartctl -i /dev/sd* to harvest smart attribute info and store them in the smart attribute dictionary.
                stdout, stderr = subprocess.Popen(cmdargs,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE).communicate()
                output = stdout.decode("utf-8").splitlines()
                for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
                    # We are using regex expressions to pick out important information for the function to return.
                    mobj = re.search(r'^.*Device Model:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['model'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Model Family:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['model_family'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Serial Number:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['serial_number'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Firmware Version:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['firmware_version'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Capacity:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['capacity'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Rotation Rate:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.attributes['rotation_rate'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Probable ATA device behind a SAT layer\s*(.*)$', line.strip(), flags=re.IGNORECASE)
                    if (mobj):
                        if self.attributes['dm_parent'] != 'default':
                            unique = self.attributes['dm_parent']
                        else:
                            unique = str(random.randint(1,20000))

                        for data in ['model', 'model_family', 'firmware_version', 'capacity', 'rotation_rate','serial_number']:
                            self.attributes[data] = 'bad_smart_data-'+unique
                        continue

            except Exception as e:
                print("An error has occurred trying to populate smart attributes in this sd device.")
                print(e)
        elif self.quick_scan:
            if self.attributes['dm_parent'] != 'default':
                unique = self.attributes['dm_parent']
            else:
                unique = str(random.randint(1,20000))

            for data in ['model', 'model_family', 'firmware_version', 'capacity', 'rotation_rate','serial_number']:
                self.attributes[data] = 'quick_scan-'+unique
    def get_serial_num(self):
        try:
            cmdargs = ['sg_vpd','-q','-p','sn','/dev/'+str(self.attributes['sd_name'])]
            stdout, stderr = subprocess.Popen(cmdargs,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
            self.attributes['serial_number'] =  str(stdout.decode("utf-8").split()[-1])
        except Exception as e:
            print("There was an error trying to get the serial number for ",self.attributes['sd_name'])
            self.attributes['serial_number'] = None



    def find_enclosure(self,enclosure_set,hardware_raid_set):
        self.attributes['encl_sg_name'] = None
        for name in enclosure_set:
            if enclosure_set[name].hba_port_path == self.hba_port_path:
                if self.attributes['encl_sg_name'] is None:
                    self.attributes['encl_sg_name'] = enclosure_set[name].attributes['encl_sg_name']
                else:
                    print('this sd device',self.attributes['sd_name'],'currently assigned to enclosure',self.attributes['encl_sg_name'])
                    print('This function is trying to reassign to enclosure',enclosure_set[name].attributes['encl_sg_name'])
                    raise(Exception('trying to change the sg name of an sd.'))
                #come up with another way to check the sg name of the disk. scsi address is not enough in the case two plugs in 1 hba.
        for name in hardware_raid_set:
            if hardware_raid_set[name].hba_port_path == self.hba_port_path:
                self.attributes['encl_sg_name'] = None


        if self.attributes['encl_sg_name'] is None:
            self.attributes['encl_sg_name'] = 'default'

    def get_parents(self, child):
        if 'dm-' in child:
            with open('/sys/block/'+child+'/dm/name','r') as f:
                name = f.read().strip()
            if 'mpath' in name and '1' not in name:
                self.attributes['dm_parent'] = child
                if self.debug: print("I am sd device: ",self.attributes['sd_name']," recording my dm parent as ", self.attributes['dm_parent'])
        elif 'md' in child:
            self.attributes['md_parent'] = child
            if self.debug: print("I am sd device: ", self.attributes['sd_name'], " recording my md_parent as ", self.attributes['md_parent'])
        parents = glob.glob('/sys/block/'+child+'/holders/*')
        if len(parents) != 0:
            parent = parents[0].split('/')[-1]
            self.get_parents(parent)
        return