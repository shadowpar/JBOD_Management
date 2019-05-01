#!/usr/bin/python36
import os
from jbod_management.jbod_physical_devices.enclosure_services_device import encl_serv_dev_simple
from jbod_management.jbod_physical_devices.scsi_disk import scsi_disk
from jbod_management.kernel_devices.md_device import md_device_simple
from jbod_management.kernel_devices.mpath_device import mpath_device_simple
from jbod_management.jbod_physical_devices.jbod_chassis import jbod_chassis_simple
from jbod_management.jbod_physical_devices.physical_drive import physical_drive_simple
from jbod_management.jbod_physical_devices.hardware_raid import hardware_raid_simple
from pathlib import Path

class scanner_scsi_bus(object):
    def __init__(self,debug=False, sys_path='/sys', quick_scan=False):
        self.debug = debug
        self.debug = False
        self.quick_scan = quick_scan
        if self.debug: print('SCSI scanner class is running in debug mode.')


class scan_scsi_bus(object):
    def __init__(self,debug=False,sys_path='/sys',quick_scan=False):
        self.debug = debug
        self.quick_scan = quick_scan
        if self.debug: print('SCSI scan class is running in debug mode.')
        self.scsi_disks = []
        self.scsi_enclosures = []
        self.hardware_raid = []
        self.simple_sas_enclosures = {}
        self.simple_local_enclosures = {}
        self.simple_scsi_sds = {}
        self.simple_mds = {}
        self.simple_mpaths = {}
        self.simple_chassis = {}
        self.simple_physical_drives = {}
        self.simple_hardware_raid = {}
        self.abandoned_drives = {}
        self.scsi_dev_map = {'0':'Direct-access block device ','1':'Sequential-access device','5':'CD/DVD-ROM device','12':'Storage array controller device','13':'Enclosure services device'}
        self.scsi_path = sys_path+'/bus/scsi/devices'
        self.sort_scsi_devices()
        if self.debug: self.print_scsi_leaders()
        self.process_scsi_enclosures()
        self.process_scsi_disks()
        self.populate_simple_devices()

    def sort_scsi_devices(self):
        bus_contents = os.listdir(self.scsi_path)
        starter = [item for item in bus_contents if 'target' not in item.casefold() and 'host' not in item.casefold()]
        if self.debug: print('The current contents of starter list:',starter)
        for device in starter:#process each scsi device and sort it into the correct array or disregard.
            with open(self.scsi_path+'/'+device+'/type','r') as f:
                scsi_type = str(f.read().strip())
                if scsi_type == '0':
                    self.scsi_disks.append(self.scsi_path+'/'+device)
                elif scsi_type == '13':
                    self.scsi_enclosures.append(self.scsi_path+'/'+device)
                elif scsi_type == '5':
                    if self.debug: print('This is a CD/DVD, ignoring')
                elif scsi_type =='12':
                    if self.debug: print('This looks like a hardware raid controller')
                    self.hardware_raid.append(self.scsi_path+'/'+device)
    def print_scsi_leaders(self):
        print('Being hardware raid leaders section')
        for hdraid in self.hardware_raid:
            print(hdraid)
            with open(hdraid+'/type') as f:
                print(f.read())
            with open(hdraid+'/vendor') as f:
                print('vendor:',f.read())
            with open(hdraid+'/vendor') as f:
                print('model:',f.read())
            print(Path(hdraid).resolve())
        print('---------End HD raid--------')
        print('Begin ses enclosures section')
        for ses in self.scsi_enclosures:
            print(ses)
            with open(ses + '/type') as f:
                print(f.read())
            with open(ses + '/vendor') as f:
                print('vendor:', f.read())
            with open(ses + '/vendor') as f:
                print('model:', f.read())
            print(Path(ses).resolve())
        print('---------End ses enclosures--------')


    def process_scsi_enclosures(self):
        for device in self.scsi_enclosures:
            encl = encl_serv_dev_simple(debug=self.debug,attributes={'device_path':device})
            if encl.attributes['encl_sg_name'] not in self.simple_sas_enclosures and encl.attributes['sas_address'] is not None:
                self.simple_sas_enclosures[encl.attributes['encl_sg_name']] = encl
                if self.debug:
                    for address in self.simple_sas_enclosures[encl.attributes['encl_sg_name']].sas_slot_map:
                        print('These values are for enclosure', self.simple_sas_enclosures[encl.attributes['encl_sg_name']].attributes['encl_sg_name'])
                        print('sas address', address, 'index:', self.simple_sas_enclosures[encl.attributes['encl_sg_name']].sas_slot_map[address]['index_num'])
            elif encl.attributes['encl_sg_name'] not in self.simple_local_enclosures and encl.attributes['sas_address'] is None:
                self.simple_local_enclosures[encl.attributes['encl_sg_name']] = encl
                if self.debug:
                    for address in self.simple_local_enclosures[encl.attributes['encl_sg_name']].sas_slot_map:
                        print('These values are for enclosure', self.simple_sas_enclosures[encl.attributes['encl_sg_name']].attributes['encl_sg_name'])
                        print("This is a local ses controller not using SAS")
    def process_hardware_raid(self):
        if self.debug: print('------Entering function process_hardware_raid in scsi_scan_py class')
        for device in self.hardware_raid:
            hw_raid = hardware_raid_simple(attributes={'device_path':device})
            self.simple_hardware_raid[hw_raid.attributes['raid_sg_name']] = hw_raid

    def process_scsi_disks(self): #use scsi disk device path to build useful sd devices.
        for device in self.scsi_disks:
            disk = scsi_disk(attributes={'device_path':device},quick_scan=self.quick_scan,debug=self.debug)
            disk.find_enclosure(self.simple_sas_enclosures, self.simple_hardware_raid)
            if disk.attributes['encl_sg_name'] is not 'default':
                self.simple_scsi_sds[disk.attributes['sd_name']] = disk
    def populate_simple_devices(self):
        for encl in self.simple_sas_enclosures:
            #setup chassis devices
            wwid = self.simple_sas_enclosures[encl].attributes['wwid']
            num_slots = self.simple_sas_enclosures[encl].attributes['num_slots']
            location = 'unknown'
            if wwid not in self.simple_chassis:
                self.simple_chassis[wwid] = jbod_chassis_simple(debug=self.debug,attributes={'id':None,'wwid':wwid,'num_slots':num_slots,'location':location})
        #next setup md and multipath devices and physical drives
        for sd in self.simple_scsi_sds:
            # try:
                #getting the index and slot number attributes for each sd device by looking its sas_address up in the sas_slot_map for the appropriate enclosure.
            if self.debug: print('Entering populate simple devices in scsi_scan class for ', sd)
            encl_sg_name = self.simple_scsi_sds[sd].attributes['encl_sg_name']
            if self.debug: print('breakpoint 1')
            sas_addr = self.simple_scsi_sds[sd].attributes['sas_address']
            if self.debug:
                print('breakpoint2')
                for address in self.simple_sas_enclosures[encl_sg_name].sas_slot_map:
                    print('My sg is ', encl_sg_name, 'my length is', len(self.simple_sas_enclosures[encl_sg_name].sas_slot_map))
                    print('sas_address', address,'slot', self.simple_sas_enclosures[encl_sg_name].sas_slot_map[address]['slot_num'])
            try:
                self.simple_scsi_sds[sd].attributes['index_num'] = str(self.simple_sas_enclosures[encl_sg_name].sas_slot_map[sas_addr]['index_num'])
                if self.debug: print('breakpoint 3')
                self.simple_scsi_sds[sd].attributes['slot_num'] = str(self.simple_sas_enclosures[encl_sg_name].sas_slot_map[sas_addr]['slot_num'])
            except KeyError as k:
                print('Unable to find index/slot number for ',self.simple_scsi_sds[sd].attributes['sd_name'])
                self.abandoned_drives[self.simple_scsi_sds[sd].attributes['sd_name']] = self.simple_scsi_sds[sd]
                print(k)
            if self.debug: print('breakpoint 4')
            #getting the chassis id from the enclosure to store in physical_device table
            try:
                if sd in self.abandoned_drives:
                    self.abandoned_drives[sd].attributes['chassis_wwid'] = 'No Chassis'
                    if os.path.isdir('/sys/block/'+self.abandoned_drives[sd].attributes['dm_parent']):
                        if self.debug: print('The parent of this failed device is ',self.abandoned_drives[sd].attributes['dm_parent'])
                        slaves = os.listdir('/sys/block/'+str(self.abandoned_drives[sd].attributes['dm_parent'])+'/slaves')
                        if self.debug: print('These drives are siblings',slaves)
                elif sd in self.simple_scsi_sds:
                    self.simple_scsi_sds[sd].attributes['chassis_wwid'] = str(self.simple_sas_enclosures[encl_sg_name].attributes['wwid'])
                else:
                    raise Exception('This scsi disk:',sd,'does not fit in the good drives or the no SAS address bad drives.')
            except Exception as e:
                print(e)


            if self.debug: print('breakpoint end sd loops.')
            # except Exception as e:
            #     print('ran into a problem trying to get index or slot, or chassis wwid from ',self.simple_scsi_sds[sd].attributes['sd_name'])
            #     print(e)
            #     exit(1)
            try:
                if sd in self.abandoned_drives: #drives with errors that prevent determining slots or drives which are not in a SAS connected chassis
                    if 'md_parent' not in self.abandoned_drives[sd].attributes: self.abandoned_drives[sd].attributes['md_parent'] = 'default'
                    if 'dm_parent' not in self.abandoned_drives[sd].attributes: self.abandoned_drives[sd].attributes['dm_parent'] = 'default'
                elif sd in self.simple_scsi_sds: #properly functioning no sys drives whose slots could be determined.
                    if self.debug:print('entering create md land---------------------------------------------')
                    if 'md_parent' not in self.simple_scsi_sds[sd].attributes: self.simple_scsi_sds[sd].attributes['md_parent'] = 'default'
                    if 'dm_parent' not in self.simple_scsi_sds[sd].attributes: self.simple_scsi_sds[sd].attributes['dm_parent'] = 'default'
                    md_name = self.simple_scsi_sds[sd].attributes['md_parent']
                    dm_name = self.simple_scsi_sds[sd].attributes['dm_parent']
                    serial_number = self.simple_scsi_sds[sd].attributes['serial_number']
                    if md_name not in self.simple_mds and md_name != 'default':
                        if self.debug:print('I am added the following md in scsi scan', md_name)
                        self.simple_mds[md_name] = md_device_simple(debug=self.debug,attributes={'md_name':md_name})
                    if dm_name not in self.simple_mpaths and dm_name != 'default':
                        self.simple_mpaths[dm_name] = mpath_device_simple(debug=self.debug,attributes={'dm_name':dm_name})
                    if serial_number not in self.simple_physical_drives:
                        self.simple_physical_drives[serial_number] = physical_drive_simple(debug=self.debug,attributes=self.simple_scsi_sds[sd].attributes)
                else:
                    raise Exception('This sd device',sd,'does not fit into current handling routines.')

            except KeyError as k:
                print('It appears there is a missing key',self.simple_scsi_sds[sd].attributes['sd_name'])
                print(k)
            except Exception as e:
                print(e)
        for sd in self.abandoned_drives:
            del (self.simple_scsi_sds[self.abandoned_drives[sd].attributes['sd_name']])







