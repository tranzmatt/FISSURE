#!/usr/bin/env python3
"""TPMS Capture

Capture TPMS using rtl_433 and RTL2832U

For FISSURE database identification, add the following row to the `attacks` table.

"protocol","attack_name","modulation_type","hardware","attack_type","filename","category_name","version"
"TPMS","Receive","FSK","RTL2832U","Python3 Script","TPMS_RTLSDR_Receive.py","Sniffing/Snooping","maint-3.10"

Returns
-------
_type_
    _description_
"""
import sys
import socket
import time
import json
import subprocess
from multiprocessing import Process
from datetime import datetime, timezone

DEVICE = 0 # device index
FREQUENCY = 315e6 # or 433e6
GAIN = 49 # rx gain
NOTES = 'Use rtl_433 to capture TPMS messages'

def main(device:int=DEVICE, frequency:float=FREQUENCY, gain:float=GAIN, whitelist:list[str]=None):
    # launch tpms receiver
    cmd = ['rtl_433', '-d', '%d'%device, '-M', 'level', '-f', '%d'%frequency, '-g', '%d'%gain, '-v', '-F', 'syslog:127.0.0.1:1514']
    p = Process(target=subprocess.run, args=(' '.join(cmd),), kwargs={'shell': True})
    p.start()
    time.sleep(1) # let rtl_433 start

    # create message parser
    try:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind(('localhost', 1514))
        except OSError as e:
            if 'Errno 98' in str(e): # address already in use
                subprocess.run(['fuser', '-k', '1514/udp']) # kill as user
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    client_socket.bind(('localhost', 1514))
                except OSError as e:
                    if 'Errno 98' in str(e): # address already in use
                        subprocess.run(['sudo', 'fuser', '-k', '1514/udp']) # kill as sudo
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        client_socket.bind(('localhost', 1514))
                    else:
                        raise OSError(e)
            else:
                raise OSError(e)
        while True:
            time.sleep(0.1)
            data = client_socket.recvfrom(512)
            data = data[0].decode('utf-8')
            data = json.loads(data[data.index('rtl_433 - - - {') + 14:])
            
            # Find the actual key that matches "id" (case-insensitive)
            id_key = next((key for key in data.keys() if 'id' in key.lower()), None)
            if id_key:
                id = data.pop(id_key)
                if whitelist is None or id in whitelist:
                    # Find any key that contains "pressure" (case-insensitive)
                    pressure_key = next((key for key in data.keys() if "pressure" in key.lower()), None)

                    if pressure_key:
                        sys.stdout.write(json.dumps({
                            'msg': 'alert',
                            'text': f"TPMS id={id} {pressure_key}={data.get(pressure_key)}",
                        }) + '\n')
                        sys.stdout.flush()

                    if 'time' in data.keys():
                        _ = data.pop('time')
                    sys.stdout.write(json.dumps({
                        'msg': 'tak',
                        'uid': id,
                        'lat': '%(latitude)f',
                        'lon': '%(longitude)f',
                        'alt': '%(altitude)f',
                        'time': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                        'remarks': '"' + json.dumps(data, separators=(',', ':')) + '"',
                        'type': 'a-h-G-U-C', # red ground symbol
                    }) + '\n')
                    sys.stdout.flush()
    finally:
        client_socket.close()
        p.terminate()

def getArguments():
    device = DEVICE
    frequency = FREQUENCY
    gain = GAIN
    whitelist = '' # no whitelist == all ids reported
    notes = NOTES

    return (
        ['device', 'frequency', 'gain', 'whitelist', 'notes'],
        [device, frequency, gain, whitelist, notes]
    )

if __name__ == '__main__':
    # get default values
    (device, frequency, gain, whitelist, notes) = getArguments()[1]

    # handle input
    nargs = len(sys.argv)
    device = float(sys.argv[1]) if nargs > 1 else device
    frequency = float(sys.argv[2]) if nargs > 2 else frequency
    gain = float(sys.argv[3]) if nargs > 3 else gain
    whitelist = sys.argv[4] if nargs > 4 else whitelist
    if len(whitelist) > 0:
        whitelist = list(whitelist.split(','))
    else:
        whitelist = None

    # run
    main(device, frequency, gain, whitelist)
