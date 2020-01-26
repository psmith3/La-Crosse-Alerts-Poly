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
        self.name = 'La Crosse'
        self.url_api = 'http://decent-destiny-704.appspot.com/laxservices/user-api.php?'
        self.url_login = 'https://decent-destiny-704.appspot.com/laxservices/user-api.php?pkey=Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe&action=userlogin'
        self.discovery = False
        self.poly.onConfig(self.process_config)

    def start(self):

        # This grabs the server.json data and checks profile_version is up to date
        serverdata = self.poly.get_server_data()
        LOGGER.info('Started La Crosse Alerts Poly NodeServer {}'.format(serverdata['version']))
        self.heartbeat(0)
        self.check_params()
        #self.discover()
        self.poly.add_custom_config_docs("")
        self.discover()


    def shortPoll(self):

        pass
        #LOGGER.debug('shortPoll')

    def longPoll(self):

        LOGGER.debug('longPoll')
        LOGGER.info('Getting Device Data')

        PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':self.userSKey, 'action':"refreshdeviceinfo"}
        r1 = requests.get(url = self.url_api, params = PARAMS)
        devicedata = r1.json()
        gateway = devicedata['device0']['assocGateway']
        GW_PARAMS = {'gatewayid':gateway, 'pkey':'Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe','action':'getGatewayInfo'}
        gw = requests.get(url = self.url_api, params = GW_PARAMS)
        gwdata = gw.json()

        #determine gateway lastseen time in minutes from current time
        str = gwdata[0]
        d = dict(x.split("=") for x in str.split(","))
        gwls = d['lastseen']
        ct = (time.time())
        diff = int(ct)-int(gwls)
        diff_mins = int(diff/60)
        self.setDriver('GV1', diff_mins)

        #determine online / offline status for gateway
        if diff_mins > 5:
            self.setDriver('GV0', 0)
            LOGGER.info('Gateway offline')
        else:
            self.setDriver('GV0', 1)
            LOGGER.info('Gateway Online')

        LOGGER.info('Gateway last seen {} mins ago'.format(diff_mins))


        for node in self.nodes:
            if self.nodes[node].id == 'device0node':
                device0name = (devicedata['device0']['device_name'])
                device0parent = devicedata['device0']
                device0data = devicedata['device0']['obs'][0]
                self.set_driver(node, 'ST', device0data, 'ambient_temp')
                self.set_driver(node, 'GV0', device0data, 'probe_temp')
                self.set_driver(node, 'GV1', device0data, 'humidity')
                self.set_driver(node, 'GV2', device0data, 'linkquality')
                self.set_driver(node, 'GV3', device0data, 'lowbattery')

                #determine device0 lastseen time in minutes from current time
                dev0ls = (devicedata['device0']['obs'][0]['u_timestamp'])
                ct = (time.time())
                dev0diff = int(ct)-int(dev0ls)
                dev0diff_mins = int(dev0diff/60)
                lastseen0 = {"dev0diff_mins":dev0diff_mins}

                #determine online / offline status for device0
                if dev0diff_mins > 60:
                    statusdata0 = {"status":"0"}
                    LOGGER.info(f'{device0name} Offline')
                else:
                    statusdata0 = {"status":"1"}
                    LOGGER.info(f'{device0name} Online')

                self.set_driver(node, 'GV4', statusdata0, 'status')
                self.set_driver(node, 'GV5', lastseen0, 'dev0diff_mins')
                self.set_driver(node, 'GV6', device0parent, 'interval')

            if self.nodes[node].id == 'device1node':
                device1name = (devicedata['device1']['device_name'])
                device1parent = devicedata['device1']
                device1data = devicedata['device1']['obs'][0]
                self.set_driver(node, 'ST', device1data, 'ambient_temp')
                self.set_driver(node, 'GV0', device1data, 'probe_temp')
                self.set_driver(node, 'GV1', device1data, 'humidity')
                self.set_driver(node, 'GV2', device1data, 'linkquality')
                self.set_driver(node, 'GV3', device1data, 'lowbattery')

                #determine device1 lastseen time in minutes from current time
                dev1ls = (devicedata['device1']['obs'][0]['u_timestamp'])
                ct = (time.time())
                dev1diff = int(ct)-int(dev1ls)
                dev1diff_mins = int(dev1diff/60)
                lastseen1 = {"dev1diff_mins":dev1diff_mins}

                #determine online / offline status for device1
                if dev1diff_mins > 60:
                    statusdata1 = {"status":"0"}
                    LOGGER.info(f'{device1name} Offline')
                else:
                    statusdata1 = {"status":"1"}
                    LOGGER.info(f'{device1name} Online')

                self.set_driver(node, 'GV4', statusdata1, 'status')
                self.set_driver(node, 'GV5', lastseen1, 'dev1diff_mins')
                self.set_driver(node, 'GV6', device1parent, 'interval')

    def set_driver(self, node, driver, data, index):
        try:
            self.nodes[node].setDriver(driver, data[index],
                    report = True, force = True)
        except (ValueError, KeyError, TypeError):
            LOGGER.warning('Missing data: ' + index)

    def query(self,command=None):

        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

        self.parent.longPoll()

    def discover(self, *args, **kwargs):

        self.discovery = True
        payload = {'iLogEmail':self.email,'iLogPass':self.password}
        LOGGER.info(payload)
        r = requests.post(self.url_login, data=payload)
        pastebin_url = r.text
        data = r.json()

        if "result" in data:
            LOGGER.info('Login Failed. Check email address and password')
            self.addNotice('Login Failed. Check email address and password')
            polyglot.stop()

        else:
            self.removeNoticesAll()
            self.addNotice('Connected to La Crosse Alerts Mobile server')
            userSKey = data["sessionKey"]
            self.userSKey = userSKey
            LOGGER.info('Getting Gateway & Device Data')
            PARAMS = {'pkey':"Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe",'ref':userSKey, 'action':"refreshdeviceinfo"}
            r1 = requests.get(url = self.url_api, params = PARAMS)
            devicedata = r1.json()
            gateway = devicedata['device0']['assocGateway']
            GW_PARAMS = {'gatewayid':gateway, 'pkey':'Dyd7kC4wxLDFz0rQ6W5T28DPgrM6SOBe','action':'getGatewayInfo'}
            gw = requests.get(url = self.url_api, params = GW_PARAMS)
            gwdata = gw.json()
            str = gwdata[0]
            d = dict(x.split("=") for x in str.split(","))
            gwls = d['lastseen']
            ct = (time.time())
            diff = int(ct)-int(gwls)
            diff_mins = int(diff/60)
            self.setDriver('GV1', diff_mins)

            if diff_mins > 5:
                self.setDriver('GV0', 0) # offline
                LOGGER.info('Gateway offline')
            else:
                self.setDriver('GV0', 1) # online
                LOGGER.info('Gateway Online')

            LOGGER.info('Gateway last seen {} mins ago'.format(diff_mins))

        if 'device0' in devicedata:
            device0name = (devicedata['device0']['device_name'])
            LOGGER.info(f'Adding device0 node for {device0name} sensor')
            self.addNode(device0node(self, self.address, 'device0node', device0name))

        if 'device1' in devicedata:
            device1name = (devicedata['device1']['device_name'])
            LOGGER.info(f'Adding device1 node for {device1name} sensor')
            self.addNode(device1node(self, self.address, 'device1node', device1name))

        if 'device2' in devicedata:
            device2name = (devicedata['device2']['device_name'])
            LOGGER.info(f'Adding device1 node for {device2name} sensor')
            self.addNode(device2node(self, self.address, 'device2node', device2name))

        if 'device3' in devicedata:
            device3name = (devicedata['device3']['device_name'])
            LOGGER.info(f'Adding device3 node for {device3name} sensor')
            self.addNode(device3node(self, self.address, 'device3node', device3name))

        if 'device4' in devicedata:
            device4name = (devicedata['device4']['device_name'])
            LOGGER.info(f'Adding device4 node for {device4name} sensor')
            self.addNode(device4node(self, self.address, 'device4node', device4name))

        self.parent.longPoll()


    def delete(self):

        LOGGER.info('Deleting NS')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        # this seems to get called twice for every change, why?
        # What does config represent?
        LOGGER.info("process_config: Enter config={}".format(config));
        LOGGER.info("process_config: Exit");

    def heartbeat(self,init=False):
        LOGGER.debug('heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def check_params(self):

        self.removeNoticesAll()
        default_user = "<Your La Crosse Email>"
        default_password = "<Your La Crosse Password>"
        if 'email' in self.polyConfig['customParams']:
            self.email = self.polyConfig['customParams']['email']
        else:
            self.email = default_user
            LOGGER.error('check_params: email address not defined in customParams, please add it. Using {}'.format(self.email))
            st = False

        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            self.password = default_password
            LOGGER.error('check_params: password not defined in customParams, please add it. Using {}'.format(self.password))
            st = False
        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'email': self.email})

        # Add a notice if they need to change the user/password from the default.
        if self.email == default_user or self.password == default_password:
            # This doesn't pass a key to test the old way.
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
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile
    }


    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2}, # NS status
        {'driver': 'GV0', 'value': 0, 'uom': 2}, # Gateway status
        {'driver': 'GV1', 'value': 0, 'uom': 45}  # Gateway last seen
        ]

