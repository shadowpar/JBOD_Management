#!/usr/bin/python36
import subprocess, sys
from jbod_management.utility_scripts.scsi_scan import scan_scsi_bus




class disk_wiper(object):
    def __init__(self,disk_name_list=[],wipe_group=None):
        if wipe_group == 'external_sas_enclosures':
            inventory = scan_scsi_bus(debug=False, quick_scan=True)
            for drive in inventory.simple_scsi_sds:
                disk_name_list.append(drive)

        for disk_name in disk_name_list:
                self.disk_wipe(disk_name)

    def disk_wipe(self,drive_name):
        cmdargs = ['dd', 'if=/dev/zero', 'of=/dev/' + drive_name, 'bs=1M', 'count=1024', 'status=progress']
        process = subprocess.Popen(cmdargs, stdout=subprocess.PIPE)
        for line in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
            sys.stdout.write(line)

    def print_sas(self,drive_name):
        cmdargs = ['cat', '/sys/block/' + drive_name + '/device/sas_address']
        process = subprocess.Popen(cmdargs, stdout=subprocess.PIPE)
        for line in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
            sys.stdout.write(line)


