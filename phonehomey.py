
import itertools
import os
import requests
import subprocess
import time
import yaml
from datetime import datetime
from prowlpy import prowlpy


def exe_cmd(cmd):
    ''' A wrapper for calling subprocess in order to get the output back the same way every time '''
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return {'returncode': p.returncode, 'output': stdout.decode("utf-8")}
    else:
        return {'returncode': p.returncode, 'output': stderr.decode("utf-8")}


def read_settings():
    settings = {}
    if os.path.isfile("settings.yml"):
        with open("settings.yml", 'r') as stream:
            try:
                settings = yaml.load(stream)[0]
            except e as error:
                print('Error parsing settings.yml: {}'.format(e))
            return settings
    else:
        print('File settings.yml not found')


def wake_up_call(api_key):
    ''' send a push notification to the prowl API to wake up the phone '''
    p = prowlpy.Prowl(api_key)
    try:
        p.add(
            application='phonehomey',
            event='tickle',
            description="checking for this phone",
            priority=-2,
            )
        print 'Success'
    except Exception, msg:
        print msg


def locate_ip(mac, ip_address):
    ''' Get the phone's IP address from arp using its MAC address '''
    # do an scan to update the arp table
    exe_cmd("/usr/local/bin/arp-scan -l")
    # tease the IP address out of the arp table if it's there
    arp_list = exe_cmd('arp -an | grep -v incomplete')
    for entry in arp_list['output'].split('\n'):
        if mac in entry:
            ipa = entry.split('(')[1]
            ip = ipa.split(')')[0]
            return ip
    # if the MAC is not found, just return the IP that was passed in
    return ip_address


def never_stop_looking(last_known_ip):
    ''' Infinite loop function that looks for the device in question '''
    # set up initial vars for the loop
    active = False
    phone_ip = last_known_ip
    last_seen = int(time.time())
    # commence looping!
    while True:
        output = exe_cmd('ping -c 1 -t 1 {}'.format(phone_ip))
        now = int(time.time())
        if output['returncode'] == 0:
            lapse = now - last_seen
            last_seen = now
            if not active:
                print("{} - Active. Seconds inactive: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), lapse))
                active = True
            time.sleep(1)
        else:
            if active:
                print("{} - Inactive.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                active = False
            time.sleep(1)
        # if it's been over an hour, the phone may get a new IP address from the router
        if (now - last_seen) > 3600:
            phone_ip = locate_ip(macs[0], last_known_ip)
            if phone_ip != last_known_ip:
                last_known_ip = phone_ip
                print("{} moved to: {}".format(macs[0], last_known_ip))
            else:
                time.sleep(5)


def get_this_party_started():
    ''' Startup function to discover device and kick off the loop '''
    last_known_ip = "0.0.0.0"
    print("{} - Started".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    # need to discover the phone before the script can continue
    found = False
    while not found:
        phone_ip = locate_ip(macs[0], last_known_ip)
        if phone_ip != last_known_ip:
            last_known_ip = phone_ip
            print("Found: {}".format(last_known_ip))
            found = True
        else:
            time.sleep(1)
    # run the infinite loop looking for the device
    never_stop_looking(last_known_ip)


if __name__ == '__main__':
    get_this_party_started()
