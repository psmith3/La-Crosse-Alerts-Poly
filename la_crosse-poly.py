#!/usr/bin/env python
"""
This is a La Crosse Alerts Poly NodeServer for Polyglot v2 written in Python2/3
by Parker Smith (psmith3) parker@parker3.com.
La Crosse Alerts Poly Node Server. Integrates La Crosse Alerts from wireless temperature & humidity sensors and allows monitoring of
1 gateway and up to 5 sensors. ISY integration provides Ambient Temperature, Probe Temperature & Relative Humidity;
Time Last Seen in minutes; Gateway & sensor online status; RF Link Quality; Low Battery Alerts.
Set alerts for any available attributes such as low battery, connection loss, and min / max alerts for temperature and humidity.
No subscription required and data is pulled from API for Basic Lifetime subscription included with La Crosse devices.
"""
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import requests
import json

LOGGER = polyinterface.LOGGER

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):

        super(Controller, self).__init__(polyglot)
        self.name = 'La Crosse Controller'
        self.url_api = 'http://decent-destiny-704.appspot.com/laxservices/user-api.php?'
        self.url_login = 'https://decent-destiny-704.appspot.com/laxservices/user-api.php?pkey=Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe&action=userlogin'
        self.devices = '0'
        self.discovery = False
        self.poly.onConfig(self.process_config)

    def start(self):

        # This grabs the server.json data and checks profile_version is up to date
        serverdata = self.poly.get_server_data()
        LOGGER.info('Started La Crosse Alerts Poly NodeServer {}'.format(serverdata['version']))
        #self.heartbeat(0)
        self.check_params()
        self.poly.add_custom_config_docs("")
        self.discover()


    def shortPoll(self):

        pass


    def longPoll(self):
        LOGGER.info('Getting Device Data from Controller longPoll')
        PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':self.userSKey, 'action':"refreshdeviceinfo"}
        try:
            r1 = requests.get(url = self.url_api, params = PARAMS)
            devicedata = r1.json()
        except Exception as err:
            LOGGER.error('Excption: {0}'.format(err), exc_info=True)
            return
        for devKey in devicedata.keys():
            if "device" in devKey:
                dev = devicedata[devKey]
                obs = dev["obs"][0]
                name = dev["device_name"]
                temp = obs["ambient_temp"]
                probeTemp = obs["probe_temp"]
                humidity = obs["humidity"]
                devtype = obs["device_type"]
                nodeid = obs["device_id"].strip("0").lower()
                deviceid = obs["device_id"].strip("0")
                linkquality = obs["linkquality"]
                lowbattery = obs["lowbattery"]
                gateway = dev["assocGateway"]
                interval = dev['interval']
                utctime = obs['utctime']

                #Determine Device Status and Last Seen time in minutes
                ct = (time.time())
                devdiff = int(ct)-int(utctime)
                devdiff_mins = int(devdiff/60)
                if devdiff_mins > int(interval):
                    statusdata = 0
                    LOGGER.info(f'{name} Offline')
                else:
                    statusdata = 1
                    LOGGER.info(f'{name} Online')

                LOGGER.info(f'Updating {name} Temp: {temp}')
                LOGGER.info(f'Updating {name} Probe Temp: {probeTemp}')
                LOGGER.info(f'Updating {name} Humidity: {humidity}%')
                LOGGER.info(f'Updating {name} Link Quality: {linkquality}%')
                LOGGER.info(f'Updating {name} Low Battery: {lowbattery}')
                LOGGER.info(f'Updating {name} Sensor Interval: {interval} minutes')
                LOGGER.info(f'Updating {name} Sensor Last Seen: {devdiff_mins} minutes')
                LOGGER.info('')
                if lowbattery == 1:
                    batstat = 10
                    LOGGER.info(f'Replace {name} Battery Soon')
                else:
                    batstat = 13
                    LOGGER.info(f'{name} Battery Is Fully Charged')

                #Determine Gateway Status and Last Seen time in minutes
                GW_PARAMS = {'gatewayid':gateway, 'pkey':'Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe','action':'getGatewayInfo'}
                gateway = gateway.strip("0")
                try:
                    gw = requests.get(url = self.url_api, params = GW_PARAMS)
                    gwdata = gw.json()
                except Exception as err:
                    LOGGER.error('Excption: {0}'.format(err), exc_info=True)
                    return
                str = gwdata[0]
                d = dict(x.split("=") for x in str.split(","))
                ls = d['lastseen']
                ct = (time.time())
                diff = int(ct)-int(ls)
                diff_mins = int(diff/60)
                if diff_mins > 5:
                    checkGateway = 0 # offline
                    LOGGER.info(f'{name} Gateway {gateway} offline')
                else:
                    checkGateway = 1 # online
                    LOGGER.info(f'{name} Gateway {gateway} last seen {diff_mins} mins ago')

                for node in self.nodes:
                    if self.nodes[node].address == f't{nodeid}':
                        self.set_driver(node, 'ST', temp)
                        self.set_driver(node, 'CLIHUM', humidity)
                        self.set_driver(node, 'GV2', linkquality)
                        self.set_driver(node, 'BATLVL', batstat)
                        self.set_driver(node, 'GV4', statusdata)
                        self.set_driver(node, 'GV5', devdiff_mins)
                        self.set_driver(node, 'GV6', interval)
                        self.set_driver(node, 'GV7', interval)
                        self.set_driver(node, 'BATLVL', batstat)
                        self.set_driver(node, 'GV0', gateway) #associated gateway
                        self.set_driver(node, 'GV1', diff_mins) #gateway last seen
                        self.set_driver(node, 'GV3', checkGateway) #gateway online status

                    if self.nodes[node].address == f'h{nodeid}':
                        self.set_driver(node, 'ST', humidity)

                    if self.nodes[node].address == f'p{nodeid}':
                        self.set_driver(node, 'ST', probeTemp)

                    if self.nodes[node].address == f'w{nodeid}':
                        self.set_driver(node, 'ST', probeTemp)

    def set_driver(self, node, driver, data):
        try:
            self.nodes[node].setDriver(driver, data,
                    report = True, force = True)
        except (ValueError, KeyError, TypeError):
            LOGGER.warning('Missing data: ')

    def query(self,command=None):

        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

        self.parent.longPoll()

    def discover(self, *args, **kwargs):

        self.discovery = True
        payload = {'iLogEmail':self.email,'iLogPass':self.password}
        LOGGER.info(payload)
        try:
            r = requests.post(self.url_login, data=payload)
            pastebin_url = r.text
            data = r.json()
        except Exception as err:
            LOGGER.error('Excption: {0}'.format(err), exc_info=True)
            return

        if "result" in data:
            LOGGER.info('Login Failed. Check email address and password')
            self.addNotice('Login Failed. Check email address and password')
            polyglot.stop()

        else:
            self.removeNoticesAll()
            self.addNotice('Connected to La Crosse Alerts Mobile server')
            self.setDriver('GV0', 1)
            userSKey = data["sessionKey"]
            self.userSKey = userSKey
            LOGGER.info('Getting Gateway & Device Data')
            PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':self.userSKey, 'action':"refreshdeviceinfo"}
            try:
                r1 = requests.get(url = self.url_api, params = PARAMS)
                devicedata = r1.json()
            except Exception as err:
                LOGGER.error('Excption: {0}'.format(err), exc_info=True)
                return

            for devKey in devicedata.keys():
                if "device" in devKey:
                    dev = devicedata[devKey]
                    obs = dev["obs"][0]
                    unit = dev["unit"]
                    name = dev["device_name"]
                    temp = obs["ambient_temp"]
                    probeTemp = obs["probe_temp"]
                    humidity = obs["humidity"]
                    devtype = obs["device_type"]
                    nodeid = obs["device_id"].strip("0").lower()
                    gateway = dev["assocGateway"]
                    LOGGER.info(f'Found {devtype}: {name}')
                    self.addNode(device_tempnode(self, self.address, f't{nodeid}', f'{name} Temperature', devicedata[devKey]))
                    self.addNode(device_humiditynode(self, f't{nodeid}', f'h{nodeid}', f'{name} Humidity', devicedata[devKey]))
                    if probeTemp == 'N/C':
                        LOGGER.info(f'{name} Probe not found')

                    else:
                        self.addNode(device_probetempnode(self, f't{nodeid}', f'p{nodeid}', f'{name} Probe Temp', devicedata[devKey]))
                        LOGGER.info(f'{name} Probe Temp node added')

                    if "wet" in unit:
                        self.addNode(device_wetnode(self, f't{nodeid}', f'w{nodeid}', f'{name} Water Detector', devicedata[devKey]))
                        LOGGER.info(f'{name} Wet node added')

            LOGGER.info('Total Device Count Discovered: {}'.format(len(devicedata.keys())-1))
            devices = (len(devicedata.keys())-1)
            self.setDriver('GV1', devices)

    def delete(self):
        LOGGER.info('Deleting NS')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        LOGGER.info("process_config: Enter config={}".format(config));
        LOGGER.info("process_config: Exit");

    #def heartbeat(self,init=False):
    #    LOGGER.debug('heartbeat: init={}'.format(init))
    #    if init is not False:
    #        self.hb = init
    #    LOGGER.debug('heartbeat: hb={}'.format(self.hb))
    #    if self.hb == 0:
    #        self.reportCmd("DON",2)
    #        self.hb = 1
    #    else:
    #        self.reportCmd("DOF",2)
    #        self.hb = 0

    def check_params(self):
        self.removeNoticesAll()
        default_user = "<Your La Crosse Email>"
        default_password = "<Your La Crosse Password>"
        if 'email' in self.polyConfig['customParams']:
            self.email = self.polyConfig['customParams']['email']
        else:
            self.email = default_user
            LOGGER.error(f'check_params: email address not defined in customParams, please add it. Using {self.email}')
            st = False

        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            self.password = default_password
            LOGGER.error(f'check_params: password not defined in customParams, please add it. Using {self.password}')
            st = False
        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'email': self.email})

        # Add a notice if they need to change the user/password from the default.
        if self.email == default_user or self.password == default_password:
            self.addNotice('Please configure La Crosse email address and password in configuration page, and restart this nodeserver')
            polyglot.stop()

    def remove_notice_test(self,command):
        LOGGER.info('remove_notice_test: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNotice('test')

    def remove_notices_all(self,command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self,command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st


    id = 'controller'
    hint = 0xffffff
    commands = {
        'QUERY': query,
        'DISCOVER': discover
    }

    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2}, # NS status
        {'driver': 'GV0', 'value': 0, 'uom': 2}, # La Crosse Account Connection Status
        {'driver': 'GV1', 'value': 0, 'uom': 70}  # number of devices found
        ]

