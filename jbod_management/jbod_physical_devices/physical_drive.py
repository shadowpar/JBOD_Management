#!/usr/bin/python36

import re,subprocess

class physical_drive_simple(object):
    def __init__(self,debug=False,attributes={'serial_number':None,'encl_sg_name':'sg1','status':'Unkown','Ident':'Unknown'}):
        self.debug = debug
        if self.debug: print('physical drive simple class in debug mode')
        self.serial_number = attributes['serial_number']
        self.attributes = attributes
        if self.debug: print('Inisde of physical drive creator my attributes are: ',self.attributes)
        if self.serial_number is None or len(attributes) == 0:
            print("Failed to create a physical drive object without serial number")
            exit(1)
        if self.attributes['serial_number'] != 'default':
            if self.debug: print('I am entering physical drive populate sg_ses attrs')
            self.populate_ses_attrs()

    def populate_ses_attrs(self):
        try: #retrieve information about drive status and ident light status from sg_ses
            cmdargs = ['sg_ses', '--index='+str(self.attributes['index_num']), '--join', '/dev/' + self.attributes['encl_sg_name']]
            stdout, stderr = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            output = stdout.decode("utf-8").splitlines()
            for line in output:  # parsing the output of smartctl -a /dev/$enclosure sg name
                if self.debug: print('The line im processing in populate sg_ses_attrs is: \n',line)
                # We are using regex expressions to pick out important information for the function to return.
                mobj = re.search(r'^.*status:\s*([a-zA-Z]+).*', line,flags=re.IGNORECASE)
                if (mobj):
                    if self.debug: print('I found a status:',mobj.group(1).strip())
                    self.attributes['status'] = str(mobj.group(1).strip())  # Pick the slot number out of sg_ses output and map to sas address
                    continue
                mobj = re.search(r'^.*Ident=\s*([0-1]+).*', line,flags=re.IGNORECASE)
                if (mobj):
                    if self.debug: print('I found an ident:', mobj.group(1).strip())
                    self.attributes['ident'] = mobj.group(1).strip()  # Pick the slot number out of sg_ses output and map to sas address
                    continue
        except Exception as e:
            print('Failed to get ses attrs for physical drive: ',self.attributes['serial_number'],'in index number',self.attributes['index_num'])
            print(e)


