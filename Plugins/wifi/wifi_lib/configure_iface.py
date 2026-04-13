#! /usr/bin/env python3
"""WiFi Interface Configuration

This module provides functions to configure WiFi interfaces, including setting monitor mode, frequency, and channel.
"""
import subprocess
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_change(dev: str, commands: List[List[str]], raise_error: bool = False, logger: logging.Logger = logger) -> bool:
    """Apply a series of commands to change the state of a network device.

    Parameters
    ----------
    dev : str
        The network device to configure (e.g., 'wlan0').
    commands : List[List[str]]
        A list of commands, where each command is represented as a list of strings.
    raise_error : bool, optional
        Whether to raise an error if any command fails, by default False
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    bool
        True if the changes were successfully applied, False otherwise.

    Raises
    ------
    RuntimeError
        If any command fails and raise_error is True.
    """
    try:
        subprocess.run(['sudo', 'ip', 'link', 'set', dev, 'down'], check=True)
        for command in commands:
            logger.info(f"Running command: {' '.join(command)}")
            subprocess.run(command, check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', dev, 'up'], check=True)
        logger.info(f"Successfully applied changes to {dev}")
        return True
    except subprocess.CalledProcessError as e:
        report = f"Failed to apply changes to {dev}:\n\tCommand:{command}\n\tError: {e}"
        logger.error(report)
        if raise_error:
            raise RuntimeError(report)
        return False

def set_monitor_mode(dev: str, raise_error: bool = False, logger: logging.Logger = logger) -> bool:
    """Set the network device to monitor mode.

    Parameters
    ----------
    dev : str
        The network device to configure (e.g., 'wlan0').
    raise_error : bool, optional
        Whether to raise an error if the operation fails, by default False
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    bool
        True if the operation was successful, False otherwise.

    Raises
    ------
    RuntimeError
        If the operation fails and raise_error is True.
    """
    return apply_change(dev, [['sudo', 'iwconfig', dev, 'mode', 'Monitor']], raise_error, logger)

def set_freq(dev: str, freq: float, raise_error: bool = False, logger: logging.Logger = logger) -> bool:
    """Set the frequency of the network device.

    Parameters
    ----------
    dev : str
        The network device to configure (e.g., 'wlan0').
    freq : float
        The frequency to set (in GHz).
    raise_error : bool, optional
        Whether to raise an error if the operation fails, by default False
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    bool
        True if the operation was successful, False otherwise.

    Raises
    ------
    RuntimeError
        If the operation fails and raise_error is True.
    """
    return apply_change(dev, [['sudo', 'iwconfig', dev, 'freq', str(freq)]], raise_error, logger)

def set_channel(dev: str, channel: int, raise_error: bool = False, logger: logging.Logger = logger) -> bool:
    """Set the channel of the network device.

    Parameters
    ----------
    dev : str
        The network device to configure (e.g., 'wlan0').
    channel : int
        The channel to set.
    raise_error : bool, optional
        Whether to raise an error if the operation fails, by default False
    logger : logging.Logger
        Logger for logging information and errors.

    Returns
    -------
    bool
        True if the operation was successful, False otherwise.

    Raises
    ------
    RuntimeError
        If the operation fails and raise_error is True.
    """
    command = ['sudo', 'iwconfig', dev, 'channel', str(channel)]
    try:
        logger.info(f"Running command: {' '.join(command)}")
        subprocess.run(command, check=True)
        logger.info(f"Successfully applied changes to {dev}")
        return True
    except subprocess.CalledProcessError as e:
        report = f"Failed to apply changes to {dev}:\n\tCommand:{command}\n\tError: {e}"
        logger.error(report)
        if raise_error:
            raise RuntimeError(report)
        return False