class device_tempnode(polyinterface.Node):

    def __init__(self, controller, primary, address, name, devicedata):
        super(device_tempnode, self).__init__(controller, address, address, name)
        self.isPrimary = True
        self.devicedata = devicedata

    def start(self):
        LOGGER.info('Starting Node Start Section')
        dev = self.devicedata
        name = dev["device_name"]
        obs = dev["obs"][0]
        temp = obs["ambient_temp"]
        probeTemp = obs["probe_temp"]
        humidity = obs["humidity"]
        devtype = obs["device_type"]
        deviceid = obs["device_id"]
        self.deviceid = deviceid
        nodeid = dev["device_name"].replace(" ", "").lower()
        linkquality = obs["linkquality"]
        lowbattery = obs["lowbattery"]
        gateway = dev["assocGateway"]
        interval = dev['interval']
        utctime = obs['utctime']
        ct = (time.time())
        devdiff = int(ct)-int(utctime)
        devdiff_mins = int(devdiff/60)
        LOGGER.info(name)
        LOGGER.info(devtype)
        if devdiff_mins > 60:
            statusdata = 0
            LOGGER.info(f'{name} Offline')
        else:
            statusdata = 1
            LOGGER.info(f'{name} Online')
        self.setDriver('GV4', statusdata)
        LOGGER.info(f'Setting {name} Temp: {temp}')
        self.setDriver('ST', temp)
        LOGGER.info(f'Setting {name} Humidity: {humidity}%')
        self.setDriver('CLIHUM', humidity)
        LOGGER.info(f'Setting {name} Link Quality: {linkquality}%')
        self.setDriver('GV2', linkquality)
        LOGGER.info(f'Setting {name} Low Battery: {lowbattery}')
        LOGGER.info(f'Setting {name} Sensor Interval: {interval} minutes')
        self.setDriver('GV6', interval)
        self.setDriver('GV7', interval)
        LOGGER.info(f'Setting {name} Sensor Last Seen: {devdiff_mins} minutes')
        self.setDriver('GV5', devdiff_mins)
        if lowbattery == 1:
            batstat = 10
            LOGGER.info(f'Replace {name} Battery Soon')
        else:
            batstat = 13
            LOGGER.info(f'{name} Battery Is Fully Charged')
        self.setDriver('BATLVL', batstat)
        LOGGER.info('')
        GW_PARAMS = {'gatewayid':gateway, 'pkey':'Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe','action':'getGatewayInfo'}
        gateway = gateway.strip("0")
        try:
            gw = requests.get(url = self.controller.url_api, params = GW_PARAMS)
            gwdata = gw.json()
        except Exception as err:
            LOGGER.error('Excption: {0}'.format(err), exc_info=True)
            return
        str = gwdata[0]
        d = dict(x.split("=") for x in str.split(","))
        ls = d['lastseen']
        ct = (time.time())
        diff = int(ct)-int(ls)
        diff_mins = int(diff/60)
        if diff_mins > 5:
            checkGateway = 0 # offline
            LOGGER.info(f'{name} Gateway {gateway} offline')
        else:
            checkGateway = 1 # online
            LOGGER.info(f'{name} Gateway {gateway} last seen {diff_mins} mins ago')

        LOGGER.info(f'Setting {name} Associated Gateway: {gateway}')
        self.setDriver('GV0', gateway)
        self.setDriver('GV1', diff_mins) #set gateway last seen
        self.setDriver('GV3', checkGateway) #set gateway online status
        LOGGER.info(f'{name} Device ID: {deviceid}')

    def query(self,command=None):
        self.reportDrivers()
        self.parent.longPoll()

    def dev_interval(self, command):

        val = int(command.get('value'))
        LOGGER.info(f'Sensor interval changed to {val} minutes')
        dev = self.devicedata
        obs = dev["obs"][0]
        name = dev["device_name"]
        deviceid = obs["device_id"]
        PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':self.controller.userSKey, 'action':"refreshdeviceinfo"}
        try:
            r1 = requests.get(url = self.controller.url_api, params = PARAMS)
            devicedata = r1.json()
        except Exception as err:
            LOGGER.error('Excption: {0}'.format(err), exc_info=True)
            return
        SENSOR_PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':self.controller.userSKey,'sensor':deviceid, 'action':'setsensorinterval','interval':val}
        try:
            r2 = requests.get(url = self.controller.url_api, params = SENSOR_PARAMS)
        except Exception as err:
            LOGGER.error('Excption: {0}'.format(err), exc_info=True)
            return
        LOGGER.info(f'Changing {name} Device ID {deviceid} Sensor interval changed to {val} minutes')
        self.setDriver('GV7', val)
        self.parent.longPoll()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'CLIHUM', 'value': 0, 'uom': 22}, #humiidty
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'BATLVL', 'value': 0, 'uom': 93}, #lowbattery
            {'driver': 'GV4', 'value': 0, 'uom': 2}, #online
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45}, #interval
            {'driver': 'GV7', 'value': 0, 'uom': 45}, #dev_interval
            {'driver': 'GV0', 'value': 0, 'uom': 25}, #associated gateway
            {'driver': 'GV1', 'value': 0, 'uom': 45}, #gateway lastseen
            {'driver': 'GV3', 'value': 0, 'uom': 2}] #gateway online


    commands = {
        'INTERVAL': dev_interval,
        'QUERY': query
    }

    id = 'device_tempnode'
    hint = 0xffffff