class device0node(polyinterface.Node):

    def __init__(self, controller, primary, address, name):

        super(device0node, self).__init__(controller, primary, address, name)

    def start(self):

        self.setDriver('ST', 1)
        pass

    def shortPoll(self):
        LOGGER.debug('shortPoll')

    def longPoll(self):
        LOGGER.debug('longPoll')

    def setOn(self, command):

        self.setDriver('ST', 1)

    def setOff(self, command):

        self.setDriver('ST', 0)

    def query(self,command=None):

        self.reportDrivers()
        self.parent.longPoll()


    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'GV0', 'value': 0, 'uom': 17}, #probe_temp
            {'driver': 'GV1', 'value': 0, 'uom': 22}, #humidity
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'GV3', 'value': 0, 'uom': 2}, #lowbattery
            {'driver': 'GV4', 'value': 0, 'uom': 2}, #online
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45} #interval
            ]

    id = 'device0node'

    commands = {
                    'QUERY': query
                }

class device1node(polyinterface.Node):

    def __init__(self, controller, primary, address, name):

        super(device1node, self).__init__(controller, primary, address, name)

    def start(self):

        self.setDriver('ST', 1)
        pass

    def shortPoll(self):
        LOGGER.debug('shortPoll')

    def longPoll(self):
        LOGGER.debug('longPoll')

    def setOn(self, command):

        self.setDriver('ST', 1)

    def setOff(self, command):

        self.setDriver('ST', 0)

    def query(self,command=None):

        self.reportDrivers()
        self.parent.longPoll()

    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'GV0', 'value': 0, 'uom': 17}, #probe_temp
            {'driver': 'GV1', 'value': 0, 'uom': 22}, #humidity
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'GV3', 'value': 0, 'uom': 2}, #lowbattery
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45} #interval
            ]

    id = 'device1node'

    commands = {
                    'QUERY': query
                }

