#!/usr/bin/python36

import os, glob, subprocess, re

class sd_device(object):
    def __init__(self, system_path, debug=False, solo=True,slot='Unknown',index='Unknown',dm_parent=None,mpath_parent=None,md_parent=None,dm_part=None,dm_part_name=None, enclosure_scsi_address='Unknown'):
        self.sys_path = system_path
        self.debug = debug
        if self.debug: print('sd_device class in debug mode')
        self.name = self.sys_path.split('/')[-1]
        self.attributes = {}
        self.major_minor_num = 'FAIL SD'
        self.sas_address = 'FAIL SD'
        self.parent = None
        self.index = index
        self.slot_num = slot
        self.ancestors = {'dm_parent':dm_parent, 'mpath_parent':mpath_parent, 'md_parent':md_parent, 'dm_part':dm_part, 'dm_part_name':dm_part_name,'enclosure_scsi_address':enclosure_scsi_address}
        self.ses_attrs = {'status':None,'ident':None, 'slot_num':str(slot), 'index_num':str(index)}#Holds status information derived from sg_ses by slot number
        self.smart_attrs = {'model_family':None, 'model':None, 'serial_number':None, 'firmware_version':None, 'capacity':None, 'rotation_rate':None}#holds information derived from smartctl -i /dev/sd*
        self.chassis_id = ''
        self.solo = solo
        self.populate_info()
        self.get_parents2(self.name)
        self.combine_attributes()

    def combine_attributes(self):
        self.attributes = {'sd_name': self.name, 'sas_address': self.sas_address}
        self.attributes.update(self.ses_attrs)
        self.attributes.update(self.smart_attrs)

    def get_parents2(self, child):
        if 'sd' in child:
            self.ancestors['base'] = child
        elif 'dm' in child:
            with open('/sys/block/'+child+'/dm/name','r') as f:
                name = f.read().strip()
            if 'mpath' in name and '1' not in name:
                self.ancestors['dm_parent'] = child
                if self.debug: print("I am sd device: ",self.ancestors['base']," recording my dm parent as ", self.ancestors['dm_parent'])
                self.ancestors['mpath_parent'] = name
            if 'mpath' in name and '1' in name:
                self.ancestors['dm_part'] = child
                if self.debug: print("I am sd device: ", self.ancestors['base'], " recording my dm part as ", self.ancestors['dm_part'])
                self.ancestors['dm_part_name'] = name
        elif 'md' in child:
            self.ancestors['md_parent'] = child
            if self.debug: print("I am sd device: ", self.ancestors['base'], " recording my md_parent as ", self.ancestors['md_parent'])
        parents = glob.glob('/sys/block/'+child+'/holders/*')
        if len(parents) != 0:
            parent = parents[0].split('/')[-1]
            self.get_parents2(parent)
        return

    def populate_info(self):

        try:
            my_enclosure_scsi_start = ''
            print('sd test 1')
            with open(self.sys_path + '/dev', 'r') as f:
                print('sd test 2')
                self.major_minor_num = f.readline().strip()
                print('sd test 3')
            print('sd test 4')
            for line in os.listdir(self.sys_path + '/device/scsi_disk'):
                print('sd test 5')
                my_enclosure_scsi_start = str(line.split(':')[0])
                print('sd test 6')
            encl = glob.glob('/sys/class/enclosure/' + my_enclosure_scsi_start + '*')[0]  # get the enclosure scsi ID that matches the first octet of the scsi ID of the drive in question. This is the IO module through which the OS sees this physical disk. We use this to compare SAS addresses later to determine slot numbers.
            print('sd test 7')
            with open(encl + '/id', 'r') as f:
                print('sd test 8')
                self.chassis_id = f.readline().lstrip('0x').strip()
                print('sd test 9')
            with open(self.sys_path+'/device/sas_address') as f:
                print('sd test 10')
                self.sas_address = f.readline().lstrip('0x').strip()
                print('sd test 11')
            if self.solo:
                print('sd test 12')
                self.populate_smart_attrs()
                print('sd test 13')

        except Exception as e:
            print("Failed to populate info for " + self.name)
            print(e)
    def populate_smart_attrs(self, attributes=None):
        if attributes is None:
            try:
                cmdargs = ['smartctl', '-i','/dev/' + self.name]  # Using smartctl -i /dev/sd* to harvest smart attribute info and store them in the smart attribute dictionary.
                stdout, stderr = subprocess.Popen(cmdargs,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE).communicate()
                output = stdout.decode("utf-8").splitlines()
                for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
                    # We are using regex expressions to pick out important information for the function to return.
                    mobj = re.search(r'^.*Device Model:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['model'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Model Family:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['model_family'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Serial Number:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['serial_number'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Firmware Version:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['firmware_version'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Capacity:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['capacity'] = mobj.group(1)
                        continue
                    mobj = re.search(r'^.*Rotation Rate:\s*(.*)$', line.strip(),flags=re.IGNORECASE)
                    if (mobj):
                        self.smart_attrs['rotation_rate'] = mobj.group(1)
                        continue
                return self.smart_attrs
            except Exception as e:
                print("An error has occurred trying to populate smart attributes in this sd device.")
                print(e)
        else:
            self.smart_attrs = attributes

    def find_parent(self): #Must pass a path if called from the class instead of an instantiated object of the class.
        sys_path = self.sys_path
        holders = os.listdir(sys_path+'/holders')
        if len(holders) != 0:
            self.parent = holders[0]
        else:
            if self.debug: print("The sd device ", sys_path, " has no parent")

class sd_device_simple(object):
    def __init__(self, debug=False, attributes={'sd_name':None,'serial_number':None}):
        self.attributes = attributes
        self.debug = debug
        if self.debug: print('sd device simple class is in debug mode')
        if attributes['sd_name'] is None or len(attributes) == 0:
            print("You attempted to create an sd_device without the required sd_name unique identifier. The program has failed")
            exit(1)

    def find_additional_sd_info(self):

        pass