class device_probetempnode(polyinterface.Node):

    def __init__(self, controller, primary, address, name, devicedata):
        super(device_probetempnode, self).__init__(controller, primary, address, name)
        self.devicedata = devicedata

    def start(self):
        LOGGER.info('Starting Probe Temp Node Start Section')
        dev = self.devicedata
        name = dev["device_name"]
        obs = dev["obs"][0]
        probeTemp = obs["probe_temp"]
        nodeid = dev["device_name"].replace(" ", "").lower()
        LOGGER.info(name)
        LOGGER.info(f'Setting {name} Probe Temp: {probeTemp}')
        LOGGER.info('')
        self.setDriver('ST', probeTemp)

    def query(self,command=None):
        self.reportDrivers()
        self.parent.longPoll()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 17}] #probe temp

    commands = {
        'QUERY': query
    }

    id = 'device_probetempnode'
    hint = 0xffffff

class device_humiditynode(polyinterface.Node):

    def __init__(self, controller, primary, address, name, devicedata):
        super(device_humiditynode, self).__init__(controller, primary, address, name)
        self.devicedata = devicedata

    def start(self):
        LOGGER.info('Starting Humidity Node Start Section')
        dev = self.devicedata
        obs = dev["obs"][0]
        name = dev["device_name"]
        humidity = obs["humidity"]
        LOGGER.info(name)
        LOGGER.info(f'Setting {name} Humidity: {humidity}')
        LOGGER.info('')
        self.setDriver('ST', humidity)

    def query(self,command=None):
        self.reportDrivers()
        #self.parent.longPoll()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 22}] #humidity

    commands = {
        'QUERY': query
    }

    id = 'device_humiditynode'
    hint = 0xffffff

class device_wetnode(polyinterface.Node):

    def __init__(self, controller, primary, address, name, devicedata):
        super(device_wetnode, self).__init__(controller, primary, address, name)
        self.devicedata = devicedata

    def start(self):
        LOGGER.info('Starting Wet Node Start Section')
        dev = self.devicedata
        name = dev["device_name"]
        obs = dev["obs"][0]
        probeTemp = obs["probe_temp"]
        LOGGER.info(name)
        LOGGER.info(f'Setting {name} Water Detector Status: {probeTemp}')
        LOGGER.info('')
        self.setDriver('ST', probeTemp)

    def query(self,command=None):
        self.reportDrivers()
        self.parent.longPoll()


    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}] #Water Detected

    commands = {
        'QUERY': query
    }

    id = 'device_wetnode'
    hint = 0xffffff

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('La Crosse')

        polyglot.start()

        control = Controller(polyglot)

        control.runForever()

    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)
