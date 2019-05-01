#!/usr/bin/python36
from __future__ import print_function
import os, re, subprocess, glob
from jbod_management.kernel_devices.sd_device import sd_device
from jbod_management.utility_scripts.scsi_scan import scan_scsi_bus
from jbod_management.jbod_physical_devices.scsi_disk import scsi_disk


class enclosure_disk_mapper(object):
    def __init__(self, enclosure, quiet=False, debug=False):
        self.encl_sg_name = enclosure
        self.debug = debug
        if self.debug: print('enclosure_disk_mapper class in debug mode')
        self.sd_devices = []
        self.num_slots = self.get_num_slots()
        self.sas_map_slot = {}  # mapping between sas addresses obtained from sg_ses and the index/slot numbers in the form {$sas_address:{'index':$index, 'slot':$slot}}
        self.drive_dict = {}  # dictionary of kernel drives seen through this enclosure with their associated indexes and slot numbers in the form {$index:{'slot':$slot, 'sd_name':$sd_name}} where $sd_name is the kernel name for block device shown in /sys/block/sd*
        self.create_sas_mapping()
        self.query_sd_device()
        if quiet:
            self.create_sd_devices()
        elif not quiet:
            self.create_sd_devices()
            self.print_disk_list()
            self.check_missing_drives()

    def check_missing_drives(self):
            for key in range(int(self.num_slots)-1):
                if key not in self.drive_dict:
                    print("The drive with index",key,"appears to be missing.")
                    command = "sg_ses --join --index="+str(key)+" /dev/"+self.encl_sg_name
                    subprocess.call(command,shell=True)


    def get_chassis_id(self):
        pass
    def create_sas_mapping(self):
        for idx in range(self.num_slots):
            try:
                slot_num = ''
                slot_sas_address = ''
                cmdargs = ['sg_ses', '--index=0,' + str(idx), '--join', '/dev/' + self.encl_sg_name]
                stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                output = stdout.decode("utf-8").splitlines()
                for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
                    # We are using regex expressions to pick out important information for the function to return.
                    mobj = re.search(r'^\s*SLOT\s*([0-9]{1,3}).*', line,flags=re.IGNORECASE)
                    if (mobj):
                        slot_num = mobj.group(1)  # Pick the slot number out of sg_ses output and map to sas address
                        continue
                    mobj = re.search(r'^\s*SAS address:\s*0x([a-fA-F0-9]{16})\s*', line,flags=re.IGNORECASE)
                    if (mobj):
                        slot_sas_address = mobj.group(1).lstrip(
                            '0x').strip()  # Pick the slot number out of sg_ses output and map to sas address
                        continue
                self.sas_map_slot[slot_sas_address] = {'index': idx, 'slot': slot_num}
            except Exception as e:
                print("An error has occurred while retrieving information from sg_ses for the chassis.")
                print(e)
    def query_sd_device(self):
        list_of_sds = glob.glob('/sys/block/sd*')
        output_lines = {}
        for sd in list_of_sds:
            sd_name = sd.split('/')[-1]
            if os.path.isfile(sd + '/device/sas_address'):
                with open(sd + '/device/sas_address', 'r') as f:
                    sas_addr = f.readline().lstrip('0x').strip()
                if sas_addr in self.sas_map_slot:
                    slot_num = self.sas_map_slot[sas_addr]['slot']
                    index_num = self.sas_map_slot[sas_addr]['index']
                    output_lines[index_num] = str(slot_num) + "----" + sd_name

                    ancestors = self.get_parents2(sd_name)
                    dm_parent = ancestors['dm_parent']
                    mpath_parent = ancestors['mpath_parent']
                    md_parent = ancestors['md_parent']
                    dm_part = ancestors['dm_part']
                    dm_part_name = ancestors['dm_part_name']
                    self.drive_dict[index_num] = {'slot': slot_num, 'sd_name': sd_name, 'dm_parent':dm_parent, 'mpath_parent':mpath_parent, 'md_parent':md_parent, 'dm_part':dm_part, 'dm_part_name':dm_part_name}
                else:
                    pass
            else:
                pass
    def create_sd_devices(self):
        for idx in range(int(self.num_slots)):
            dm_parent = self.drive_dict[idx]['dm_parent']
            if self.debug: print('Creating new sd device in disk_map. index:',idx,"sd_name:",self.drive_dict[idx]['sd_name'],"dm_parent",dm_parent)
            mpath_parent = self.drive_dict[idx]['mpath_parent']
            if self.debug: print('Creating new sd device in disk_map. index:', idx, "sd_name:", self.drive_dict[idx]['sd_name'],
                  "mpath_parent", mpath_parent)
            md_parent = self.drive_dict[idx]['md_parent']
            if self.debug: print('Creating new sd device in disk_map. index:', idx, "sd_name:", self.drive_dict[idx]['sd_name'],
                  "md_parent", md_parent)
            if self.debug: print('Special test create',md_parent)
            dm_part = self.drive_dict[idx]['dm_part']
            if self.debug: print('Creating new sd device in disk_map. index:', idx, "sd_name:", self.drive_dict[idx]['sd_name'],
                  "dm_part", dm_part)
            dm_part_name = self.drive_dict[idx]['dm_part_name']
            if self.debug: print('Creating new sd device in disk_map. index:', idx, "sd_name:", self.drive_dict[idx]['sd_name'],
                  "dm_part_name", dm_part_name)
            slot = self.drive_dict[idx]['slot']
            self.sd_devices.append(sd_device('/sys/block/' + self.drive_dict[idx]['sd_name'], slot=slot, index=idx, dm_parent=dm_parent, mpath_parent=mpath_parent, md_parent=md_parent, dm_part=dm_part, dm_part_name=dm_part_name))

    def print_disk_list(self):
        print('\n--------------------------Start of disks in enclosure',self.encl_sg_name,'------------------------------------------\n')
        print('|'+'Index'.center(5)+'|'+'Slot'.center(4)+'|'+'Disk Name'.center(10)+'|'+'Multipath Device'.center(16)+'|'+'Mpath Partition'.center(15)+'|'+'md raid'.center(7)+'|')
        # for idx in self.drive_dict:
        for idx in range(len(self.drive_dict)):
            try:
                print(''.ljust(64,'-'))

                col1 = str(idx)
                col2 = str(self.drive_dict[idx]['slot']).lstrip('0')
                if col2 == '':
                    col2 = '0'
                col3 = str(self.drive_dict[idx]['sd_name'])
                col4 = str(self.drive_dict[idx]['dm_parent']+'/'+self.drive_dict[idx]['mpath_parent'])
                col5 = str(self.drive_dict[idx]['dm_part']+'/'+self.drive_dict[idx]['dm_part_name'])
                col6 = str(self.drive_dict[idx]['md_parent'])
                print('|'+col1.center(5)+'|'+col2.center(4)+'|'+col3.center(10)+'|'+col4.center(16)+'|'+col5.center(15)+'|'+col6.center(7)+'|')
            except Exception as e:
                print('This index/slot appears to not to be in the drive dictionary:', idx)
                print(e)
        print(''.ljust(64, '-'))

    def get_parents2(self, child, ancestors={'dm_parent':'Not Multipath','mpath_parent':'Not Multipath','dm_part':'Not Partitioned','dm_part_name':'Not Partitioned','md_parent':'Not Part of MD'}):
        if 'sd' in child:
            ancestors['base'] = child
        elif 'dm' in child:
            with open('/sys/block/'+child+'/dm/name','r') as f:
                name = f.read().strip()
            if 'mpath' in name and '1' not in name:
                ancestors['dm_parent'] = child
                ancestors['mpath_parent'] = name
            if 'mpath' in name and '1' in name:
                ancestors['dm_part'] = child
                ancestors['dm_part_name'] = name
        elif 'md' in child:
            ancestors['md_parent'] = child
        parents = glob.glob('/sys/block/'+child+'/holders/*')
        if len(parents) != 0:
            parent = parents[0].split('/')[-1]
            ancestors = self.get_parents2(parent, ancestors)
        return ancestors

    def get_num_slots(self):
        # #Tryto get the number of slots in the chassis/enclosure from sysfs, this does not always work.
        num_components = 10
        try:
            encl_ident = os.listdir('/sys/class/scsi_generic/'+self.encl_sg_name+'/device/enclosure/')[0]
            with open('/sys/class/scsi_generic/'+self.encl_sg_name+'/device/enclosure/'+encl_ident+'/components') as f:
                num_components = int(f.read())
            return num_components
        except Exception as e:
            print('Failed to get number of slots from sysfs')
            print(e)
        try:
            if self.debug: print("entering try loop for sg_ses attempt")
            valid_entry = False #just a flag to tell us we need to read the next line.
            cmdargs = ['sg_ses', '-p', 'cf', '/dev/'+self.encl_sg_name]
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
                        return num_components
                    continue
        except Exception as e:
            print("An error occurred trying to find number of components using sg_ses")
            print(e)
        return num_components

