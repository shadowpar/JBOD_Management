#!/usr/bin/python36



class jbod_chassis_simple(object):
    def __init__(self,debug=False,attributes={'wwid':None,'num_slots':None,'location':'Unknown'}):
        self.debug = debug
        if self.debug: print('jbod simple class in debug mode')
        if self.debug: print(attributes)
        if self.debug: print('Entering constructor for jbod_chassis_simple')
        self.attributes = attributes
        if self.debug: print(self.attributes)
        self.idiot_check()
    def idiot_check(self):
        if self.debug: print('inside idiot check',self.attributes)
        if self.attributes['wwid'] is None or len(self.attributes) == 0:
            print("You attempted to create a JBOD chassis without the required wwid unique identifier. The program has failed")
            exit(1)






