#!/usr/bin/env python3
"""Wifi Exploit Finder

Scan wifi channels using an 802.11x adapter capable of monitor mode. If an exploitable device is found, an exploit message is sent to the hiprfisr.

For FISSURE database identification, add the following row to the `attacks` table.

"protocol","attack_name","modulation_type","hardware","attack_type","filename","category_name","version"
"802.11x","Exploit_Finder","Default","802.11x Adapter","Python3 Script","Wifi_Exploit_Finder.py","Sniffing/Snooping","maint-3.10"

References:

- [1] https://community.cisco.com/t5/wireless-mobility-knowledge-base/802-11-frames-a-starter-guide-to-learn-wireless-sniffer-traces/ta-p/3110019
"""
import sys
import subprocess
import time
import csv
import numpy as np
import json
from datetime import datetime, timezone
import os
from fissure.utils import FLOW_GRAPH_LIBRARY_3_10
from typing import List


DURATION = -1 # to run until interrupted
DWELL = 1 # 1 second per channel
NOTES = 'Wifi exploitable device finder'

# vendor plain text (reduced from variants)
# (search term, plain output)
VENDOR_PLAIN = [
    ('d-link', 'd-link'),
    ('tp-link', 'tp-link')
]

def apply_change(dev:str,commands:List[List[str]]):
    subprocess.run(['sudo','ip','link','set',dev,'down'])
    for command in commands:
        subprocess.run(command)
    subprocess.run(['sudo','ip','link','set',dev,'up'])

def set_monitor_mode(dev:str):
    apply_change(dev,[
        ['sudo','iwconfig',dev,'mode','Monitor']
    ])

def set_freq(dev:str,freq:float):
    subprocess.run(['sudo','iwconfig',dev,'freq',str(freq)])

def set_channel(dev:str,channel:int):
    subprocess.run(['sudo','iwconfig',dev,'channel',str(channel)])

def get_channels(dev:str)->dict:
    output = subprocess.run(['sudo','iwlist',dev,'frequency'], capture_output=True)
    output = output.stdout.decode('utf-8')
    output = output.split('\n')
    channels = {}
    for line in output:
        if 'Current' in line:
            continue
        if 'Channel' in line:
            line = line[line.index('Channel')+7:]
            channel = int(line[:line.index(':')])
            frequency = float(line[line.index(':')+1:line.index('GHz')])
            channels[channel] = frequency
    return channels

class OUILookup(object):
    def __init__(self):
        self._table = {}
        oui = os.path.join(FLOW_GRAPH_LIBRARY_3_10, "Single-Stage Flow Graphs", "resources", "oui.csv")
        with open(oui, "r") as ouifile:
            ouireader = csv.reader(ouifile)
            for lines in ouireader:
                self._table[lines[1]] = lines[2]

    def match(self, mac):
        tmp_mac = mac.replace(":", "").upper()
        found_mac = tmp_mac[:6]
        entry = self._table.get(found_mac)
        return entry

