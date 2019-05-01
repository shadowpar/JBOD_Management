#!/usr/bin/python36

import os, subprocess, re
from pathlib import Path
class encl_serv_dev_simple(object):
    def __init__(self,debug=False,attributes={'device_path':'default','sas_address':None}):
        self.attributes = attributes
        self.debug = debug
        self.scsi_addr = self.attributes['device_path'].split('/')[-1]
        self.hba_path = ''
        self.hba_port_path = ''
        self.sas_slot_map = {}
        self.expander_addresses = []
        if 'device_path' not in self.attributes:
            print('Unable to create scsi_disk object, no valid path given')
            exit(1)
        if os.path.isdir(self.attributes['device_path']):
            self.gather_attributes()
            self.create_sas_slot_mapping()
            self.get_port_path()

    def gather_attributes(self):
        try:
            self.attributes['encl_sg_name'] = os.listdir(self.attributes['device_path']+'/scsi_generic')[0]
        except IndexError as e:
            print('I failed to find a generic scsi name for:',self.attributes['device_path'])
            print('This encl_serv_dev_simple class relies on the scsi generic name to function.')
            print(e)
            exit(1)
        try:
            with open(self.attributes['device_path']+'/vendor','r') as f:
                self.attributes['vendor'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a vendor name for:',self.attributes['device_path'])
            print(e)
        try:
            with open(self.attributes['device_path']+'/model','r') as f:
                self.attributes['model'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a model name for:',self.attributes['device_path'])
            print(e)
        try:
            with open(self.attributes['device_path']+'/sas_address','r') as f:
                self.attributes['sas_address'] = f.read().lstrip('0x').strip()
        except FileNotFoundError as e:
            print('I failed to find a sas_address for:',self.attributes['device_path'])
            self.attributes['sas_address'] = None
            print(e)
        try:
            with open(self.attributes['device_path']+'/state','r') as f:
                self.attributes['state'] = f.read().strip()
        except FileNotFoundError as e:
            print('I failed to find a state for:',self.attributes['device_path'])
            print(e)
        try:
            with open(self.attributes['device_path']+'/enclosure/'+self.scsi_addr+'/id','r') as f:
                self.attributes['wwid'] = f.read().lstrip('0x').strip()
        except FileNotFoundError as e:
            try:
                self.get_wwid_from_sg_ses()
                #print(e)
            except Exception as l:
                print('I was unable to find the wwid in any way for enclosure',self.attributes['device_path'])
                print(l)
                exit(1)
        try:
            with open(self.attributes['device_path']+'/enclosure/'+self.scsi_addr+'/components','r') as f:
                self.attributes['num_slots'] = f.read().strip()
        except FileNotFoundError as e:
            try:
                self.get_slots_from_sg_ses()
                #print(e)
            except Exception as l:
                print('I was unable to find the wwid in any way for enclosure',self.attributes['device_path'])
                print(l)
                exit(1)

    def get_wwid_from_sg_ses(self):
        cmdargs = ['sg_ses','-p','ed','/dev/'+self.attributes['encl_sg_name']]
        stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        output = stdout.decode("utf-8").splitlines()
        for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
            # We are using regex expressions to pick out important information for the function to return.
            mobj = re.search(r'^.*Primary enclosure logical identifier.*:\s*([a-fA-F0-9x]+).*', line, flags=re.IGNORECASE)
            if (mobj):
                self.attributes['wwid'] = str(mobj.group(1).lstrip('0x').strip())  # Pick the slot number out of sg_ses output and map to sas address
                continue

    def get_slots_from_sg_ses(self):
            valid_entry = False #just a flag to tell us we need to read the next line.
            cmdargs = ['sg_ses', '-p', 'cf', '/dev/'+self.attributes['encl_sg_name']]
            stdout, stderr = subprocess.Popen(cmdargs,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE).communicate()
            output = stdout.decode("utf-8").splitlines()
            for line in output:  # parsing the output of sg_ses -p cf /dev/sg*
                # We are using regex expressions to pick out important information for the function to return.
                mobj = re.search(r'^.*Element type: Array device slot', line.strip(),flags=re.IGNORECASE)
                if (mobj):
                    valid_entry = True
                    continue
                mobj = re.search(r'^.*number of possible elements:\s*([0-9]+)', line.strip(),flags=re.IGNORECASE)
                if (mobj):
                    if(valid_entry == True):
                        num_components = int(mobj.group(1))
                        self.attributes['num_slots'] = str(num_components)
                        return

    def create_sas_slot_mapping(self):
        for idx in range(int(self.attributes['num_slots'])):
            try:
                slot_num = ''
                slot_sas_address = ''
                cmdargs = ['sg_ses', '--index=0,' + str(idx), '--join', '/dev/' + self.attributes['encl_sg_name']]
                stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                output = stdout.decode("utf-8").splitlines()
                for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
                    # We are using regex expressions to pick out important information for the function to return.
                    mobj = re.search(r'^\s*SLOT\s*([0-9]{1,3}).*', line,flags=re.IGNORECASE)
                    if (mobj):
                        slot_num = mobj.group(1) .strip() # Pick the slot number out of sg_ses output and map to sas address
                        continue
                    mobj = re.search(r'^\s*SAS address:\s*0x([a-fA-F0-9]{16})\s*', line,flags=re.IGNORECASE)
                    if (mobj):
                        slot_sas_address = mobj.group(1).lstrip('0x').strip()  # Pick the slot number out of sg_ses output and map to sas address
                        continue
                    mobj = re.search(r'^\s*attached SAS address:\s*0x([a-fA-F0-9]{16})\s*', line, flags=re.IGNORECASE)
                    if (mobj):
                        self.expander_addresses.append(mobj.group(1).lstrip('0x').lstrip('0x').strip())  # Pick the slot number out of sg_ses output and map to sas address
                        continue

                self.sas_slot_map[slot_sas_address] = {'index_num': idx, 'slot_num': slot_num}
            except Exception as e:
                print("An error has occurred while building sas_slot map for enclosure: ", self.attributes['encl_sg_name'])
                print(e)
        if self.debug:
            print('I am enclosure', self.attributes['encl_sg_name'])
            print('I have the following SAS addresses stored in my sas map')
            for address in self.sas_slot_map:
                print('sas address',address,'index:',self.sas_slot_map[address]['index_num'])

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