class device2node(polyinterface.Node):

    def __init__(self, controller, primary, address, name):

        super(device2node, self).__init__(controller, primary, address, name)

    def start(self):

        self.setDriver('ST', 1)
        pass

    def shortPoll(self):
        LOGGER.debug('shortPoll')

    def longPoll(self):
        LOGGER.debug('longPoll')

    def setOn(self, command):

        self.setDriver('ST', 1)

    def setOff(self, command):

        self.setDriver('ST', 0)

    def query(self,command=None):

        self.reportDrivers()
        self.parent.longPoll()


    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'GV0', 'value': 0, 'uom': 17}, #probe_temp
            {'driver': 'GV1', 'value': 0, 'uom': 22}, #humidity
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'GV3', 'value': 0, 'uom': 2}, #lowbattery
            {'driver': 'GV4', 'value': 0, 'uom': 2}, #online
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45} #interval
            ]

    id = 'device2node'

    commands = {
                    'QUERY': query
                }

class device3node(polyinterface.Node):

    def __init__(self, controller, primary, address, name):

        super(device3node, self).__init__(controller, primary, address, name)

    def start(self):

        self.setDriver('ST', 1)
        pass

    def shortPoll(self):
        LOGGER.debug('shortPoll')

    def longPoll(self):
        LOGGER.debug('longPoll')

    def setOn(self, command):

        self.setDriver('ST', 1)

    def setOff(self, command):

        self.setDriver('ST', 0)

    def query(self,command=None):

        self.reportDrivers()
        self.parent.longPoll()


    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'GV0', 'value': 0, 'uom': 17}, #probe_temp
            {'driver': 'GV1', 'value': 0, 'uom': 22}, #humidity
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'GV3', 'value': 0, 'uom': 2}, #lowbattery
            {'driver': 'GV4', 'value': 0, 'uom': 2}, #online
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45} #interval
            ]

    id = 'device3node'

    commands = {
                    'QUERY': query
                }

class device4node(polyinterface.Node):

    def __init__(self, controller, primary, address, name):

        super(device4node, self).__init__(controller, primary, address, name)

    def start(self):

        self.setDriver('ST', 1)
        pass

    def shortPoll(self):
        LOGGER.debug('shortPoll')

    def longPoll(self):
        LOGGER.debug('longPoll')

    def setOn(self, command):

        self.setDriver('ST', 1)

    def setOff(self, command):

        self.setDriver('ST', 0)

    def query(self,command=None):

        self.reportDrivers()
        self.parent.longPoll()


    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 17}, #ambient temp
            {'driver': 'GV0', 'value': 0, 'uom': 17}, #probe_temp
            {'driver': 'GV1', 'value': 0, 'uom': 22}, #humidity
            {'driver': 'GV2', 'value': 0, 'uom': 51}, #linkquality
            {'driver': 'GV3', 'value': 0, 'uom': 2}, #lowbattery
            {'driver': 'GV4', 'value': 0, 'uom': 2}, #online
            {'driver': 'GV5', 'value': 0, 'uom': 45}, #lastseen
            {'driver': 'GV6', 'value': 0, 'uom': 45} #interval
            ]

    id = 'device4node'

    commands = {
                    'QUERY': query
                }


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
