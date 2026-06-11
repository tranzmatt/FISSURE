#!/usr/bin/env python3
"""Wifi Scanner

Scan wifi channels using an 802.11x adapter capable of monitor mode.

For FISSURE database identification, add the following row to the `attacks` table.

"protocol","attack_name","modulation_type","hardware","attack_type","filename","category_name","version"
"802.11x","Scan","Default","802.11x Adapter","Python3 Script","wifi_rx_scan.py","Sniffing/Snooping","maint-3.10"
"""
import sys
import subprocess
import time
import csv
import numpy as np
import json
from datetime import datetime, timezone
from typing import List
import os

DURATION = -1 # to run until interrupted
DWELL = 1 # 1 second per channel
NOTES = 'Scan Wifi channels'

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
    apply_change(dev,[
        ['sudo','iwconfig',dev,'freq',str(freq)]
    ])

def set_channel(dev:str,channel:int):
    apply_change(dev,[
        ['sudo','iwconfig',dev,'channel',str(channel)]
    ])

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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'resources', 'oui.csv')
        with open(file_path, newline='') as ouifile:
            ouireader = csv.reader(ouifile)
            for lines in ouireader:
                self._table[lines[1]] = lines[2]

    def match(self, mac):
        tmp_mac = mac.replace(":", "").upper()
        found_mac = tmp_mac[:6]
        entry = self._table.get(found_mac)
        return entry

def scan(dev:str, channels:List[int]=None, duration:int=DURATION, dwell:int=DWELL, power_limit:float=-np.inf):
    """Scan Wifi Channels

    Scan wifi channels using an 802.11x adapter capable of monitor mode.

    For FISSURE database identification, add the following row to the `attacks` table.

    "protocol","attack_name","modulation_type","hardware","attack_type","filename","category_name","version"
    "802.11x","Scan","Default","802.11x Adapter","Python3 Script","wifi_rx_scan.py","Sniffing/Snooping","maint-3.10"

    Parameters
    ----------
    dev : str
        Phy interface name
    channels : List[int], optional
        Channels to scan, by default None to use all channels available to phy
    duration : int, optional
        Duration of scan where -1 is infinite, by default DURATION
    dwell : int, optional
        Dwell time per channel, by default DWELL

    Returns
    -------
    dict
        Detected wireless nodes where keys are detected transmitter/receiver mac addresses and values are the observed values including `timestamp` as time of first observation
    """
    if channels is None:
        # get available channels
        channels = list(get_channels(dev).keys())
   
    # set monitor mode
    set_monitor_mode(dev)
    
    # create known wireless nodes address list
    nodes = {}

    # create oui lookup table
    oui = OUILookup()
    
    tend = np.inf if duration == -1 else time.time() + duration
        
    while True:
        newta = False
        for channel in channels:
            # set channel
            set_channel(dev, channel)

            if time.time() + dwell > tend:
                # stop scan
                return nodes

            # capture
            output = subprocess.run([
                'sudo', 'tshark', '-i', dev, '-E', 'separator=,', '-E', 'occurrence=f',
                '-a', 'duration:' + str(dwell), '-Tfields',
                '-e', 'frame.time_epoch', '-e', 'radiotap.channel.freq', '-e', 'wlan.ta',
                '-e', 'wlan.ra', '-e', 'radiotap.dbm_antsignal', '-e', 'wlan.ssid'
            ], capture_output=True)
            output = output.stdout.decode('utf-8')
            reader = csv.reader(output.split('\n'),escapechar="\\")
            for row in reader:
                if len(row) == 6: # populated line
                    power = power_limit - 1 if len(row[4])==0 else int(row[4].split(',')[0])
                    if power < power_limit:
                        continue
                    for mac in row[2:4]: # process both transmitter and receiver mac addresses
                        if len(mac) > 0 and not mac in nodes.keys():
                            newta = True
                            if row[5] == '<MISSING>':
                                ssid = '<MISSING>'
                            else:
                                ssid = ''
                                for i in range(0,len(row[5]),2):
                                    ssid += chr(int(row[5][i:i+2], 16))

                            # match mac to vendor
                            vendor = oui.match(mac)

                            # add to nodes table
                            nodes[mac] = {
                                'frequency_mhz': int(row[1]),
                                'timestamp': datetime.fromtimestamp(float(row[0]), timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                'snr_db': power,
                                'ssid': ssid,
                                'vendor': vendor
                            }
                            currobv = nodes.get(mac)

                            # create alert and tak messages
                            _ = currobv.pop('timestamp')
                            sys.stdout.write(json.dumps({
                                'msg': 'alert',
                                'text': f"Wifi mac={mac} frequency_mhz={currobv.get('frequency_mhz')} snr_db={currobv.get('snr_db')}"
                            }) + '\n')
                            sys.stdout.write(json.dumps({
                                'msg': 'tak',
                                'uid': str(mac),
                                'lat': '%(latitude)f',
                                'lon': '%(longitude)f',
                                'alt': '%(altitude)f',
                                'time': datetime.fromtimestamp(float(row[0]), timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                'remarks': '"' + json.dumps(currobv, separators=(',', ':')) + '"'
                            }) + '\n')
                            sys.stdout.write(json.dumps({
                                'msg': 'snreport',
                                'text': [ # https://www.globalsecurity.org/intell/library/policy/army/fm/34-35/appc.htm#figc_5
                                    'UNCLAS',
                                    f"MSGID/TACREP/FISSURE REPORT//", # TACREP=Tactical Report
                                    f"GNDOP/{datetime.now(timezone.utc).strftime('%H%M%SZ')}/1/US/ENEMY COMBATANT/ROUTER:{mac}//", # GNDOP=Ground Operations
                                    "LOCATION/TAMPA,FL/%(latitude_ddm)s%(longitude_ddm)s//", # City as city,state or city,country and Location in degree and decimal minutes format
                                    f"COMEW/{currobv.get('frequency_mhz'):0.3f}MHZ/20MHZ//", # COMEW=Communications Electronic Warfare
                                ]
                            }) + '\n')
                            sys.stdout.flush()

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
    duration = int(sys.argv[2]) if nargs > 2 else duration
    dwell = int(sys.argv[3]) if nargs > 3 else dwell
    power = int(sys.argv[4]) if nargs > 4 else power
    channels = sys.argv[5] if nargs > 5 else channels
    channels = None if channels in [None, 'None'] else [int(c) for c in channels.split(',')]

    # run
    scan(iface, channels, duration, dwell, power)
