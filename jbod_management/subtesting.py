#!/usr/bin/python36

import subprocess, sys, select
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import shlex
import threading

cmdargs = ['ls','-l']
#cmdargs = shlex.shlex('ping 10.42.42.14')
cmdargs = ['ping','10.42.42.14']


proc = subprocess.Popen(cmdargs,stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.STDOUT)
poll_object = select.poll()
poll_object.register(proc.stdout,select.POLLIN)

while proc.poll() is None:
    whole_line = threading.Thread(target=proc.stdout.readline(),)

