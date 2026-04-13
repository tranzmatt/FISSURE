#!/usr/bin/env python3
"""Wifi Access Point Scanner

Scan wifi channels using an 802.11x adapter capable of monitor mode. Report if an access point (AP) is found.

References:

- [1] https://community.cisco.com/t5/wireless-mobility-knowledge-base/802-11-frames-a-starter-guide-to-learn-wireless-sniffer-traces/ta-p/3110019
"""
import asyncio
import csv
import json
import logging
import numpy as np
import os
import sys
import subprocess
import time
from typing import List, Dict, Any, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    # add fissure to path and import modules
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation

# add wifi_lib to path and import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wifi_lib.query_iface import verify_interface, get_channels, choose_interface
from wifi_lib.configure_iface import set_monitor_mode, set_channel
from wifi_lib.oui import OUILookup, get_vendor_common_name

class OperationMain(Operation):
    """WiFi AP Scanner
    """
    def __init__(self, dev: Union[str, None] = None, duration: float = -1, dwell: float = 1, power: float = -100, channels: Union[List[int], None] = None, sensor_node_id: Union[int, str] = 0, logger: logging.Logger = logging.getLogger(__name__), alert_callback: callable = None, tak_cot_callback: callable = None) -> None:
        """
        Initialize the Wifi AP Scanner.

        Parameters
        ----------
        dev : str, optional
            Network interface to use for scanning (e.g., 'wlan0').
        duration : float, optional
            Duration of the scan in seconds. Default is -1 for indefinite scanning.
        dwell : float, optional
            Time to spend on each channel in seconds. Default is 1.
        power : float, optional
            Minimum signal strength (in dBm) to consider a device. Default is -100.
        channels : Union[List[int], None], optional
            List of channels to scan. If None, all available channels will be scanned.
        sensor_node_id : Union[int, str], optional
            The ID of the sensor node, by default 0
        logger : logging.Logger, optional
            Logger instance for logging, by default None
        alert_callback : callable, optional
            Callback function for alerts, by default None
        tak_cot_callback : callable, optional
            Callback function for TAK CoT messages, by default None
        """
        # templated common init
        super().__init__(sensor_node_id=sensor_node_id, logger=logger, alert_callback=alert_callback, tak_cot_callback=tak_cot_callback)

        # developer defined init
        if dev is None:
            # choose interface
            dev = choose_interface(logger=self.logger)
            if dev is None:
                self.logger.error("No suitable WiFi interface found for scanning.")
                raise ValueError("No suitable WiFi interface found for scanning.")
        self.dev = dev
        self.duration = float(duration)
        self.dwell = float(dwell)
        self.power = float(power)
        if channels is None or channels == 'None':
            # get available channels
            self.channels = list(get_channels(dev).keys())
        else:
            self.channels = channels

        # verify interface is valid
        verify_interface(self.dev, raise_error=True, logger=self.logger)

        # defined resources
        self.resource_args = {
            'dev': self.dev
        }

        self.ssids = {} # SSID table

        self.artifacts = {} # artifact table

        # build tshark command
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

        # initialize oui lookup
        self.oui_lookup = OUILookup()

    @staticmethod
    def get_resources(dev: str = '') -> Dict[str, Any]:
        """
        Get the resources required by the plugin script.

        Parameters
        ----------
        dev : str
            The network device name (e.g., 'wlan0').

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the resources for the plugin script.
        """
        return {
            'wifi_interface': {
                'type': 'wifi_adapter',
                'model': '',
                'serial': dev,
                'description': 'A wifi adapter capable of operating in monitor mode.',
                'required': True
            }
        }

    @staticmethod
    def get_interfaces() -> Dict[str, Any]:
        """
        Get the interfaces available for the plugin script.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the interfaces for the plugin script.
        """
        return {
            'alert': {
                'type': 'alert',
                'channel': 'fissure', # FISSURE zmq
                'direction': 'out',
                'description': 'Wifi AP detections.'
            },
            'tak': {
                'type': 'tak',
                'channel': 'fissure', # FISSURE zmq
                'direction': 'out',
                'description': 'Wifi AP detections in TAK CoT format.'
            }
        }

    async def setup(self) -> bool:
        """
        Setup the environment to run the operation.

        Returns
        -------
        bool
            True if setup is successful, False otherwise.
        """
        # set monitor mode
        configured = set_monitor_mode(self.dev, raise_error=True, logger=self.logger)
        if not configured:
            self.logger.debug(f"Failed to set monitor mode on interface {self.dev}.")
            self.logger.error("Operation environment setup failed.")
            await self.teardown()
            return False

        # create flag to indicate successful setup
        self._setup_complete = True
        self.logger.info("Operation environment setup complete.")
        return True

    async def run(self) -> None:
        """
        Run the operation.
        """
        # run end time
        tend = np.inf if self.duration == -1 else time.time() + self.duration
        self._mac_reported = {}
        while not self._stop:
            for channel in self.channels:
                # yield event loop and check for stop conditions
                await asyncio.sleep(0)
                if self._stop:
                    self.logger.info(f"Stop signal received. Stopping {self.__class__.__name__} channel scan...")
                    break
                if time.time() + self.dwell > tend:
                    # stop scan
                    self.logger.debug("Scan duration reached. Stopping scan...")
                    await self.stop()
                    return

                # set channel
                channel_set = set_channel(self.dev, channel)
                if not channel_set:
                    self.logger.error(f"Failed to set channel {channel} on interface {self.dev}.")
                    return

                # capture
                self.logger.debug(f"Scanning channel {channel} for {self.dwell} seconds...")
                output = subprocess.run(self.cmd, capture_output=True)
                output = output.stdout.decode('utf-8')
                reader = csv.reader(output.split('\n'),escapechar="\\")
                self._curr_ap = []
                nrows = 0
                for row in reader:
                    # yield event loop and check for stop conditions
                    await asyncio.sleep(0)
                    if self._stop:
                        self.logger.info(f"Stop signal received. Stopping {self.__class__.__name__} channel scan...")
                        break

                    if len(row) == self.nfields: # populated line
                        nrows += 1
                        self.logger.debug(f"Processing row: {row}")
                        # check power
                        power = row[self.fields.get('dbm_antsignal')]
                        power = self.power - 1 if len(power)==0 else int(power.split(',')[0])
                        if power < self.power:
                            self.logger.debug(f"Signal power {power} dBm below threshold {self.power} dBm; skipping.")
                            continue

                        # get ssid
                        ssid_raw = row[self.fields.get('ssid')]
                        if ssid_raw in ['<MISSING>', '']:
                            ssid = ssid_raw
                        elif ssid_raw is None:
                            ssid = ''
                        else:
                            ssid = ''
                            for i in range(0,len(ssid_raw),2):
                                ssid += chr(int(ssid_raw[i:i+2], 16))

                        # report AP and stations based on frame type/subtype
                        subtype_idx = self.fields.get('type_subtype')
                        if subtype_idx is None:
                            self.logger.debug("type_subtype field index not found; skipping row.")
                            continue
                        type_subtype = int(row[subtype_idx], 16)
                        freq_idx = self.fields.get('freq')
                        if freq_idx is None:
                            self.logger.debug("freq field index not found; skipping row.")
                            continue
                        freq = float(row[freq_idx])
                        sa_idx = self.fields.get('sa')
                        da_idx = self.fields.get('da')
                        
                        # Management frames (Type 0)
                        if type_subtype == 8: # beacon
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='ap')
                        elif type_subtype == 5: # probe response (from AP)
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='ap')
                        elif type_subtype == 4: # probe request (from station)
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='station')
                        elif type_subtype == 0: # association request
                            if da_idx is not None:
                                await self.add_ap(ssid, row[da_idx], freq, power, emtype='ap')  # DA is AP
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='station')  # SA is station
                        elif type_subtype == 1: # association response
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='ap')  # SA is AP
                            if da_idx is not None:
                                await self.add_ap(ssid, row[da_idx], freq, power, emtype='station')  # DA is station
                        elif type_subtype == 2: # reassociation request
                            if da_idx is not None:
                                await self.add_ap(ssid, row[da_idx], freq, power, emtype='ap')  # DA is AP
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='station')  # SA is station
                        elif type_subtype == 3: # reassociation response
                            if sa_idx is not None:
                                await self.add_ap(ssid, row[sa_idx], freq, power, emtype='ap')  # SA is AP
                            if da_idx is not None:
                                await self.add_ap(ssid, row[da_idx], freq, power, emtype='station')  # DA is station
                        else:
                            self.logger.debug(f"Frame type_subtype {type_subtype} not handled; skipping.")
                if nrows == 0:
                    self.logger.warning(f"No data captured on channel {channel}.")

    async def add_ap(self, ssid: str, mac: str, freq: float, power: float, emtype: str) -> None:
        """
        Add the AP to the AP table if not already present and report.

        Parameters
        ----------
        ssid : str
            SSID of the access point.
        mac : str
            MAC address of the emitter.
        freq : float
            Frequency of the emitter.
        power : float
            Signal power of the emitter.
        emtype : str
            Type of the emitter (e.g., 'ap' or 'station').
        """
        vendor = self.oui_lookup.match(mac)

        # update ssid document
        self.update_ssid_doc(ssid, mac, freq, power, emtype, vendor)

        # check if reported recently
        if mac in self._mac_reported:
            last_time = self._mac_reported[mac]
            if time.time() - last_time < self.dwell:
                # already reported in this scan cycle
                self.logger.debug(f"AP with MAC {mac} already reported recently; skipping.")
                return
            else:
                self._mac_reported[mac] = time.time()
        else:
            self._mac_reported[mac] = time.time()

        if ssid is None or ssid == '':
            ssid = f'{emtype.upper()}_{mac}'

        # send alert
        await self.alert_callback(self.sensor_node_id, self.opid, f'Wifi AP vendor "{vendor}" Detected: SSID={ssid} MAC={mac} FREQ={freq}MHz POWER={power}dBm', logger=self.logger)

        # send tak cot
        await self.tak_cot_callback(self.sensor_node_id, self.opid, uid=ssid, remarks=f'Wifi AP vendor "{vendor}" Detected: SSID={ssid} MAC={mac} FREQ={freq}MHz POWER={power}dBm', lat=True, lon=True, alt=True, time=True, type='a-h-G-E-S', logger=self.logger)

    def update_ssid_doc(self, ssid: str, mac: str, freq: float, power: float, emtype: str, vendor: Union[str, None]) -> None:
        """
        Update the SSID document in the database.

        Parameters
        ----------
        ssid : str
            SSID of the access point.
        mac : str
            MAC address of the emitter.
        freq : float
            Frequency of the emitter (in MHz).
        power : float
            Signal power of the emitter (in dBm).
        emtype : str
            Type of the emitter ('ap' or 'station').
        vendor : Union[str, None]
            Vendor of the emitter.
        """
        if ssid not in self.ssids:
            self.ssids[ssid] = {
                'ssid': ssid,
                'aps': [{'mac': mac, 'freq': freq, 'power': power, 'vendor': vendor}] if emtype == 'ap' else [],
                'stations': [{'mac': mac, 'freq': freq, 'power': power, 'vendor': vendor}] if emtype == 'station' else [],
            }

            # create artifact for SSID
            art_fname = self.artifact_manager.get_filename_for_artifact(self.opid, '.json')
            with open(art_fname, 'w') as f:
                json.dump(self.ssids[ssid], f, indent=4)
            artifact_id = self.create_artifact(art_fname, f'Wifi SSID={ssid}', 'json')
            self.artifacts[ssid] = artifact_id

        else:
            update = False
            if emtype == 'ap' and mac not in [entry['mac'] for entry in self.ssids[ssid]['aps']]:
                self.ssids[ssid]['aps'].append({'mac': mac, 'freq': freq, 'power': power, 'vendor': vendor})
                update = True
            elif emtype == 'station' and mac not in [entry['mac'] for entry in self.ssids[ssid]['stations']]:
                self.ssids[ssid]['stations'].append({'mac': mac, 'freq': freq, 'power': power, 'vendor': vendor})
                update = True

            if update:
                # update artifact for SSID
                artid = self.artifacts.get(ssid)
                if artid is not None:
                    artifact = self.artifact_manager.get_artifact(artid)
                    if artifact is None:
                        self.logger.warning(f"Artifact with ID {artid} not found for SSID {ssid}.")

                    else:
                        art_fname = artifact.file_path
                        with open(art_fname, 'w') as f:
                            json.dump(self.ssids[ssid], f, indent=4)
                        flag = self.update_artifact(artid)
                        if not flag:
                            self.logger.warning(f"Failed to update artifact for SSID {ssid}.")
                else:
                    self.logger.warning(f"No artifact found for SSID {ssid} to update.")

        self.logger.debug(f"Updating SSID document: SSID={ssid} MAC={mac}")

if __name__ == "__main__":
    """Run the plugin script as a standalone program for testing purposes.
    """
    from fissure.utils.plugins.test_operation import run_test
    dev = choose_interface()
    run_test(
        OperationMain,
        {
            'dev': dev,
            'duration': -1,
            'dwell': 0.5,
            'power': -100,
            'channels': list(range(1,10)) + [124,128,140]
        },
        {
            'dev': dev
        }
    )