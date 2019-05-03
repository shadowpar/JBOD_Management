#!/usr/bin/python36
import subprocess, glob,os, re
from math import trunc



def raid_partition_drive(drive_name):
    print("Running the command 'parted -s /dev/" + drive_name + " mklabel gpt'")
    cmdargs = ['parted', '-s', '/dev/' + drive_name, 'mklabel', 'gpt']
    subprocess.call(cmdargs)
    print("Running the command 'parted -s /dev/" + drive_name + " -a optimal unit MB mkpart primary 1 100% set 1 hidden on'")
    cmdargs = ['parted', '-s', '/dev/' + drive_name, '-a', 'optimal', 'unit', 'MB', 'mkpart', 'primary', '1', '100%',
               'set', '1', 'hidden', 'on']
    subprocess.call(cmdargs)



def find_free_md_number(known_mds=[]):
    print("This is the contents of known mds passed tino find free md number",known_mds)
    command = 'mdadm -As'
    subprocess.call(command,shell=True)
    existing_mds = glob.glob("/sys/block/md*")
    if len(existing_mds) == 0 and len(known_mds) == 0:
        return 0
    else:
        numbers = []
        for item in existing_mds:
            numbers.append(int(item.split('/')[-1].lstrip('md').rstrip()))
        for item in known_mds:
            numbers.append(int(item.split('/')[-1].lstrip('md').rstrip()))
        return max(numbers) + 1 #return the next available integer for md*



#This helper function takes the name, number of devices, raid level, and a list of raid partition names and an optional external bitmap file target.
#It then uses the mdadm command to create a raid array after some dummy checks. Can be used manually from interactive python shell
#It is also used by the initial_JBOD_raid_creator class
def create_md_raid_lun(md_name,raid_devices_count,raid_level,raid_partition_names=[],external_bitmap=None,chunk_size=None,disk_size=None):
    if os.path.isdir('/sys/block/'+str(md_name)):
        print("The md device "+str(md_name)+" already exists.")
        exit(1)
    if len(raid_partition_names) < raid_devices_count:
        print("You need at least",raid_devices_count,"devices to build this RAID"+str(raid_level),"device")
        exit(1)
    if disk_size is None or chunk_size is None: #failed to calculate disk size or chunk size, let mdadm handle it auto
        mdadm_cmd = ['mdadm','-vv','--create','/dev/'+str(md_name),'--level='+str(raid_level),'--raid-devices='+str(raid_devices_count)]
    else:
        mdadm_cmd = ['mdadm','-vv','--create','/dev/'+str(md_name),'--size='+disk_size,'--chunk='+chunk_size,'--level='+str(raid_level),'--raid-devices='+str(raid_devices_count)]

    print("right now '1' the mdadm command is",mdadm_cmd)
    if external_bitmap is not None:
        if os.path.isfile(external_bitmap):
            print("removing old bitmap file")
            subprocess.call('rm -f '+str(external_bitmap))
        if not os.path.isdir(os.path.dirname(str(external_bitmap))):
            print("Target external bitmap directory does not exist.")
            exit(1)
        mdadm_cmd.append('--bitmap='+str(external_bitmap))
        print("right now '2' the mdadm command is", mdadm_cmd)
    for part in raid_partition_names:
        mdadm_cmd.append(part)
        print(" the mdadm command is", mdadm_cmd)
    print("right now '5' the mdadm command is", mdadm_cmd)


    p = subprocess.run(mdadm_cmd,stderr=subprocess.PIPE,stdout=subprocess.PIPE,stdin=subprocess.PIPE)
    for line in iter(p.stdout):
        print(line)


    check_md = 'mdadm -D /dev/'+str(md_name)
    subprocess.call(check_md,shell=True)


#This function creates a logical volume to hold external bitmaps for raid arrays
def create_external_bitmap_mount(vg='sysvg',bitmap_dir='/bitmap'):
    #check if external bitmap mount point already exists. First check for existence of directory /bitmap
    lvexists = False
    if not os.path.isdir(bitmap_dir):
        os.mkdir(bitmap_dir)
    cmdargs = ['lvs', '--no-headings']
    stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    output = stdout.decode("utf-8").splitlines()
    for line in output:
        # We are using regex expressions to pick out important information for the function to return.
        mobj = re.search(r'^\s*bitmap\s*sys-vg.*', line,flags=re.IGNORECASE)
        if (mobj):
            print('The bitmap logical volume already exists')
            lvexists = True
            break
    if not lvexists:
        command = 'lvcreate -L 1G sysvg -nbitmap'
        subprocess.call(command, shell=True)
        command = 'mkfs.ext3 /dev/mapper/sysvg-bitmap'
        subprocess.call(command, shell=True)
        with open('/etc/fstab','a') as f:
            f.write('/dev/mapper/sysvg-bitmap on /bitmap type ext3 (rw,relatime,stripe=64,data=ordered)\n')
    if not os.path.ismount('/bitmap'):
        command = 'mount /dev/mapper/sysvg-bitmap /bitmap'
        subprocess.call(command, shell=True)
    command = 'rm -f /bitmap/md*'
    subprocess.call(command, shell=True)

