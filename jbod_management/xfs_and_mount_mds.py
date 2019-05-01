#!/usr/bin/python36
####to do: parallelize this xfs creation using threads
from jbod_management.utility_scripts.helper_functions import create_mount_xfs_on_md
import os, glob

mdlist_short = []
try:
    mdlist = glob.glob("/sys/block/md*")
    print('I found the following MD devices.',mdlist)
    mdlist_short = [name.split('/')[-1] for name in mdlist]
    print('I found the following MD devices.',mdlist_short)
except Exception as e:
    print("unable to find md devices")
    print(e)
    exit(1)
for md in mdlist_short:
    create_mount_xfs_on_md(md)