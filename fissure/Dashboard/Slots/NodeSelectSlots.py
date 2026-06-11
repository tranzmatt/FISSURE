from PyQt5 import QtCore, QtWidgets

# import fissure.comms
import fissure.utils
import qasync
import time
import os
import yaml
import asyncio
import tempfile
import subprocess
import serial.tools.list_ports
import re


@qasync.asyncSlot(QtCore.QObject)
async def refreshClicked(HWSelect: QtCore.QObject):
    """
    Send command to HiprFisr to refresh the list of connected nodes.
    """
    # Send Message to Backend
    await HWSelect.dashboard.backend.nodeRefresh()


@qasync.asyncSlot(QtCore.QObject)
async def selectClicked(HWSelect: QtCore.QObject):
    """
    Send command to HiprFisr to.
    """
    # Get Node UUID
    tableWidget_node_list_widget = HWSelect.tableWidget_node_list

    row = tableWidget_node_list_widget.currentRow()
    node_uuid = str(tableWidget_node_list_widget.item(row, 1).text())
    node_assigned_id = str(tableWidget_node_list_widget.item(row,3).text())

    # Send Message to Backend
    await HWSelect.dashboard.backend.nodeSelectIP(node_uuid)

    # Close Dialog
    HWSelect.close()

    # # Check if Meshtastic handshake is completed
    # if node_assigned_id == "0":
    #     ret = await fissure.Dashboard.UI_Components.Qt5.async_ok_dialog(HWSelect, "Assigned ID = 0. Meshtastic node needs to complete handshake. Please wait for the assigned ID to update and then click Refresh before selecting.")
    #     return

    # # Send Message to Backend
    # get_network_type = str(getattr(HWSelect, f"comboBox_network_type_{tab_index+1}").currentText())
    # if get_network_type == "IP":
    #     await HWSelect.dashboard.backend.nodeSelectIP(str(tab_index), node_uuid)
    # elif get_network_type == "Meshtastic":
    #     await HWSelect.dashboard.backend.nodeSelectLT(str(tab_index), node_uuid)