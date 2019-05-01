#!/usr/bin/python36

import os

from jbod_management.jbod_physical_devices.jbod_chassis import jbod_chassis_simple
from jbod_management.jbod_physical_devices.physical_drive import physical_drive_simple
from jbod_management.kernel_devices.mpath_device import mpath_device_simple
from jbod_management.kernel_devices.md_device import md_device_simple
from jbod_management.jbod_physical_devices.enclosure_services_device import encl_serv_dev_simple
from jbod_management.jbod_physical_devices.scsi_disk import scsi_disk
from jbod_management.utility_scripts.scsi_scan import scan_scsi_bus
import sqlite3, datetime
import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class chassis(Base):
    __table__name = 'chassis'

    id = Column(Integer, primary_key=True)
    wwid = Column(String,nullable=False)
    num_slots = Column(Integer,nullable=False)
    location = Column(String,nullable=True)
    def __repr__(self):
        return "<chassis(wwid='%s', num_slots,'%s', location,'%s')" % (self.wwid, self.num_slots,self.location)



class orm_database_writer(Base):
    def __init__(self,data_location='/var/lib/jbod_management'):
        self.data_location = data_location
        self.engine = sqlalchemy.create_engine('sqlite:///:memory',echo=True)
        self.Base = declarative_base()


class database_writer(object):
    def __init__(self, debug=False, data_location='/var/lib/jbod_management'):
        self.debug = debug
        if self.debug: print('database_writer class in debug mode.')
        if self.debug: print('beginning database writer class')
        self.data_location = data_location
        self.dtype_map = {'Null':None, 'Integer':type(int(1)),'Real':type(float), 'Text':type(str),'Blob':type(bytes)}
        if not os.path.isdir(self.data_location): os.mkdir(self.data_location)
        if not os.path.isdir(self.data_location+'/logs'): os.mkdir(self.data_location+'/logs')
        if self.debug: print('I am about to declare tables')

        # self.tables = {'md_name': 'md_devices', type(md_device_simple(debug=self.debug,attributes={'md_name': 'default'})): 'md_devices',
        #               'dm_name': 'multipath_devices',type(mpath_device_simple(debug=self.debug,attributes={'dm_name': 'default'})): 'multipath_devices',
        #               'wwid': 'chassis', type(jbod_chassis_simple(debug=self.debug,attributes={'wwid': 'default'})): 'chassis',
        #               'sd_name': 'sd_devices', type(sd_device_simple(debug=self.debug,attributes={'sd_name': 'default'})): 'sd_devices',
        #               'serial_number': 'physical_drives',type(physical_drive_simple(debug=self.debug,attributes={'serial_number':'default'})): 'physical_drives',
        #                'sg_name':'enclosure_devices',type(encl_serv_dev_simple(debug=self.debug,attributes={'device_path':'default'})):'enclosure_devices'}

        self.tables = {'md_name': 'md_devices',type(md_device_simple(debug=self.debug, attributes={'md_name': 'default'})): 'md_devices',
                      'dm_name': 'multipath_devices', type(mpath_device_simple(debug=self.debug, attributes={'dm_name': 'default'})): 'multipath_devices',
                      'wwid': 'chassis',type(jbod_chassis_simple(debug=self.debug, attributes={'wwid': 'default'})): 'chassis',
                      'sd_name': 'sd_devices',type(scsi_disk(debug=self.debug, attributes={'device_path': 'default'})): 'sd_devices',
                      'serial_number': 'physical_drives', type(physical_drive_simple(debug=self.debug, attributes={'serial_number': 'default'})): 'physical_drives',
                      'encl_sg_name': 'enclosure_devices', type(encl_serv_dev_simple(debug=self.debug, attributes={'device_path': 'default'})): 'enclosure_devices'}


        self.md_log = open(self.data_location + '/logs/md.log', 'a')
        self.dm_log = open(self.data_location + '/logs/dm.log', 'a')
        self.sd_log = open(self.data_location + '/logs/sd.log', 'a')
        self.physical_drives_log = open(self.data_location + '/logs/physical_drives.log', 'a')
        self.general_log = open(self.data_location + '/logs/general.log', 'a')
        self.chassis_log = open(self.data_location + '/logs/chassis.log', 'a')
        self.enclosure_devices_log = open(self.data_location + '/logs/enclosure_devices.log', 'a')
        if self.debug: print('I am about to declare the log files')

        # self.log_files = {'md_name': self.md_log, type(md_device_simple(debug=self.debug,attributes={'md_name': 'default'})): self.md_log,
        #                   'dm_name': self.dm_log, type(mpath_device_simple(debug=self.debug,attributes={'dm_name': 'default'})): self.dm_log,
        #                   'wwid': self.chassis_log, type(jbod_chassis_simple(debug=self.debug,attributes={'wwid': 'default'})): self.chassis_log,
        #                   'sd_name': self.sd_log, type(sd_device_simple(debug=self.debug,attributes={'sd_name': 'default'})): self.sd_log,
        #                   'serial_number': self.physical_drives_log,type(physical_drive_simple(debug=self.debug,attributes={'serial_number':'default'})): self.physical_drives_log,
        #                   'sg_name': self.enclosure_devices_log, type(encl_serv_dev_simple(debug=self.debug, attributes={'device_path': 'default'})): self.enclosure_devices_log}

        self.log_files = {'md_name': self.md_log,type(md_device_simple(debug=self.debug, attributes={'md_name': 'default'})): self.md_log,
                          'dm_name': self.dm_log,type(mpath_device_simple(debug=self.debug, attributes={'dm_name': 'default'})): self.dm_log,
                          'wwid': self.chassis_log,type(jbod_chassis_simple(debug=self.debug, attributes={'wwid': 'default'})): self.chassis_log,
                          'sd_name': self.sd_log,type(scsi_disk(debug=self.debug, attributes={'device_path': 'default'})): self.sd_log,
                          'serial_number': self.physical_drives_log, type(physical_drive_simple(debug=self.debug,attributes={'serial_number': 'default'})): self.physical_drives_log,
                          'encl_sg_name': self.enclosure_devices_log, type(encl_serv_dev_simple(debug=self.debug,attributes={'device_path': 'default'})): self.enclosure_devices_log}

        if not os.path.isfile(self.data_location + '/jbod_management.db'):
            self.create_new_database()
        self.conn = sqlite3.connect(self.data_location + '/jbod_management.db')
        self.cursor = self.conn.cursor()
        #self.tables_description = self.get_table_info()

        #self.dm_devices = {}    #Dictionary of the form {'dm_name':mpath_device_simple}
        #self.md_devices = {}    #Dictionary of the form {'md_name':md_device_simple}
        #self.chassis = {}   #Dictionary of the form {'wwid':jbod_chassis_simple_object}
        #self.physical_drives = {}   #dictionary of the form {'serial_number':physical_drive_object}
        #self.sd_devices = {}    #Dictionary of the form {'sd_name':sd_device}
        if self.debug: print('about to do disk_inventory')
        #self.disk_inventory = multi_chassis_mapper(debug=self.debug,quiet=True).chassis_encl_list
        self.general_log.write(str(datetime.datetime.now()) + '-------Commencing run of database writer.py\n')
        #self.process_incoming_sd_data()
        if self.debug: print('about to show database')
        self.process_disks_inventory()
        self.show_database_contents_debug()
        self.cleanup()

    def get_table_info(self): #write a function that uses the sql statement c.execute('PRAGMA TABLE_INFO(tablename)') where c is the cursor. for each table
                                #such that the result is a dictionary of the form {table_name:{column_name:type}} Then create a dictionary that maps sqlite3 types to python data types.
        pass

    def create_new_database(self):
        conn = sqlite3.connect(self.data_location+'/jbod_management.db')
        cursor = conn.cursor()
        if self.debug: print('Entering create new database function')
        cursor.execute('''CREATE TABLE chassis(
                                                    id INTEGER PRIMARY KEY,
                                                    wwid TEXT UNIQUE NOT NULL,
                                                    num_slots INTEGER NOT NULL,
                                                    location TEXT
                                                    )''')

        cursor.execute('''CREATE TABLE enclosure_devices(
                                                        id INTEGER PRIMARY KEY,
                                                        encl_sg_name TEXT UNIQUE NOT NULL,
                                                        sas_address TEXT,
                                                        vendor TEXT,
                                                        model TEXT,
                                                        state TEXT,
                                                        wwid TEXT NOT NULL,
                                                        FOREIGN KEY(wwid) REFERENCES chassis(wwid)
                                                        )''')

        cursor.execute('''CREATE TABLE md_devices(
                                                        id INTEGER PRIMARY KEY,
                                                        md_name TEXT UNIQUE NOT NULL,
                                                        md_size TEXT,
                                                        md_used TEXT,
                                                        md_free TEXT,
                                                        md_filesystem TEXT,
                                                        md_raid_level TEXT,
                                                        md_status TEXT,
                                                        md_mount_point TEXT,
                                                        md_raid_devices TEXT,
                                                        md_present_devices TEXT,
                                                        md_active_devices TEXT,
                                                        md_working_devices TEXT,
                                                        md_spare_devices TEXT,
                                                        md_failed_devices TEXT,
                                                        md_device_status_list TEXT
                                                        )''')

        cursor.execute('''CREATE TABLE multipath_devices(
                                                            id INTEGER PRIMARY KEY,
                                                            dm_name TEXT UNIQUE NOT NULL,
                                                            mpath_name TEXT,
                                                            dm_partition TEXT,
                                                            dm_partition_name TEXT,
                                                            md_parent TEXT,
                                                            FOREIGN KEY(md_parent) REFERENCES md_devices(md_name)
                                                            )''')

        cursor.execute('''CREATE TABLE physical_drives(
                                                            id INTEGER PRIMARY KEY,
                                                            serial_number TEXT UNIQUE NOT NULL,
                                                            slot_num TEXT,
                                                            index_num TEXT,
                                                            chassis_wwid TEXT,
                                                            dm_parent TEXT,
                                                            md_parent,
                                                            status TEXT,
                                                            ident INTEGER,
                                                            model_family TEXT,
                                                            model TEXT,
                                                            firmware_version TEXT,
                                                            capacity TEXT,
                                                            rotation_rate TEXT,
                                                            FOREIGN KEY(chassis_wwid) REFERENCES chassis(wwid),
                                                            FOREIGN KEY(dm_parent) REFERENCES multipath_devices(dm_name),
                                                            FOREIGN KEY(md_parent) REFERENCES md_devices(md_name)
                                                            )''')

        cursor.execute('''CREATE TABLE sd_devices(
                                                        id INTEGER PRIMARY KEY,
                                                        sd_name TEXT UNIQUE NOT NULL,
                                                        sas_address TEXT,
                                                        serial_number TEXT NOT NULL,
                                                        encl_sg_name TEXT,
                                                        major_minor_num TEXT UNIQUE,
                                                        partition_dev_name TEXT,
                                                        FOREIGN KEY(serial_number) REFERENCES physical_drives(serial_number)
                                                        FOREIGN KEY(encl_sg_name) REFERENCES enclosure_devices(encl_sg_name)
                                                        )''')



        conn.commit()
        conn.close()
        if self.debug: print('Leave create new database function')
    def show_database_contents_debug(self):
        self.cursor.execute('SELECT * FROM chassis')
        names = [description[0] for description in self.cursor.description]
        print('The current chassis devices')
        for row in self.cursor.fetchall():
            print(names)
            print(row)
        self.cursor.execute('SELECT * FROM enclosure_devices')
        names = [description[0] for description in self.cursor.description]
        print('The current enclosure devices')
        for row in self.cursor.fetchall():
            print(names)
            print(row)

        self.cursor.execute('SELECT * FROM md_devices')
        names = [description[0] for description in self.cursor.description]
        print('The current md devices\n')
        for row in self.cursor.fetchall():
            print(names)
            print(row)

        self.cursor.execute('SELECT * FROM multipath_devices')
        names = [description[0] for description in self.cursor.description]
        print('The current multipath devices\n')
        for row in self.cursor.fetchall():
            print(names)
            print(row)

        self.cursor.execute('SELECT * FROM physical_drives')
        names = [description[0] for description in self.cursor.description]
        print('The current physical drive devices\n')
        for row in self.cursor.fetchall():
            print(names)
            print(row)

        self.cursor.execute('SELECT * FROM sd_devices')
        names = [description[0] for description in self.cursor.description]
        print("This is the current list of sd devices.")
        for row in self.cursor.fetchall():
            print(names)
            print(row)
        input('Press any key to exit')

    def process_disks_inventory(self):
        if self.debug == 'light': print('entering process disks enclosures')
        inventory = scan_scsi_bus()
        for chassis in inventory.simple_chassis:
            self.add_device_generic(inventory.simple_chassis[chassis])
        for encl in inventory.simple_sas_enclosures:
            self.add_device_generic(inventory.simple_sas_enclosures[encl])
        for pd in inventory.simple_physical_drives:
            self.add_device_generic(inventory.simple_physical_drives[pd])
        for md in inventory.simple_mds:
            self.add_device_generic(inventory.simple_mds[md])
        for dm in inventory.simple_mpaths:
            self.add_device_generic(inventory.simple_mpaths[dm])
        for sd in inventory.simple_scsi_sds:
            self.add_device_generic(inventory.simple_scsi_sds[sd])



    def record_change(self,object_type,entry='Something changed but I don\'t know what'):#function to write log entries describing he change in records
        #insert code here to record changes for relevant fields when overwritten. This might simply be logging the changes to a certain table.
        if self.debug: print('Entering the record change function')
        log_file = self.log_files[object_type]
        if self.debug: print(object_type,log_file,type(log_file))
        if self.debug: print('-------------------------------------')
        if self.debug: print(object_type,log_file,type(log_file))
        entry=str(datetime.datetime.now())+'-----'+entry+'\n'
        if self.debug: print('I am inside the record change function and the logfile is ', log_file)
        log_file.write(entry)
        self.general_log.write(entry)

    def update_record(self,values,names,row):
        if self.debug: print('\nEntering the update_record function')
        values = values
        if self.debug: print(values)
        names = names
        if self.debug: print(names)
        row = [item for item in row]
        if self.debug: print(row)
        key = names[1]
        key_value = values[0]
        param_dict = {} #This is a dictionary to hold the parameter names and '?'s this allows us to construct dynamic  update statements for any number of fields
        if self.debug: print('content of values',values)
        if self.debug: print('content of row',row)
        if self.debug: print('content of names',names)
        if values == row:
            return
        for value in values:
            idx = values.index(value)
            if value == row[idx]:
                if self.debug: print('The value is the same value=',value,row[idx])
                continue
            elif value != row[idx]:
                if self.debug: print('the value is different',value,row[idx])
                param_dict[names[idx]] = value
        log_string = 'The record with key '+str(key)+'='+str(key_value)+' has been updated. Changes are as follows: \n '
        for change in param_dict:
            if self.debug: print('I am trying to add a value for \'change\' in param_dict. that change is :',change)
            log_string += 'Field '+str(change)+' updated from '+str(row[names.index(change)])+' to '+str(param_dict[change])
            if self.debug: print(log_string)
        update_string = "UPDATE " + self.tables[key] + ' SET '
        update_substring = ''
        update_values = []
        for change in param_dict:
            update_substring += '\''+str(change)+'\' = ?,'
            update_values.append(param_dict[change])
        if self.debug: print('this is the update substring before:', update_substring)
        update_substring = update_substring.rstrip(',')
        if self.debug: print('this is the update substring after: ', update_substring)
        update_string += update_substring
        update_string += ' WHERE \''+str(key)+'\' = ?'
        update_values.append(key_value)
        if self.debug: print('\nThis is the log strings',log_string)
        if self.debug: print('\nThis is the update string\n',update_string)
        if self.debug: print('This is the log file',self.log_files[key])
        self.record_change(key,log_string)
        self.cursor.execute(update_string,update_values)
        self.conn.commit()
        if self.debug: print('Leaving the update record function')

    def add_device_generic(self,my_device_simple):
        if self.debug: print('Starting add device of type ',type(my_device_simple))
        self.cursor.execute('SELECT * FROM '+self.tables[type(my_device_simple)])
        my_device_simple.attributes, names = self.verify_attributes(my_device_simple.attributes)
        key = names[1]
        values = [my_device_simple.attributes[name] for name in names]
        for row in self.cursor:
            if row[1] == my_device_simple.attributes[key]:
                self.update_record(values,names,row)
                return
        try:
            params = self.param_string_gen(len(names))
        except Exception as e:
            print('failed to find param length string')
            params = None
            print(e)
            exit(1)
        try:
            if params is None: raise Exception('There is nothing in the params string, so skipping attempt at insert.')
            insert_string = 'INSERT INTO '+self.tables[key]+' VALUES'+params
            if self.debug: print(insert_string)
            if self.debug: print(values)
            self.cursor.execute(insert_string,values)
            log_string = 'Inserting the following item into table '+str(self.tables[key])
            self.record_change(type(my_device_simple),log_string)
            self.conn.commit()
        except Exception as e:
            print('failed trying to insert parameters')
            print(e)
            exit(1)


    def verify_attributes(self,attributes={}):#must be run after select statements from relevant source
        fields_to_update = {}
        names = [description[0] for description in self.cursor.description]
        key = names[1]
        for item in attributes:
            if item in names:
                fields_to_update[item] = attributes[item]
            else:
                if self.debug: print('Tried to pass an attribute called',item,'that does not have a corresponding column in table '+self.tables[key]+' Ignoring.')
        for name in names:
            if name not in fields_to_update:
                fields_to_update[name] = None
        return fields_to_update, names
    def param_string_gen(self,count):#allows a variable number of parameters while still protecting against sql injection attacks.
        param_str = '('
        param_str = param_str+'?,'*count
        param_str = param_str.rstrip(',')
        param_str = param_str+')'
        return param_str

    def cleanup(self):
        self.general_log.write(str(datetime.datetime.now()) + '----------Ending run of database writer.py\n')
        self.md_log.close()
        self.dm_log.close()
        self.sd_log.close()
        self.physical_drives_log.close()
        self.general_log.close()
        self.conn.close()
        self.chassis_log.close()

#writer = database_writer(debug=True)