class Scan(object):
    def __init__(self, dev:str, channels:List[int]=None, duration:float=DURATION, dwell:float=DWELL, power_limit:float=-np.inf):
        self.dev = dev
        self.duration = duration
        self.dwell = dwell
        self.power_limit = power_limit

        if channels is None:
            # get available channels
            self.channels = list(get_channels(dev).keys())
        else:
            self.channels = channels

        # set monitor mode
        set_monitor_mode(dev)

        # initialize wireless ap address lookup
        self.aps = {}

        # create oui lookup table
        self.oui = OUILookup()

        self.fields_ordered = [
            'frame.time_epoch',
            'radiotap.channel.freq',
            'wlan.sa',
            'wlan.ta',
            'wlan.ra',
            'wlan.da',
            'radiotap.dbm_antsignal',
            'wlan.ssid',
            'wlan.fc.type_subtype'
        ]
        self.nfields = len(self.fields_ordered)
        self.fields = {field.split('.')[-1]: i for (i, field) in enumerate(self.fields_ordered)}
        self.cmd = ['sudo', 'tshark', '-i', dev, '-E', 'separator=,', '-E', 'occurrence=f', '-a', 'duration:' + str(dwell), '-Tfields']
        for field in self.fields_ordered:
            self.cmd += ['-e', field]

    def add_ap(self, mac, freq, row):
        # get vendor
        vendor = self.oui.match(mac)

        # get ssid
        ssid_raw = row[self.fields.get('ssid')]
        if ssid_raw == '<MISSING>':
            ssid = '<MISSING>'
        else:
            ssid = ''
            for i in range(0,len(ssid_raw),2):
                ssid += chr(int(ssid_raw[i:i+2], 16))

        # get vendor plain text
        vendor_plain = None
        for vplain in VENDOR_PLAIN:
            if vendor is not None and vplain[0] in vendor.lower():
                vendor_plain = vplain[1]

        # add to AP table (unindent to avoid filtering on these)
        self.aps[mac] = {
            'vendor': vendor,
            'vendor_plain': vendor_plain,
            'ssid': ssid,
            'stations': {}
        }

        sys.stdout.write(json.dumps({
            'msg': 'tak',
            'uid': ssid, #mac,
            'lat': '%(latitude)f',
            'lon': '%(longitude)f',
            'alt': '%(altitude)f',
            'time': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'type': 'a-h-G-E-S'
        }) + '\n')
        sys.stdout.flush()

    def add_station(self, mac, mac_ap, freq, row):
        if len(mac)==17 and\
        mac_ap in self.aps.keys() and\
        not mac == 'ff:ff:ff:ff:ff:ff':# and not mac in self.aps[mac_ap]['stations'].keys():
            # found new station
            self.aps[mac_ap]['stations'][mac] = freq

            sys.stdout.flush()

    def run(self):
        tend = np.inf if self.duration == -1 else time.time() + self.duration
        while True:
            newta = False
            for channel in self.channels:
                # set channel
                set_channel(self.dev, channel)

                if time.time() + self.dwell > tend:
                    # stop scan
                    return self.aps

                # capture
                output = subprocess.run(self.cmd, capture_output=True)
                output = output.stdout.decode('utf-8')
                reader = csv.reader(output.split('\n'),escapechar="\\")
                aps_seen = []
                for row in reader:
                    if len(row) == self.nfields: # populated line
                        power = row[self.fields.get('dbm_antsignal')]
                        power = self.power_limit - 1 if len(power)==0 else int(power.split(',')[0])
                        if power < self.power_limit:
                            continue

                        mac_sa = row[self.fields.get('sa')]
                        mac_da = row[self.fields.get('da')]
                        freq = float(row[self.fields.get('freq')])

                        if mac_sa in aps_seen:
                            continue
                        else:
                            aps_seen += [mac_sa]

                        type_subtype = int(row[self.fields.get('type_subtype')], 16)
                        if type_subtype == 8: # beacon
                            self.add_ap(mac_sa, freq, row)
                            continue

                        elif type_subtype == 0: # association request
                            self.add_ap(mac_da, freq, row)

            #return
            if not newta:
                sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S") + ' - No new mac addresses detected in channel scan\n')
                sys.stdout.flush()

def getArguments():
    iface = None
    duration=DURATION
    dwell=DWELL
    power = -100
    channels = None
    run_with_sudo = "False"
    notes = NOTES

    return (
        ['iface', 'duration', 'dwell', 'power', 'channels', 'run_with_sudo', 'notes'],
        [iface, duration, dwell, power, channels, run_with_sudo, notes]
    )

if __name__ == '__main__':
    # get default values
    (iface, duration, dwell, power, channels, run_with_sudo, notes) = getArguments()[1]

    # handle input
    nargs = len(sys.argv)
    iface = sys.argv[1] if nargs > 1 else iface
    duration = float(sys.argv[2]) if nargs > 2 else duration
    dwell = float(sys.argv[3]) if nargs > 3 else dwell
    power = int(sys.argv[4]) if nargs > 4 else power
    channels = sys.argv[5] if nargs > 5 else channels
    channels = None if channels in [None, 'None'] else [int(c) for c in channels.split(',')]

    # run
    scan = Scan(iface, channels, duration, dwell, power)
    scan.run()
