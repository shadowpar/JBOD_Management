#!/usr/bin/python36

import subprocess
from jbod_management.utility_scripts.scsi_scan import scan_scsi_bus


class disk_tuner():
    def __init__(self):
        self.sysctl_settings = {'vm.dirty_background_bytes':'0', 'vm.dirty_bytes':'0', 'vm.dirty_expire_centisecs':'3000', 'vm.dirty_ratio':'40', 'vm.dirty_writeback_centisecs':'500', 'vm.swappiness':'10'}
                # Dictionary that holds  the mapping between sysctl setting name and value
        self.inventory = scan_scsi_bus(quick_scan=True)
        self.tune_up_system()
        self.tune_up_mds()
        self.tune_up_drives()

    def tune_up_system(self):
        for setting in self.sysctl_settings:
            command = 'sysctl -w ' + setting + '=' + self.sysctl_settings[setting]
            subprocess.call(command, shell=True)
        command = 'tuned-adm profile throughput-performance'
        subprocess.call(command,shell=True)

    def tune_up_drives(self):
        for sd in self.inventory.simple_scsi_sds:
            with open('/sys/block/'+str(self.inventory.simple_scsi_sds[sd].attributes['sd_name'])+'/queue/nr_requests','w') as f:
                f.write('32768')
            with open('/sys/block/'+str(self.inventory.simple_scsi_sds[sd].attributes['sd_name'])+'/queue/read_ahead_kb', 'w') as f:
                    f.write('128')

    def tune_up_mds(self):
        for md in self.inventory.simple_mds:
            with open('/sys/block/'+str(self.inventory.simple_mds[md].attributes['md_name'])+'/md/stripe_cache_size','w') as f:
                f.write('32768')

tuner = disk_tuner()