class multi_chassis_mapper(object):
    def __init__(self, debug=False, quiet=False):
        self.chassis_encl_list = {}#Dictionary of the form {'chassis_id':{'num_slots':84,enclosures'{'encl_sg_name1':enclosure_mapper_object1}}}
        self.debug = debug
        if self.debug: print('multichassis mapper class in debug mode')
        self.quiet = quiet
        self.find_unique_chassis()
        self.get_enclosures()


    def find_unique_chassis(self):  # Function that creates a dictionary unique chassis and the enclosures they contain.  Form {'chassis_id':{'sg_names':[$sg1,sg2], 'num_slots':$number_slots_in_chassis, 'lun_size':$drives_per_lun}}
        enclosure_list = os.listdir('/sys/class/enclosure')
        for encl in enclosure_list:
            try:
                sg_name = os.listdir('/sys/class/enclosure/' + encl + '/device/scsi_generic')[0]  # picks off the sg name of enclosure without the full path
                with open('/sys/class/enclosure/' + encl + '/id') as f:
                    chassis_id = f.readline().lstrip('0x').strip()
                if chassis_id not in self.chassis_encl_list:
                    self.chassis_encl_list[chassis_id] = {'enclosures': {sg_name:'First One'}}
                else:
                    self.chassis_encl_list[chassis_id]['enclosures'][sg_name] = 'Second one'
            except Exception as e:
                print("Failed to find required information about enclosure ", encl)
                print(e)
                exit(1)

    def get_enclosures(self):
        for chassis_id in self.chassis_encl_list:
            if not self.quiet:
                if self.debug: print("\n\n-----------------------------Enclosures in Chassis with ID", chassis_id,"-----------------------------------------------------\n")
                for sg_name in self.chassis_encl_list[chassis_id]['enclosures']:
                    self.chassis_encl_list[chassis_id]['enclosures'][sg_name] = enclosure_disk_mapper(sg_name)
                    self.chassis_encl_list[chassis_id]['num_slots'] = self.chassis_encl_list[chassis_id]['enclosures'][sg_name].num_slots
                if self.debug: print("This chassis has",self.chassis_encl_list[chassis_id]['num_slots'],"slots.")
            elif self.quiet:
                for sg_name in self.chassis_encl_list[chassis_id]['enclosures']:
                    self.chassis_encl_list[chassis_id]['enclosures'][sg_name] = enclosure_disk_mapper(sg_name,quiet=True)
                    self.chassis_encl_list[chassis_id]['num_slots'] = self.chassis_encl_list[chassis_id]['enclosures'][sg_name].num_slots

