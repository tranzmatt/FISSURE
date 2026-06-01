#! /usr/bin/env python3
"""OUI Lookup

This module provides functions to look up Organizationally Unique Identifiers (OUIs) for MAC addresses.
"""
import csv
import os
from typing import Union

# vendor plain text (reduced from variants)
# (search term, plain output)
VENDOR_PLAIN = [
    ('d-link', 'd-link'),
    ('tp-link', 'tp-link')
]

class OUILookup(object):
    def __init__(self):
        """
        OUI Lookup class
        """
        self._table = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'resources', 'oui.csv')
        with open(file_path, newline='') as ouifile:
            ouireader = csv.reader(ouifile)
            for lines in ouireader:
                self._table[lines[1]] = lines[2]

    def match(self, mac: str) -> Union[str, None]:
        """
        Match a MAC address to its OUI entry.

        Parameters
        ----------
        mac : str
            The MAC address to match.

        Returns
        -------
        Union[str, None]
            The OUI entry if found, otherwise None.
        """
        tmp_mac = mac.replace(":", "").upper()
        found_mac = tmp_mac[:6]
        return self._table.get(found_mac)

def get_vendor_common_name(name: str) -> Union[str, None]:
    """
    Get the common name for a vendor.

    Parameters
    ----------
    name : str
        The name of the vendor.

    Returns
    -------
    Union[str, None]
        Common name of the vendor if found, otherwise None.
    """
    common_name = None
    for pair in VENDOR_PLAIN:
        if name is not None and pair[0] in name.lower():
            common_name = pair[1]
    return common_name