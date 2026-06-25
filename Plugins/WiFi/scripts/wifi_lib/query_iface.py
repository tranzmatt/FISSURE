#! /usr/bin/env python3
"""WiFi Interface Query
This module provides functions to query information about WiFi interfaces, including their status and configuration.
"""
import logging
import subprocess
from typing import List, Dict, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_monitor_capable(iface: str) -> bool:
    """Check if interface supports monitor mode without switching to it.

    Parameters
    ----------
    iface : str
        The network interface name

    Returns
    -------
    bool
        True if interface supports monitor mode
    """
    try:
        output = subprocess.run(['iw', iface, 'info'], capture_output=True)
        if output.returncode != 0:
            return False
        info = output.stdout.decode('utf-8')

        # Extract phy name from info
        phy_name = None
        for line in info.split('\n'):
            if 'wiphy' in line.lower():
                phy_name = 'phy' + line.split()[-1]
                break
        if phy_name is None:
            return False

        # Check supported interface modes
        output = subprocess.run(['iw', 'phy', phy_name, 'info'], capture_output=True)
        phy_info = output.stdout.decode('utf-8')

        # Look for "Supported interface modes" section
        if 'monitor' in phy_info.lower():
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return False

def get_interfaces(monitor_only: bool=False) -> List[str]:
    """Get a list of available WiFi interfaces.

    Parameters
    ----------
    monitor_only : bool, optional
        If True, only return interfaces capable of monitor mode, by default False

    Returns
    -------
    List[str]
        A list of WiFi interface names.
    """
    output = subprocess.run(['iwconfig'], capture_output=True)
    output = output.stdout.decode('utf-8')
    interfaces = []
    for line in output.split('\n'):
        if 'no wireless extensions' in line:
            continue
        if line and not line.startswith(' '):
            iface = line.split()[0]
            if monitor_only and is_monitor_capable(iface):
                interfaces.append(iface)
            elif not monitor_only:
                interfaces.append(iface)
    return interfaces

def choose_interface(logger: logging.Logger=logger) -> Union[str, None]:
    """Choose a WiFi interface based on rules.

    1. If only one interface is available,
        a. If does not support monitor mode, return None
        b. If supports monitor mode, return it.
    2. If multiple interfaces are available,
        a. If only one interface is not in use, return it.
        b. If multiple interfaces are not in use,
            i. If one interface supports monitor mode, return it.
            ii. Otherwise, return the first available interface.

    Parameters
    ----------
    logger : logging.Logger, optional
        Logger for logging information and errors.

    Returns
    -------
    Union[str, None]
        The name of the chosen WiFi interface, or None if no suitable interface is found.
    """
    interfaces = get_interfaces()
    if len(interfaces) == 0:
        logger.error("No WiFi interfaces found.")
        return None
    elif len(interfaces) == 1:
        iface = interfaces[0]
        if is_monitor_capable(iface):
            logger.info(f"Only one interface found: {iface}, which supports monitor mode.")
            return iface
        else:
            logger.error(f"Only one interface found: {iface}, which does not support monitor mode.")
            return None
    else:
        free_interfaces = []
        for iface in interfaces:
            status = get_interface_status(iface)
            if 'Access Point' not in status or ('Access Point' in status and status['Access Point'] == 'Not-Associated'):
                if is_monitor_capable(iface):
                    free_interfaces.append(iface)
        if len(free_interfaces) == 1:
            logger.info(f"One interface found, choosing the only free one: {free_interfaces[0]}")
            return free_interfaces[0]
        elif len(free_interfaces) > 1:
            logger.info(f"Multiple monitor mode capable free interfaces found, choosing the first: {free_interfaces[0]}")
            return free_interfaces[0]
        else:
            logger.error("All interfaces are currently in use.")
            return None

def verify_interface(dev: str, raise_error: bool = False, logger: logging.Logger = logger) -> bool:
    """Verify if a specific WiFi interface exists.

    Parameters
    ----------
    dev : str
        The network device to verify (e.g., 'wlan0').
    raise_error : bool, optional
        Whether to raise an error if the interface does not exist, by default False
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    bool
        True if the interface exists, False otherwise.

    Raises
    ------
    ValueError
        If the interface does not exist and raise_error is True.
    """
    interfaces = get_interfaces()
    if dev in interfaces:
        output = subprocess.run(['iwconfig', dev], capture_output=True)
        if b'No such device' in output.stdout:
            logger.error(f"Interface {dev} does not exist.")
            if raise_error:
                raise ValueError(f"Interface {dev} does not exist.")
            return False
        logger.info(f"Interface {dev} exists.")
        return True
    logger.error(f"Interface {dev} does not exist.")
    if raise_error:
        raise ValueError(f"Interface {dev} does not exist.")
    return False

def get_interface_status(dev: str) -> Dict[str, str]:
    """Get the status of a specific WiFi interface.

    Parameters
    ----------
    dev : str
        The network device to query (e.g., 'wlan0').

    Returns
    -------
    Dict[str, str]
        A dictionary containing the status information of the interface.
    """
    output = subprocess.run(['iwconfig', dev], capture_output=True)
    output = output.stdout.decode('utf-8')
    status = {}
    for line in output.split('\n'):
        if '=' in line or ':' in line:
            parts = [p for p in line.replace('\t', '  ').split('  ') if p]
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    status[key.strip()] = value.strip()
                elif ':' in part:
                    key, value = part.split(':', 1)
                    status[key.strip()] = value.strip()
    return status

def get_channels(dev: str, logger: logging.Logger = logger) -> Dict[int, float]:
    """Get the available channels and their frequencies for the network device.

    Parameters
    ----------
    dev : str
        The network device to query (e.g., 'wlan0').
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    Dict[int, float]
        A dictionary mapping channel numbers to their frequencies (in GHz).
    """
    try:
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
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get channels for {dev}: {e}")
        return {}