class system_inventory_printer():
    def __init__(self,debug=False):
        self.debug = debug
        if self.debug: print('ENTERING SYSTEM INVENTORY PRINTER IN DEBUG MODE')
        self.inventory = scan_scsi_bus(debug=self.debug,quick_scan=True)
        self.print_inventory = {}
        self.prepare_print_inventory()
        self.print_disk_list()

    def prepare_print_inventory(self):
        for chassis in self.inventory.simple_chassis:
            if chassis not in self.print_inventory: self.print_inventory[chassis] = [encl_sg_name for encl_sg_name in self.inventory.simple_sas_enclosures if self.inventory.simple_sas_enclosures[encl_sg_name].attributes['wwid'] == chassis]
            sg_dict = {}
            num_slots = int(self.inventory.simple_chassis[chassis].attributes['num_slots'])
            for encl_sg_name in self.print_inventory[chassis]:
                sg_dict[encl_sg_name] = {}
                for sd_name in self.inventory.simple_scsi_sds:
                    if self.inventory.simple_scsi_sds[sd_name].attributes['encl_sg_name'] == encl_sg_name:
                        sg_dict[encl_sg_name][int(self.inventory.simple_scsi_sds[sd_name].attributes['index_num'])] = self.inventory.simple_scsi_sds[sd_name]
                for count in range(0,num_slots):
                    if count not in sg_dict[encl_sg_name]:
                        sg_dict[encl_sg_name][str(count)] = scsi_disk(attributes={'device_path':'default','index_num':count,'slot_num':'None','sd_name':'None','dm_parent':'None','dm_part':'None','dm_part_name':'None','md_parent':'None'})

                sg_dict[encl_sg_name] = [sg_dict[encl_sg_name][idx] for idx in sg_dict[encl_sg_name]]
                #sg_dict[encl_sg_name] = [self.inventory.simple_scsi_sds[sd_name] for sd_name in self.inventory.simple_scsi_sds if self.inventory.simple_scsi_sds[sd_name].attributes['encl_sg_name'] == encl_sg_name]
                sg_dict[encl_sg_name].sort(key= lambda unsort_disk: int(unsort_disk.attributes['index_num']))
                for disk in sg_dict[encl_sg_name]:
                    try:
                        disk.attributes['mpath_parent'] = self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['mpath_name']
                        disk.attributes['dm_part'] = self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['dm_partition']
                        disk.attributes['dm_part_name'] = self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['dm_partition_name']
                    except KeyError:
                        print('applying defaults for mpath_parent, dm_part, dm_part_name')
                        disk.attributes['mpath_parent'] = 'Not Multipath'
                        disk.attributes['dm_part'] = 'Not Multipath'
                        disk.attributes['dm_part_name'] =  'Not Multipath'
                    if disk.attributes['md_parent'] == 'default': disk.attributes['md_parent'] = 'Not part of MD'
                    if disk.attributes['dm_parent'] == 'default': disk.attributes['dm_parent'] = 'Not multipath'
            self.print_inventory[chassis] = sg_dict


    def print_disk_list(self):
        for chassis in self.print_inventory:
            print('\n\nEnclosures inside the chassis-----------',chassis,'-----------------------------------------')
            for encl_sg_name in self.print_inventory[chassis]:
                print('\n--------------------------Start of disks in enclosure', encl_sg_name,'------------------------------------------\n')
                print('|' + 'Index'.center(5) + '|' + 'Slot'.center(4) + '|' + 'Disk Name'.center(10) + '|' + 'Multipath Device'.center(16) + '|' + 'Mpath Partition'.center(15) + '|' + 'md raid'.center(7) + '|')
                # for idx in self.drive_dict:
                for disk in self.print_inventory[chassis][encl_sg_name]:
                    try:
                        print(''.ljust(64, '-'))
                        col1 = str(disk.attributes['index_num'])
                        col2 = str(disk.attributes['slot_num']).lstrip('0')
                        if col2 == '':
                            col2 = '0'
                        col3 = str(disk.attributes['sd_name'])
                        col4 = str(disk.attributes['dm_parent'] + '/' + disk.attributes['mpath_parent'])
                        col5 = str(disk.attributes['dm_part'] + '/' + disk.attributes['dm_part_name'])
                        col6 = str(disk.attributes['md_parent'])
                        print('|' + col1.center(5) + '|' + col2.center(4) + '|' + col3.center(10) + '|' + col4.center(
                            16) + '|' + col5.center(15) + '|' + col6.center(7) + '|')
                    except Exception as e:
                        print('There was an error printing this disk list')
                        print(e)
                print(''.ljust(64, '-'))

        if len(self.inventory.abandoned_drives) != 0:
            print('Failed drives ----------------------------')
            print('The following drives could not have their slot determined because the SAS address registered with the kernel has no corresponding SAS address with a JBOD enclosure.\nThis usually indicates a failed SAS path.')
            for sd in self.inventory.abandoned_drives:
                print(self.inventory.abandoned_drives[sd].attributes['sd_name'])
                print('Check the output of multipath -l | egrep -A5 -B5',self.inventory.abandoned_drives[sd].attributes['sd_name'])
                self.inventory.abandoned_drives[sd].attributes['chassis_wwid'] = 'No Chassis'
                if os.path.isdir('/sys/block/' + self.inventory.abandoned_drives[sd].attributes['dm_parent']):
                    print('The parent of this failed device is ',self.inventory.abandoned_drives[sd].attributes['dm_parent'])
                    slaves = os.listdir('/sys/block/' + str(self.inventory.abandoned_drives[sd].attributes['dm_parent']) + '/slaves')
                    print('These drives are siblings', slaves)
