#!/usr/bin/python36
import os, subprocess,sys
from jbod_management.utility_scripts.disk_map import scan_scsi_bus
from jbod_management.utility_scripts.helper_functions import raid_partition_drive
from jbod_management.utility_scripts.helper_functions import find_free_md_number, create_md_raid_lun, create_external_bitmap_mount
from jbod_management.utility_scripts.helper_functions import find_chunk_disk_size

####to do: modify class so that it works even if there are disks physically missing from the jbod.
class initial_JBOD_raid_creator(object):
    def __init__(self,debug=False,dryrun=False):
        self.debug = debug
        self.debug = True
        self.dryrun = dryrun
        self.new_mds = [] #A list that shows all new md devices created during the session even if they are not currently 'up'
        self.create_inventory = {}
        if self.debug: print('md raid creation class in debug mode')
        if not self.dryrun: create_external_bitmap_mount(vg='sysvg',bitmap_dir='/bitmap')
        self.inventory = scan_scsi_bus(debug=self.debug,quick_scan=True)
        self.generate_create_inventory()
        self.raid_creation()



    def generate_create_inventory(self):
        for chassis in self.inventory.simple_chassis:
            if chassis not in self.create_inventory:
                self.create_inventory[chassis] = [encl_sg_name for encl_sg_name in
                                                                                       self.inventory.simple_sas_enclosures if
                                                                                       self.inventory.simple_sas_enclosures[
                                                                                         encl_sg_name].attributes[
                                                                                         'wwid'] == chassis]
                if self.debug: print("I am adding this chassis in generate create inventory",chassis,'\n',self.create_inventory[chassis])
            sg_dict = {}
            num_slots = int(self.inventory.simple_chassis[chassis].attributes['num_slots'])
            for encl_sg_name in self.create_inventory[chassis]:
                if self.debug: print("inside gen create inv, I am working on ",encl_sg_name)
                sg_dict[encl_sg_name] = {}
                for sd_name in self.inventory.simple_scsi_sds:
                    if self.inventory.simple_scsi_sds[sd_name].attributes['encl_sg_name'] == encl_sg_name:
                        sg_dict[encl_sg_name][int(self.inventory.simple_scsi_sds[sd_name].attributes['index_num'])] = \
                        self.inventory.simple_scsi_sds[sd_name]
                for count in range(0, num_slots):
                    if count not in sg_dict[encl_sg_name]:
                        cmd = 'sg_ses --index='+str(count)+' --join '+'/dev/'+encl_sg_name
                        subprocess.call(cmd,shell=True)
                        raise Exception('The kernel does not see the disk in chassis',chassis,'enclosure ',encl_sg_name,'with index number:',count,'.\nYou must correct this before using the raid creation utility. More information about this disk is above from sg_ses')

                sg_dict[encl_sg_name] = [sg_dict[encl_sg_name][idx] for idx in sg_dict[encl_sg_name]]
                if self.debug: print("inside sg dict stuff, sg_dict[",encl_sg_name,'] is:',sg_dict[encl_sg_name])
                #Here I am creating a list from a dictionary.
                sg_dict[encl_sg_name].sort(key=lambda unsort_disk: int(unsort_disk.attributes['index_num']))
                for disk in sg_dict[encl_sg_name]:
                    try:
                        disk.attributes['mpath_parent'] = \
                        self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['mpath_name']
                        disk.attributes['dm_part'] = \
                        self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['dm_partition']
                        disk.attributes['dm_part_name'] = \
                        self.inventory.simple_mpaths[disk.attributes['dm_parent']].attributes['dm_partition_name']
                    except KeyError:
                        print('applying defaults for mpath_parent, dm_part, dm_part_name')
                        disk.attributes['mpath_parent'] = None
                        disk.attributes['dm_part'] = None
                        disk.attributes['dm_part_name'] = None
                    if disk.attributes['md_parent'] == 'default': disk.attributes['md_parent'] = None
                    if disk.attributes['dm_parent'] == 'default': disk.attributes['dm_parent'] = None
            self.create_inventory[chassis] = sg_dict

    def raid_creation(self):
        if self.debug: print("Contents of create_inventory",self.create_inventory)
        if self.debug: print('length of self.create_inventory:',len(self.create_inventory))
        for chassis in self.create_inventory:
            if self.debug: print("raid_creation->chassis in self.create_inventory",self.create_inventory[chassis])
            try:
                command = 'mdadm -S /dev/md*'
                if not self.dryrun:subprocess.call(command, shell=True)
                command = 'multipath -F'
                if not self.dryrun:subprocess.call(command, shell=True)
            except Exception as e:
                print("There was a problem trying to stop md devices")
                print(e)
            winner = None
            for encl_sg_name in self.create_inventory[chassis]: #When there are multiple enclosure services controller, use the one that sees the most disks. They should be the same.
                if self.debug: print("raid_creation->chassis->encl_sg_name in self.create_inventory", self.create_inventory[chassis][encl_sg_name])
                if self.debug: print("Entering the sg dev decision loop")
                if winner is None:
                    if self.debug: print("Winner is None")
                    winner = encl_sg_name
                    if self.debug: print("I have made the winner:",encl_sg_name)
                    continue
                elif len(self.create_inventory[chassis][encl_sg_name]) > len(self.create_inventory[chassis][winner]):
                    if self.debug: print("Comparing lengths in decision loop")
                    winner = encl_sg_name
                else:
                    print('Do nothing because I have already selected the largest enclosure')
                    if self.debug: print("Doing nothing because I already have biggest one.")

            encl_sg_name = winner
            #Cal the function to calculate LUN size for this enclosure/chassis by using num_slots and user input.
            lun_size = self.get_lun_size(num_slots=self.inventory.simple_chassis[chassis].attributes['num_slots'])
            # encl_mapper = enclosure_disk_mapper(enclosure_sg_name)
            disk_dict_by_index = self.create_inventory[chassis][encl_sg_name]
            luns_drives = self.generate_lun_files(disk_dict_by_index, lun_size)
            for lun in luns_drives:
                if 'md' in lun:
                    if self.debug: print("I am a valid LUN", lun)
                    self.create_labels_and_parts(luns_drives[lun])  # Create gpt labels and hidden partitions called '1' on each drive.
                    self.create_md_device(luns_drives[lun], lun_size,lun)  # Create md devices from each group of 'lun' drives
            # if luns_drives.has_key('spares') and len(luns_drives['spares']) != 0:      #old statement replaced with if item in set style for python3.6
            if 'spares' in luns_drives and len(luns_drives['spares']) != 0:  # If there are spare drives add them to the md0 lun. All luns will use them due to global spare group in mdadm.conf
                if self.debug: print("I am adding the following spares to md0", luns_drives['spares'])
                self.create_labels_and_parts(luns_drives['spares'])
                self.create_md_device(luns_drives['spares'], len(luns_drives['spares']), 'spares')
            if not self.dryrun:self.update_mdadm_conf()
            command = 'mdadm -S /dev/md*'
            if not self.dryrun:subprocess.call(command, shell=True)
            command = 'multipath -F'
            if not self.dryrun:subprocess.call(command, shell=True)
            command = 'multipath'
            if not self.dryrun:subprocess.call(command, shell=True)
            command = 'mdadm -As'
            if not self.dryrun:subprocess.call(command, shell=True)
            command = 'dracut -f'
            #if not self.dryrun:subprocess.call(command, shell=True)


    def get_lun_size(self, num_slots):
        if self.debug: print('Entering get_lun_size, num_slots =',num_slots)
        lun_size_map = {84:12, 102:14, 60:15}
        lun_size = int(lun_size_map[int(num_slots)])
        if self.debug: print("I have selected a recommended lun_size of", lun_size)
        num_spares = int(num_slots)%lun_size
        if self.debug: print('The number of spares is ', num_spares)
        num_luns = (int(num_slots) - num_spares)/lun_size
        if self.debug: print('The number of luns is', num_luns)
        print("The chassis has "+str(num_slots)+" slots. The recommended configuration is RAID 6 with "+str(lun_size)+" drives per LUN")
        print("This will create ", num_luns, "LUNS of ", lun_size, "drives with ", num_spares, "spare drives.")

        answer_bank = {'yes':1, 'Yes':1, 'YES':1, 'YEs':1, 'y':1, 'Y':1, 'no':0,'n':0, 'N':0, 'No':0, 'nO':0 }
        while True:
            if self.debug: print('Entering get_lun_size, num_slots =', num_slots)
            lun_size_map = {84: 12, 102: 14, 60: 15}
            lun_size = int(lun_size_map[int(num_slots)])
            if self.debug: print("I have selected a recommended lun_size of", lun_size)
            num_spares = int(num_slots) % lun_size
            if self.debug: print('The number of spares is ', num_spares)
            num_luns = (int(num_slots) - num_spares) / lun_size
            if self.debug: print('The number of luns is', num_luns)
            print("The chassis has " + str(num_slots) + " slots. The recommended configuration is RAID 6 with " + str(
                lun_size) + " drives per LUN")
            print("This will create ", num_luns, "LUNS of ", lun_size, "drives with ", num_spares, "spare drives.")

            answer_bank = {'yes': 1, 'Yes': 1, 'YES': 1, 'YEs': 1, 'y': 1, 'Y': 1, 'no': 0, 'n': 0, 'N': 0, 'No': 0,'nO': 0}

            try:
                if self.debug: print('before the answer prompt')
                answer = input("To accept this default value and continue RAID creation, type 'yes', to reject type 'no'\n")
                if self.debug: print('after the answer prompt')
                if self.debug: print('The current value of answer is: ', answer)
            except Exception as e:
                print("Trying to get user input has failed", e)
                answer = 'Failed to get an answer from user.'
                continue
            try:
                response = answer_bank.get(answer, None)
                if self.debug: print('The current value of response is: ', response)
                if response == 1:
                    return lun_size
                elif response == 0:
                    while 1:
                        try:
                            print("\nPlease enter the number of drives per LUN.\n")
                            lun_size = input("minimum 4, maximum " + str(num_slots) + "\n")
                            lun_size = int(lun_size)
                            if not 4 <= lun_size <= int(num_slots):
                                raise Exception("Error in LUN size choice.")
                        except:
                            print('Please make sure that you enter an integer between 4 and',int(num_slots))
                            continue
                        try:
                            num_spares = int(num_slots) % lun_size
                            num_luns = (int(num_slots) - num_spares) / lun_size
                            print("You have chosen to create ", num_luns, "LUNS of ", lun_size, "drives with ", num_spares, "spares.")
                            if sys.version_info[0] < 3:
                                answer2 = input("If this is correct type 'yes', if not type 'no' to try again.\n")
                            else:
                                answer2 = input("If this is correct type 'yes', if not type 'no' to try again.\n")
                            response = answer_bank.get(answer2,None)
                            if response == 1:
                                if self.debug: print('I am returning the manually entered data: ', num_luns, lun_size, num_spares)
                                return lun_size
                            else:
                                continue
                        except KeyError:
                            continue
                        except Exception as e:
                            print("There was an error trying to manually enter LUN size")
                            print(e)
                            exit(0)
                elif response is None:
                    print("Please enter 'yes' or 'no'.")
                    print("-------------------------------------------------------------------")
                    continue
            except KeyError:
                print("Please enter 'yes' or 'no'.")
                continue
            except Exception as e:
                print("There was an error trying to get lun size, see below for more information")
                print(e)
                exit(0)

    def generate_lun_files(self, drive_dict, lun_size):
        num_disks = len(drive_dict)
        if self.debug: print("The len of the drive dict is: ", num_disks)
        if self.debug: print("The leftover is: ", num_disks % lun_size)
        if self.debug: print(drive_dict)
        num_spares = num_disks % lun_size
        luns_drives = {}  # Dictionary of the form {md1:[sdaa,sdab,sdac], md2: [sdad,sdef, sdig] ...} The name of the md device is the key and the value is a list of the sd devices that belong in that lun
        num_luns = int((num_disks - num_spares) / lun_size)
        if self.debug: print("The number of luns is: ", num_luns)
        next_avail_md_num = find_free_md_number(self.new_mds)
        luns_drives['spares'] = []
        for i in range(num_luns):
            luns_drives['md' + str(next_avail_md_num+i)] = []
            for d in range(lun_size): #iterate through each index number until you reach the total number of drives that are not spares.
                idx = d + (lun_size * i)
                new_md_dev_name = 'md' + str(next_avail_md_num+i)
                if self.debug: print(idx)
                if self.debug: print("I am trying to use:",new_md_dev_name)
                luns_drives[new_md_dev_name].append(drive_dict[idx].attributes['sd_name'])
                drive_dict[idx] = None  # Set the drive to None after they are assigned to a LUN. In this way, whatever is left, that is not None, are then assigned to spares.
            if self.debug: print("------End of LUN------ ", i)
        for lun in luns_drives:
            if self.debug: print(lun, luns_drives[lun])
        if self.debug: print("Drive dict now",drive_dict)
        for drive in drive_dict:
            if self.debug: print("content of processing drive dict",drive)
            if drive is not None:
                luns_drives['spares'].append(drive.attributes['sd_name'])
        return luns_drives  # This is a dictionary that contains the md device or 'spares' as a key and a list of drives as a value

    def create_labels_and_parts(self, lun):
        for drive_name in lun:
            raid_partition_drive(drive_name)
            # print("Running the command 'parted -s /dev/" + drive_name + " mklabel gpt'")
            # cmdargs = ['parted', '-s', '/dev/'+drive_name, 'mklabel', 'gpt']
            # if not self.dryrun:subprocess.call(cmdargs)
            # print("Running the command 'parted -s /dev/" + drive_name + " -a optimal unit MB mkpart primary 1 100% set 1 hidden on'")
            # cmdargs = ['parted', '-s', '/dev/' + drive_name, '-a', 'optimal', 'unit', 'MB', 'mkpart', 'primary', '1', '100%', 'set', '1', 'hidden', 'on']
            # if not self.dryrun:subprocess.call(cmdargs)

    def create_md_device(self, lun, lun_size, lun_name):
        parts = []
        drive_sizes =  []
        for drive in lun:
            parts.append('/dev/' + drive + '1')

        if 'md' in lun_name:
            #Here we try to calculate the usable disk size to and chunk size, to handle the case of multiple disk sizes in one array
            try:
                raise Exception("Implement this later.") #for this branch to the except clause.
                chunk_size, usable_disk_size = find_chunk_disk_size(lun)
                create_md_raid_lun(md_name=lun_name, raid_devices_count=lun_size, raid_level=6,raid_partition_names=parts, external_bitmap='/bitmap/' + str(lun_name),chunk_size=str(chunk_size),disk_size=str(usable_disk_size))
            except Exception as e:
                print("something happened in md_raid_creation when seeking chunk disk size.")
                print(e)
                create_md_raid_lun(md_name=lun_name, raid_devices_count=lun_size, raid_level=6,raid_partition_names=parts, external_bitmap='/bitmap/' + str(lun_name))
            self.new_mds.append(lun_name)
        elif lun_name == 'spares':
            spare_md = str(self.new_mds[-1])
            print("The contents of spares list in create md spares portion: ",parts)
            if os.path.isdir('/sys/block/'+spare_md):
                if self.debug: print('mdadm -a /dev/'+spare_md+' ',parts)
                for spare in parts:
                    if self.debug: print("i am adding the spare ", spare)
                    cmdargs = 'mdadm --add /dev/'+spare_md+' '+spare
                    if not self.dryrun:subprocess.call(cmdargs,shell=True)
            else:
                print("Could not continue adding spares because md0 does not exist")
                exit(1)
        else:
            print("There is some kind of error and this is neither spares nor an md device")
            print("The LUn name is ", lun_name)
            exit(1)

    def update_mdadm_conf(self):#updates the /etc/mdadm.conf file to allow consistent loading of arrays in the future.
        spare_group = 'spares_'+str(self.new_mds[-1])
        skip_header = False
        try:
            with open('/etc/mdadm.conf','r') as f:
                 lines = f.readlines()
            for line in lines:
                if 'MAILFROM ' or 'MAILADDR ' or 'DEVICE ' in line:
                    skip_header = True
                else:
                    skip_header = False
        except FileNotFoundError:
            skip_header = False
        cmdargs = ['mdadm', '--detail', '--scan']
        stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        mdadm_scan = stdout.decode("utf-8").splitlines()
        cmdargs = ['hostnamectl', '--static']
        stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE).communicate()
        hostname_output = stdout.decode("utf-8").splitlines()
        mail_source = 'MAILFROM '+hostname_output[0]+'\n'
        mail_addr = 'MAILADDR raid_admin'+'\n'
        search_dev = 'DEVICE /dev/dm*\n'
        with open('/etc/mdadm.conf','a') as f:
            if not skip_header:
                f.writelines([mail_source,mail_addr,search_dev])
            for line in mdadm_scan:
                f.write(line+' spare-group='+spare_group+'\n')
