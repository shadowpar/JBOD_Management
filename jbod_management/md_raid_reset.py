#!/usr/bin/python36

from jbod_management.utility_scripts.disk_wipe import disk_wiper
import os, glob, subprocess
test_string='YOLO'
while True:
    print("Are you ABSOLUTELY CERTAIN that you want to do this?\n")
    print("This program will wipe all disks in external enclosures connected to this computer and communicating over the SAS protocol.\n")
    print("It will also delete all files in /bitmap/md* and the /etc/mdadm.conf file and stop all software raid devices.")
    print("There is no UNDO button. If not, press CTRL+C to exit.\n")
    if test_string == input("If you are sure type '"+test_string+"'"):
        print("\n------------good cruel world---------------")
        #cmdargs = ['mdadm','-S',"/dev/md*"]
        cmdargs = ["mdadm -S /dev/md*"]
        subprocess.run(cmdargs,shell=True)
        md_bitmaps = glob.glob('/bitmap/md*')
        for bitmap in md_bitmaps:
            os.remove(bitmap)
        if os.path.isfile('/etc/mdadm.conf'):
            os.remove('/etc/mdadm.conf')
        wiper = disk_wiper(wipe_group='external_sas_enclosures')
        exit(0)
    else:
        continue
