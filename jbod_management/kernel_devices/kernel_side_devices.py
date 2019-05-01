#!/usr/bin/python36

#The purpose of this module is to gather information about all scsi devices from SYSFS on a system for use in automated the #operation of linux software raid devices.

from __future__ import print_function
import os, os.path, glob

class linux_block_dev(object):
  def __init__(self, path_to_device_in, nesting):
    self.path_to_device = path_to_device_in
    self.nest_level = nesting
  def dev_print(self):
    print(self.nest_level*"   "+"|-"+self.path_to_device)
class composite_block_dev(linux_block_dev):#inherits from linux_block_dev, can be used for dm or md devices.
  def __init__(self, path_to_device_in, nesting):
    super(composite_block_dev, self).__init__(path_to_device_in, nesting)
    self.dm_slaves = []
    self.sd_slaves = []
    self.populate_dm_slaves()
    self.populate_sd_slaves()
  def populate_dm_slaves(self):
    dm_slave_names = glob.glob(self.path_to_device+'/slaves/dm*')
    for dm_slave in dm_slave_names:
      self.dm_slaves.append(dm_device(dm_slave, self.nest_level+1))
  def populate_sd_slaves(self):
    sd_slave_names = glob.glob(self.path_to_device+'/slaves/sd*')
    for sd_slave in sd_slave_names:
      self.sd_slaves.append(sd_device(sd_slave, self.nest_level+1))
  def dev_print_slaves(self):
    print(self.nest_level*" "+"|-"+self.path_to_device)
    for dm in self.dm_slaves:
      dm.dev_print_slaves()
    for sd in self.sd_slaves:
      sd.dev_print()

class md_device(composite_block_dev):
  def __init__(self, path_to_device_in, nesting):
    super(md_device, self).__init__(path_to_device_in, nesting)


class dm_device(composite_block_dev):
  def __init__(self, path_to_device_in, nesting):
    super(dm_device, self).__init__(path_to_device_in, nesting)

class sd_device(linux_block_dev):
  def __init__(self, path_to_device_in, nesting):
    super(sd_device, self).__init__(path_to_device_in, nesting)
    self.parent = "None"
    self.sas_address = ''
    self.mpathParent = "None"
    self.leader = self.path_to_device
    print(self.path_to_device)
    self.isMultipath = 1
    self.isNotRaid = 0
    self.multipathSiblings = []
    self.findParent()
    self.findMultipathSiblings()#findParent must be run first
    self.findLeader(self.path_to_device)
    self.find_sas_address()
  def find_sas_address(self):
    try:
      for line in open(self.path_to_device+'/device/sas_address','r'):
        self.sas_address = line.lstrip('0x')
    except:
      print("This device has no SAS address")
      self.sas_address = 'ignore'
  def findParent(self):
    if len(os.listdir(self.path_to_device+'/holders/') ) == 0:
      self.isMultipath = 0
    else:
      parentHolder = glob.glob(self.path_to_device+"/holders/dm*")
      if len(parentHolder) == 1:
        self.parent = parentHolder[0]
        f = open(self.parent+"/dm/name", "r")
        self.mpathParent = f.read()
        f.close()
        self.isMultipath = 1
        print("I am multipath sd device")
        print('')
        print("My multipath device is "+self.mpathParent)

  def findMultipathSiblings(self):
    if self.parent != "None":
      self.multipathSiblings = os.listdir(self.parent+"/slaves")
      print("The disks in my multipath device are")
      print(self.multipathSiblings)

  def findLeader(self, candidate):#Climb the tree to find top level block device.
      if len(os.listdir(candidate+"/holders/")) != 0:
        self.findLeader(candidate+"/holders/"+os.listdir(candidate+"/holders")[0])
      else:
        self.leader = candidate
        if self.leader.split("/")[-1].find('md') == -1:
          self.isNotRaid = 1
          print("isNotRaid is set to 1")
        else:
          self.isNotRaid = 0
          print("isNotRaid is set to 0")




class md_dev_collector:
  def __init__(self):
    self.virtual_block_dir = "/sys/devices/virtual/block/"
    self.md_device_list = glob.glob(self.virtual_block_dir+'md*')
    self.md_devices = []
    self.populate_md_devices()
  def populate_md_devices(self):
    for md in self.md_device_list:
      self.md_devices.append(md_device(md, 0))
  def md_dev_print(self):
    for md in self.md_devices:
      md.dev_print_slaves()