def find_chunk_disk_size(disk_list=[],debug=False): #pass in a group of disks meant for a software raid array. return chunk_size, usable_disk_size
    disk_sizes = []
    #for now hardcode chunk size as 512 kb,which is the mdadm default, later we will write more functiosn to determine chunk size based on anticipated file sizes.
    chunk_size = 512*1024 #chunk size in number of bytes
    usable_disk_size = None
    for disk in disk_list:
        try: #try to find usable size of the raid partition on the disk.
            with open('/sys/block/'+disk+'/'+disk+'1'+'/size') as f:
                num_512byte_sectors = float(f.read())
                disk_byte_size = (num_512byte_sectors*512.0)-(300*1024*1024) #reserving 200 MB for possible RAID metadata and disk size reporting error at the end of the drive.
                usable_disk_size = disk_byte_size - (disk_byte_size % chunk_size)
                disk_sizes.append(usable_disk_size)
                print("I am using partition size and the size in kB is",usable_disk_size/1024)

        except FileNotFoundError as e:
            print("there was a problem trying to determine the raid partition size")
            try: #since we cant find raid partition size in sysfs, we will take the drive size subtract 10 Mb for all metadata room
                with open('/sys/block/'+disk+'/size') as f:
                    num_512byte_sectors = float(f.read())
                    disk_byte_size = (num_512byte_sectors*512.0)
                    disk_byte_size = disk_byte_size - (300*1024*1024) #removing 10MB for partition metadata safety margin due to using disk size instead of partition size
                    usable_disk_size = disk_byte_size - (disk_byte_size % chunk_size)
                    disk_sizes.append(usable_disk_size)
            except FileNotFoundError as e:
                print("I was unable to locate the size file for ",disk,"in sysfs")
                print(e)
        except Exception as e:
            print("there was some problem when trying to determine disk size in find_chunk_size")
            print(e)
    print("These are the values of disk sizes", disk_sizes)
    if not len(disk_sizes) == 0:
        usable_disk_size = min(disk_sizes)
        print("I have found a usable disk size of:",usable_disk_size)
    if usable_disk_size is None:
        return None,None
    else:#return chunk size and usable_disk_size in kB
        print("I am returning the following values: chunk=",chunk_size/1024,'usable_disk_size',usable_disk_size/1024)
        return (trunc(chunk_size/1024)), (trunc(usable_disk_size/1024))

def answering_readline(file_descriptor):
     file_descriptor = subprocess.run(['command'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def create_mount_xfs_on_md(mdname):
    if not 'md' in mdname:
        print("This function is designed for creating xfs file systems on md devices and mounting them.")
        return

    if not (os.path.isdir('/sys/block/'+str(mdname))):
        try:
            cmdargs = ['mdadm','-A','/dev/'+str(mdname)]
            subprocess.run(cmdargs)
            if not (os.path.isdir('/sys/block/'+str(mdname))):
                raise Exception(mdname,"does not appear to be a valid md software raid.")
        except:
            print("Unable to find or start the md device ",mdname)
            return
    cmdargs = ['mkfs.xfs','-f','/dev/'+str(mdname)]
    try:
        subprocess.run(cmdargs)
    except Exception as e:
        print("There was a problem trying to create the xfs file system on /dev/"+str(mdname))
        return
    try:
        with open('/etc/fstab','r') as f:
            for line in f.readlines():
                if str(mdname) in line:
                    print("There is already an entry in fstab for ",mdname,"please investigate and manually correct.")
                    return
    except FileNotFoundError as e:
        print("failed to find the /etc/fstab file. Please manually create the required entries to mount",mdname)
        return
    except Exception as e:
        print(e)
        return
    try:
        with open('/etc/fstab','a') as f:
            mdnum = str(mdname).lstrip('md')
            if not os.path.isdir('/data'+mdnum):
                os.mkdir('/data'+mdnum)
            f.write('/dev/'+str(mdname)+' '+'/data'+mdnum+'                    xfs     defaults,nofail        0 0\n')
        if  not check_is_mounted(mdname):
            if not check_is_mounted('/data/'+mdnum):
                cmdargs = ['mount','/dev/'+str(mdname),'/data'+mdnum]
                subprocess.run(cmdargs)
                return
            else:
                print("This md device already appears to be mounted")
                cmdargs = ['mount','-l']
                subprocess.run(cmdargs,shell=True)
                return
        else:
            print("This directory already appears to be mounted. /data"+mdnum)
            cmdargs = ['mount','-l']
            subprocess.run(cmdargs,shell=True)
            return
    except FileNotFoundError as e:
        print("failed to find the /etc/fstab file. Please manually create the required entries to mount",mdname)
        return
    except Exception as e:
        print(e)
        return
def check_is_mounted(name): #pass a mount point or a device name in to see if it is currently mounted. returns a bool
    try:
        name = str(name)
    except Exception as e:
        print("Unable to convert ",name,"to a string")
        print(e)
        exit(1)
    with open('/proc/mounts','r') as f:
        for line in f.readlines():
            if name in line:
                print(name,"is currently mounted")
                print(line)
                return True
        print(name,"is not currently mounted.")
        return False












