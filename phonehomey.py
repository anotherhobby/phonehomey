# standard libs
import importlib
import itertools
import logging
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
# pip installs
import netaddr
import netifacese
import requests
import yaml
import ipaddress


def setup_logger(name, log_level='DEBUG', log_file=False, std_out=False):
    ''' create loggers for phonehomey '''
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
    if std_out:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
    if log_level == 'DEBUG':
        if log_file:
            file_handler.setLevel(logging.DEBUG)
        if std_out:
            stream_handler.setLevel(logging.DEBUG)
    else:
        if log_file:
            file_handler.setLevel(logging.INFO)
        if std_out:
            stream_handler.setLevel(logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if std_out:
        logger.addHandler(stream_handler)
    if log_file:
        logger.addHandler(file_handler)
    return logger


class silentPingThread(threading.Thread):
    ''' used to background ping processes using threading for fast ping scanning '''
    def __init__(self, ipaddress, timeout):
        threading.Thread.__init__(self)
        self.ipaddress = ipaddress
        self.timeout = timeout
    def run(self):
        subprocess.Popen(
            ["ping", "-c 1", self.timeout, str(self.ipaddress)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT)


class MobilePhone():
    ''' each phone in the config file becomes an instance of this class, updating its own state '''
    phones = []
    net_info = {}  
    all_home_action = ""
    all_away_action = ""
    action = False
    def __init__(self, phone):
        MobilePhone.phones.append(self)
        self.name = phone['name']
        self.mac = phone['mac']
        self.api_key = phone['api_key']
        self.home_action = phone['home_action']
        self.away_action = phone['away_action']
        self.push_timeout = phone['push_timeout']
        self.platform = phone['platform']
        self.ipaddress = '0.0.0.0'
        self.location = 'unknown'
        self.action = False
        self.last_ping = False
        self.push_sent = False
        self.active_time = int(time.time())
        self.away_time = 0
        self.push_time = 0
        self.seen_time = int(time.time())
    def send_ping(self):
        ''' ping the phone and see if it's on the LAN '''
        if platform.platform().split('-')[0] == 'Darwin':
            cmd = 'ping -c 1 -t 1 {}'.format(self.ipaddress)
        else:
            cmd = 'ping -c 1 -w 1 {}'.format(self.ipaddress)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        p.communicate()
        if p.returncode == 0:
            if not self.last_ping:
                # this is only for debug logging
                self.active_time = int(time.time())
                lapse = self.active_time - self.seen_time
                log.debug('{} came acive after {} seconds'.format(self.name, lapse))
            self.last_ping = True
            self.seen_time = int(time.time())
        else:
            if self.last_ping:
                # this is only for debug logging
                lapse = int(time.time()) - self.active_time
                log.debug('{} went inacive after {} seconds'.format(self.name, lapse))
            self.last_ping = False
        self.update()
    def send_push(self):
        ''' send a push notification wake up the phone '''
        if self.push_api == 'prowlapp':
            api_url = "https://api.prowlapp.com/publicapi/add"
            request = {
                'apikey': self.api_key,
                'application': 'phonehomey',
                'event': 'wake up call',
                'description': 'checking for this phone',
                'priority': -2
                }
            headers = {
                "content-type": "application/x-www-form-urlencoded",
                "User-Agent": "phonehomey"
                }
            data = urllib.parse.urlencode(request)
            response = requests.post(api_url, headers=headers, data=data)
        # other possible push services would go here as elif statements
        if response.status_code != 200:
            log.info("failed to post to push api for {}: {}".format(self.name, response))
        else:
            log.debug("sent push notification to {}".format(self.name))
            self.push_time = int(time.time())
    def update(self):
        ''' based on the current instance attributes, deterine location and update states '''
        location = self.location
        if self.last_ping:
            self.location = 'home'
            self.push_sent = False
        elif int(time.time()) - self.seen_time > self.push_timeout:
            if not self.push_sent:
                self.send_push()
                self.push_sent = True
            elif int(time.time()) - self.push_time > 10:
                self.location = 'away'
        if self.location != location:
            self.action = True
            log.info('{} swtiched to {}'.format(self.name, self.location))
            # update the MobilePhone class if all phones are now in the same location
            MobilePhone.action = True
            for each_phone in MobilePhone.phones:
                if each_phone.location != self.location:
                    MobilePhone.action = False


def read_config():
    ''' parse the yaml formated config file '''
    if os.path.isfile('config_local.yml'):
        startup_log.debug('reading config_local.yml')        
        with open('config_local.yml', 'r') as stream:
            try:
                config = yaml.load(stream)[0]
            except:
                startup_log.debug('error parsing {}'.format('config_local.yml'))
                config = None
            return config
    elif os.path.isfile('config.yml'):
        startup_log.debug('reading config.yml')        
        with open('config.yml', 'r') as stream:
            try:
                config = yaml.load(stream)[0]
            except:
                startup_log.debug('error parsing {}'.format('config.yml'))
                config = None
            return config
    else:
        startup_log.debug("can't find config_local.yml or config.yml".format(file))
        sys.exit()


def discover_phone(phone):
    ''' try to get the phone to show up in the arp table so it can be found by MAC address '''
    last_ip = phone.ipaddress
    phone_ip = search_arp(phone)
    if phone_ip == '0.0.0.0':
        # phone is undiscovered
        lan = ipaddress.IPv4Network(
            '{}/{}'.format(MobilePhone.net_info['network'],MobilePhone.net_info['netmask']))
        # do a ping scan to update the arp table
        # need a different ping timeout argument for Darwin
        if platform.platform().split('-')[0] == 'Darwin':
            timeout = '-t 1'
        else:
            timeout = '-w 1'
        log.info('running network scan to find {}: {}'.format(phone.name, phone.mac))
        for address in lan:
            # threading so it can be easily be backgrounded and throttled at 256 max threads
            if threading.activeCount() < 256:
                silentPingThread(address, timeout).start()
        while threading.activeCount() > 1:
            # threads still running, wait to continue
            time.sleep(.1)
        phone_ip = search_arp(phone)
    if phone_ip != '0.0.0.0' and phone_ip != last_ip:
        # the ip address has changed
        log.info("found {} at {}".format(phone.name, phone_ip))
        phone.ipaddress = phone_ip


def search_arp(phone):
    ''' search the arp table for a phone '''
    cmd = 'arp -an'
    # read the arp table
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    arp_list = stdout.decode("utf-8")
    # parse the IP address out of the arp table if it's there
    phone_ip = '0.0.0.0'
    for entry in arp_list.split('\n'):
        if phone.mac.replace(':0',':') in entry:
            ipa = entry.split('(')[1]
            phone_ip = ipa.split(')')[0]
    return phone_ip


def get_net_info():
    ''' returns the ipaddress, netmask, and network address of the local host '''
    net_info = {}
    net_info['ipaddress'] = socket.gethostbyname(socket.getfqdn())
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        try:
            interface_info = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
            if interface_info['addr'] == net_info['ipaddress']:
                net_info['netmask'] = interface_info['netmask']
                ip = netaddr.IPNetwork('{}/{}'.format(net_info['ipaddress'], net_info['netmask']))
                net_info['network'] = ip.network
                log.debug(net_info)
                return net_info
                break
        except:
            pass


def run_script(action_file, phone, all_phones=False):
    ''' execute the given python file '''
    # create local vars to pass in the phone that triggered this, and the if all phones are in the same location
    local_vars = locals()
    action = './scripts/{}'.format(action_file)
    with open(action) as f:
        code = compile(f.read(), action, 'exec')
        exec(code, globals(), local_vars)


def run_action(phone):
    ''' run actions when a phone changes to home/away '''
    if phone.location == 'home':
        phone.action = False
        log.info('run action for {}: {}'.format(phone.name, phone.home_action))
        run_script(phone.home_action, phone)
    elif phone.location == 'away':
        phone.action = False
        log.info('run action for {}: {}'.format(phone.name, phone.away_action))
        run_script(phone.away_action, phone)
    if MobilePhone.action:
        # this event triggerd a global action
        if phone.location == 'home':
            # all phones are this same location, run script
            log.info('action for all_home: {}'.format(MobilePhone.all_home_action))
            run_script(MobilePhone.all_home_action, phone, all_phones=True)
        elif phone.location == 'away':
            # all phones are this same location, run script
            log.info('action for all_away: {}'.format(MobilePhone.all_away_action))
            run_script(MobilePhone.all_home_action, phone, all_phones=True)


def hunt(phone, discover=True, push=False):
    ''' hunt for phone using push notification, network scan, and ping '''
    if push:
        phone.send_push()
        time.sleep(2)
    if discover:
        discover_phone(phone)
    phone.send_ping()
    phone.update()


def phonehomey(phone):
    ''' the primary workflow of phonehomey - discover and/or monitor a phone '''
    if phone.location is 'unknown':
        # if the phone location is unknown, it needs to be discovered
        if not phone.push_sent:
            # a push has not been sent yet, send one and try to discover the phone
            hunt(phone=phone, push=True)
            phone.away_time = int(time.time())
        elif int(time.time()) - phone.away_time > 10:
            # already sent push, also waited 10 seconds before trying to discover again
            phone.away_time = int(time.time())
            hunt(phone=phone)
    else:
        # the phone has been discovered, see if it'll ping
        hunt(phone=phone, discover=False)
        if phone.last_ping:
            # the ping returned, sleep for 1 second to throttle ping
            time.sleep(1)
        else:
            # the ping did not return
            if int(time.time()) - phone.seen_time > phone.push_timeout:
                # the push timeout has elapsed since the last ping returned
                if not phone.push_sent:
                    # send a push notification to discover the phone since we haven't yet
                    hunt(phone=phone, push=True)
                else:
                    # a push was already sent, now just monitor
                    if int(time.time()) - phone.away_time > 10:
                        # every 10 seconds, try to discover the phone
                        phone.away_time = int(time.time())
                        hunt(phone=phone)
    if phone.action:
        # the phone location changed and triggered an action
        run_action(phone)


def get_this_party_started():
    ''' Startup function to discover devices and kick off the loop '''
    global startup_log
    global log
    if '-v' in sys.argv:
        verbose = True
    else:
        verbose = False
    # startup_log doesn't actually do anything unless verbose is on, but it's required for the config function
    startup_log = setup_logger(name='startup_log', log_level='DEBUG', std_out=verbose)
    config = read_config()
    log = setup_logger(
        name='log',
        log_level=config['global']['log_level'],
        log_file=config['global']['log_file'],
        std_out=verbose)
    if verbose:
        log.debug('phonehomey is running in verbose mode')
    log.info('phonehomey started up')
    log.debug('config: {}'.format(config))
    MobilePhone.all_home_action = config['global']['all_home_action']
    MobilePhone.all_away_action = config['global']['all_away_action']
    # discover and store network information
    MobilePhone.net_info = get_net_info()
    log.debug('net info: {}'.format(MobilePhone.net_info))
    # create a MobilePhone instance of each phone in the config
    for phone in config['phones']:
        MobilePhone(phone)
    # infinite phonehomey loop!
    while True:
        for phone in MobilePhone.phones:
            # run phonehomey on each phone in the config file
            phonehomey(phone)


if __name__ == '__main__':
    get_this_party_started()
