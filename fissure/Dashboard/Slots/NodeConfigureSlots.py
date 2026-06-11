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
async def guess(NodeConfigure: QtCore.QObject):
    """
    Cycles through possible values for the selected row in the scan results table.
    """
    get_uid = NodeConfigure.uid
    scan_results_table = NodeConfigure.tableWidget_scan_results
    get_row = scan_results_table.currentRow()
    get_row_text = []
    for n in range(0, scan_results_table.columnCount()):
        get_row_text.append(str(scan_results_table.item(get_row, n).text()))

    # Send Message for HIPRFISR to Sensor Node Connections
    get_network_type = "IP"
    if get_network_type == "IP":
        await NodeConfigure.dashboard.backend.guessHardware(get_uid, get_row, get_row_text, NodeConfigure.guess_index)
    elif get_network_type == "Meshtastic":
        await NodeConfigure.dashboard.backend.guessHardwareLT(get_uid, get_row, get_row_text, NodeConfigure.guess_index)


@qasync.asyncSlot(QtCore.QObject)
async def probe(NodeConfigure: QtCore.QObject):
    """
    Probes the selected radio in the scan results table.
    """
    # Row Number and Text
    get_uid = NodeConfigure.uid
    scan_results_table = NodeConfigure.tableWidget_scan_results
    get_row = scan_results_table.currentRow()
    get_row_text = []
    for n in range(0, scan_results_table.columnCount()):
        get_row_text.append(str(scan_results_table.item(get_row, n).text()))

    # Show Label
    scan_results_label =  NodeConfigure.label2_scan_results_probe
    scan_results_label.setVisible(True)

    # Disable Probe Button
    probe_button = NodeConfigure.pushButton_scan_results_probe

    # Send Message for HIPRFISR to Sensor Node Connections
    get_network_type = "IP"
    if get_network_type == "IP":
        probe_button.setEnabled(False)
        await NodeConfigure.dashboard.backend.probeHardware(get_uid, get_row_text)
    elif get_network_type == "Meshtastic":
        await NodeConfigure.dashboard.backend.probeHardwareLT(get_uid, get_row_text)


@qasync.asyncSlot(QtCore.QObject)
async def scan(NodeConfigure: QtCore.QObject):
    """
    Performs a mass hardware scan on the local/remote sensor node and returns the results.
    """
    # Save Checked Items in Current Tab
    get_node_uid = NodeConfigure.uid
    list_widget = NodeConfigure.listWidget_scan
    hardware_list = []
    for n in range(0, list_widget.count()):
        if list_widget.item(n).checkState() == QtCore.Qt.Checked:
            hardware_list.append(str(list_widget.item(n).text()))

    # Send Message for HIPRFISR to Sensor Node Connections
    get_network_type = "IP"
    if get_network_type == "IP":
        await NodeConfigure.dashboard.backend.scanHardware(get_node_uid, hardware_list)
    elif get_network_type == "Meshtastic":
        await NodeConfigure.dashboard.backend.scanHardwareLT(get_node_uid, hardware_list)


@QtCore.pyqtSlot(QtCore.QObject)
def add_to_hardware(NodeConfigure: QtCore.QObject, suppress_warning=False):
    scan_table = NodeConfigure.tableWidget_scan_results
    hw_table = NodeConfigure.tableWidget_hardware
    src_row = scan_table.currentRow()

    if src_row < 0:
        if not suppress_warning:
            fissure.Dashboard.UI_Components.Qt5.errorMessage("Select a scan result first.")
        return

    def get_scan(col):
        item = scan_table.item(src_row, col)
        return item.text().strip() if item else ""

    scan_type          = get_scan(0)
    scan_uid           = get_scan(1)
    scan_radio_name    = get_scan(2)
    scan_serial        = get_scan(3)
    scan_interface     = get_scan(4)
    scan_ip_address    = get_scan(5)
    scan_daughterboard = get_scan(6)

    category = "wifi_adapter" if "802.11x" in scan_type.lower() else "sdr"

    if scan_uid == "":
        scan_uid = get_next_hardware_uid(hw_table, category)

    dst_row = hw_table.rowCount()
    hw_table.insertRow(dst_row)

    values = [
        "No",
        category,
        scan_uid,
        scan_type,
        scan_radio_name,
        scan_serial,
        scan_interface,
        scan_ip_address,
        scan_daughterboard,
        "",
    ]

    for col, value in enumerate(values):
        item = QtWidgets.QTableWidgetItem(str(value))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        hw_table.setItem(dst_row, col, item)

    hw_table.resizeColumnsToContents()
    hw_table.resizeRowsToContents()
    hw_table.horizontalHeader().setStretchLastSection(False)
    hw_table.horizontalHeader().setStretchLastSection(True)
    hw_table.selectRow(dst_row)


def get_next_hardware_uid(hw_table, category):
    existing = []

    for row in range(hw_table.rowCount()):
        cat_item = hw_table.item(row, 1)
        uid_item = hw_table.item(row, 2)

        if not cat_item or not uid_item:
            continue

        if cat_item.text().strip() != category:
            continue

        try:
            existing.append(int(uid_item.text().strip()))
        except ValueError:
            pass

    return str(max(existing) + 1) if existing else "0"


@QtCore.pyqtSlot(QtCore.QObject)
def remove_hardware(NodeConfigure: QtCore.QObject):
    """
    Removes a row from the hardware table.
    """
    # Remove Row
    hardware_table = NodeConfigure.tableWidget_hardware
    get_row = hardware_table.currentRow()
    hardware_table.removeRow(get_row)
    if get_row == hardware_table.rowCount():
        hardware_table.setCurrentCell(hardware_table.rowCount() - 1, 0)
    elif get_row >= 0:
        hardware_table.setCurrentCell(get_row, 0)


@QtCore.pyqtSlot(QtCore.QObject)
def add_selected(NodeConfigure: QtCore.QObject):
    """
    Adds the selected row in the scan results table to the hardware table.
    """
    add_to_hardware(NodeConfigure, True)


@QtCore.pyqtSlot(QtCore.QObject)
def add_all(NodeConfigure: QtCore.QObject):
    """
    Adds the all the rows in the scan results table to all the tables.
    """
    scan_results_table = NodeConfigure.tableWidget_scan_results
    total_rows = scan_results_table.rowCount()

    for row in range(total_rows):
        scan_results_table.setCurrentCell(row,0)  # Set the current row to simulate selection
        add_to_hardware(NodeConfigure, True)


@QtCore.pyqtSlot(QtCore.QObject)
def scan_results_remove(NodeConfigure: QtCore.QObject):
    """
    Removes a row from the scan results table.
    """
    # Retrieve widgets
    get_tableWidget = NodeConfigure.tableWidget_scan_results

    # Remove the selected row
    get_row = get_tableWidget.currentRow()
    get_tableWidget.removeRow(get_row)

    # Select a new row after deletion
    if get_tableWidget.rowCount() > 0:
        new_row = min(get_row, get_tableWidget.rowCount() - 1)  # Ensure valid row index
        get_tableWidget.setCurrentCell(new_row, 0)

    # Disable buttons if table is empty
    if get_tableWidget.rowCount() == 0:
        # Get all relevant push buttons
        get_pushButtons = [
            NodeConfigure.pushButton_add_all,
            NodeConfigure.pushButton_add_selected,
            NodeConfigure.pushButton_scan_results_remove,
            NodeConfigure.pushButton_scan_results_remove_all,
            NodeConfigure.pushButton_scan_results_probe,
            NodeConfigure.pushButton_scan_results_guess,
        ]

        for btn in get_pushButtons:
            btn.setEnabled(False)
        get_tableWidget.setEnabled(False)


@QtCore.pyqtSlot(QtCore.QObject)
def scan_results_remove_all(NodeConfigure: QtCore.QObject):
    """
    Removes all rows from the scan results table.
    """
    # Retrieve widgets
    get_tableWidget = NodeConfigure.tableWidget_scan_results

    # Get all relevant push buttons
    get_pushButtons = [
        NodeConfigure.pushButton_add_all,
        NodeConfigure.pushButton_add_selected,
        NodeConfigure.pushButton_scan_results_remove,
        NodeConfigure.pushButton_scan_results_remove_all,
        NodeConfigure.pushButton_scan_results_probe,
        NodeConfigure.pushButton_scan_results_guess,
    ]

    # Remove all rows
    get_tableWidget.setRowCount(0)

    # Disable buttons when table is empty
    for btn in get_pushButtons:
        btn.setEnabled(False)
    
    get_tableWidget.setEnabled(False)


@QtCore.pyqtSlot(QtCore.QObject)
def manual(NodeConfigure: QtCore.QObject):
    """
    Manually adds the checked hardware to the scan results table.
    """
    # Dynamically retrieve widgets based on tab index
    get_listWidget = NodeConfigure.listWidget_scan
    get_tableWidget = NodeConfigure.tableWidget_scan_results

    # Get all relevant push buttons
    get_pushButtons = [
        NodeConfigure.pushButton_add_all,
        NodeConfigure.pushButton_add_selected,
        NodeConfigure.pushButton_scan_results_remove,
        NodeConfigure.pushButton_scan_results_remove_all,
        NodeConfigure.pushButton_scan_results_probe,
        NodeConfigure.pushButton_scan_results_guess,
    ]

    # Fill Scan Results Table with Checked Items
    for n in range(get_listWidget.count()):
        if get_listWidget.item(n).checkState() == QtCore.Qt.Checked:
            rows = get_tableWidget.rowCount()
            get_tableWidget.setRowCount(rows + 1)
            table_item = QtWidgets.QTableWidgetItem(str(get_listWidget.item(n).text()))
            table_item.setTextAlignment(QtCore.Qt.AlignCenter)
            get_tableWidget.setItem(rows, 0, table_item)
            
            for m in range(1, get_tableWidget.columnCount()):
                empty_table_item = QtWidgets.QTableWidgetItem("")
                empty_table_item.setTextAlignment(QtCore.Qt.AlignCenter)
                get_tableWidget.setItem(rows, m, empty_table_item)

            NodeConfigure.highlight_hardware_id(get_tableWidget, rows)

    # Update UI
    get_tableWidget.setCurrentCell(get_tableWidget.rowCount() - 1, 0)
    get_tableWidget.resizeColumnsToContents()
    get_tableWidget.resizeRowsToContents()
    get_tableWidget.horizontalHeader().setStretchLastSection(False)
    get_tableWidget.horizontalHeader().setStretchLastSection(True)

    # Enable relevant buttons if there are rows in the table
    if get_tableWidget.rowCount() > 0:
        for btn in get_pushButtons:
            btn.setEnabled(True)
        get_tableWidget.setEnabled(True)


@qasync.asyncSlot(QtCore.QObject)
async def ping(NodeConfigure: QtCore.QObject):
    """
    Send ping command to the Sensor Node IP.
    """
    # Ping IP Address
    get_ip = NodeConfigure.ip_address

    response = os.system("ping -c 1 " + get_ip)
    if response == 0:
        NodeConfigure.dashboard.logger.info(get_ip + " is up!")
        ret = await fissure.Dashboard.UI_Components.Qt5.async_ok_dialog(NodeConfigure, get_ip + " is up!")
    else:
        NodeConfigure.dashboard.logger.info(get_ip + " is down!")
        ret = await fissure.Dashboard.UI_Components.Qt5.async_ok_dialog(NodeConfigure, get_ip + " is down!")


@qasync.asyncSlot(QtCore.QObject)
async def apply(NodeConfigure: QtCore.QObject):
    """
    Save selected sensor node changes locally and send them to the node.
    """
    dashboard = NodeConfigure.dashboard
    node_uid = dashboard.selected_node_uid
    settings = NodeConfigure.settings
    sensor_node_settings = NodeConfigure.sensor_node_settings

    if not node_uid or settings is None:
        fissure.Dashboard.UI_Components.Qt5.errorMessage("No sensor node selected.")
        return

    nickname = str(NodeConfigure.textEdit_nickname.toPlainText()).strip()
    location_description = str(NodeConfigure.textEdit_location.toPlainText()).strip()
    notes = str(NodeConfigure.textEdit_notes.toPlainText()).strip()

    if not nickname:
        fissure.Dashboard.UI_Components.Qt5.errorMessage("Enter a nickname for the sensor node.")
        return

    sensor_node_settings["nickname"] = nickname
    sensor_node_settings["location_description"] = location_description
    sensor_node_settings["notes"] = notes
    sensor_node_settings["hardware"] = build_hardware_settings_from_table(NodeConfigure)

    dashboard.selected_node_settings = settings

    # Update selected node button text
    dashboard.ui.label_top_configure_node_title.setText(nickname)

    # Send updated settings to node
    await dashboard.backend.updateNodeSettings(
        node_uid=node_uid,
        settings_dict=settings,
    )

    # Update Dashboard Tabs
    dashboard.configureSelectedNodeHardware()

    NodeConfigure.accept()


def build_hardware_settings_from_table(NodeConfigure: QtCore.QObject):
    table = NodeConfigure.tableWidget_hardware

    hardware = {
        "defaults": {
            "sdr": "",
            "wifi_adapter": "",
        },
        "sdrs": {},
        "wifi_adapters": {},
    }

    def get(row, col):
        item = table.item(row, col)
        return item.text().strip() if item else ""

    for row in range(table.rowCount()):
        default = get(row, 0)
        category = get(row, 1)
        uid = get(row, 2)
        hw_type = get(row, 3)
        radio_name = get(row, 4)
        serial = get(row, 5)
        interface = get(row, 6)
        ip_address = get(row, 7)
        daughterboard = get(row, 8)
        notes = get(row, 9)

        if not uid:
            continue

        if category == "sdr":
            hardware["sdrs"][uid] = {
                "radio_name": radio_name,
                "type": hw_type,
                "serial": serial,
                "daughterboard": daughterboard,
                "ip_address": ip_address,
                "network_interface": interface,
                "notes": notes,
            }

            if default.lower() == "yes":
                hardware["defaults"]["sdr"] = uid

        elif category == "wifi_adapter":
            hardware["wifi_adapters"][uid] = {
                "radio_name": radio_name,
                "interface": interface,
                "notes": notes,
            }

            if default.lower() == "yes":
                hardware["defaults"]["wifi_adapter"] = uid

    return hardware


@qasync.asyncSlot(QtCore.QObject)
async def find(NodeConfigure: QtCore.QObject):
    """ 
    Finds the GPS location for the provided method.
    """
    # GPS Data Format
    get_format = str(NodeConfigure.comboBox_format.currentText())
    get_gps_source = str(NodeConfigure.comboBox_gps_source.currentText())
    get_network_type = "IP"
    get_uid = NodeConfigure.uid
    find_widget = NodeConfigure.pushButton_find

    # Send the Message

    # Local, Connected: IP
    if get_network_type == "IP":
        if get_gps_source == "gpsd":
            await NodeConfigure.dashboard.backend.findGPS_Coordinates(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Meshtastic":
            await NodeConfigure.dashboard.backend.findGPS_Coordinates(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Saved":
            await NodeConfigure.dashboard.backend.findGPS_Coordinates(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Internet":
            await NodeConfigure.dashboard.backend.findGPS_Coordinates(get_uid, get_gps_source, get_format)
        else:
            return

        # Disable the Find Button
        find_widget.setEnabled(False)

    # Remote, Connected: Meshtastic
    elif get_network_type == "Meshtastic":
        # Send the Message
        if get_gps_source == "gpsd":
            await NodeConfigure.dashboard.backend.findGPS_CoordinatesLT(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Meshtastic":
            await NodeConfigure.dashboard.backend.findGPS_CoordinatesLT(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Saved":
            await NodeConfigure.dashboard.backend.findGPS_CoordinatesLT(get_uid, get_gps_source, get_format)
        elif get_gps_source == "Internet":
            await NodeConfigure.dashboard.backend.findGPS_CoordinatesLT(get_uid, get_gps_source, get_format)
        else:
            return

        # Disable the Find Button
        # find_widget.setEnabled(False)
    else:
        NodeConfigure.dashboard.logger.error("Sensor node not connected. Unable to retrieve GPS location.")


@QtCore.pyqtSlot(QtCore.QObject)
def map(NodeConfigure: QtCore.QObject):
    """ 
    Maps the GPS location in default KML viewer (likely Google Earth Pro).
    """
    # Gather Location
    get_location = NodeConfigure.label2_lat_lon_alt.text()
    get_format = str(NodeConfigure.comboBox_format.currentText())

    # Convert to DD if needed
    try:
        if get_format == "MGRS":
            lat, lon = fissure.utils.mgrs_to_dd(get_location)
        elif get_format == "DMS":
            lat, lon = fissure.utils.dms_to_dd(get_location)
        else:  # Already in Decimal Degrees
            parts = get_location.split(',')
            if len(parts) != 2:
                raise ValueError(f"Invalid Decimal Degrees format: {get_location}")
            
            lat = parts[0].strip()
            lon = parts[1].strip()

        NodeConfigure.dashboard.logger.debug(f"✅ Converted Coordinates: {lat}, {lon}")  # Debugging output

    except ValueError as e:
        NodeConfigure.dashboard.logger.error(f"❌ Error in coordinate conversion: {e}")
        return

    except Exception as e:
        NodeConfigure.dashboard.logger.error(f"❌ Unexpected error: {e}")
        return

    # Construct KML
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Placemark>
        <name>GPS Location</name>
        <Point>
          <coordinates>{lon},{lat},0</coordinates>
        </Point>
      </Placemark>
    </kml>
    """

    # Create a temporary KML file in /tmp/
    with tempfile.NamedTemporaryFile(delete=False, suffix=".kml", dir="/tmp/") as temp_kml:
        temp_kml.write(kml_content.encode('utf-8'))
        temp_kml_path = temp_kml.name

    NodeConfigure.dashboard.logger.info(f"KML written to: {temp_kml_path}")

    # Open the file using xdg-open (respects user's default KML viewer)
    subprocess.run(["xdg-open", temp_kml_path], check=False)


@qasync.asyncSlot(QtCore.QObject)
async def ip_gps_beacon_enable_disable(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to enable/disable the GPS TAK beacon.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.gpsBeaconEnableDisableIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_reboot(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to reboot the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.rebootIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_uptime(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the uptime of the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.uptimeIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_memory(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the memory usage of the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.memoryIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_disk(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the disk usage of the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.diskIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_cpu(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the CPU percentage of the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.cpuIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_processes(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the processes on the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.processesIP(NodeConfigure.uid)


@qasync.asyncSlot(QtCore.QObject)
async def ip_ifconfig(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the ifconfig output on the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.ifconfigIP(NodeConfigure.uid)  


@qasync.asyncSlot(QtCore.QObject)
async def ip_iwconfig(NodeConfigure: QtCore.QObject):
    """
    Sends a message to the HIPRFISR to retrieve the iwconfig output on the sensor node.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.iwconfigIP(NodeConfigure.uid)  


@qasync.asyncSlot(QtCore.QObject)
async def ip_ping(NodeConfigure: QtCore.QObject):
    """
    Send command to HiprFisr to ping the host running the Sensor Node and await response.
    """
    # Send Message to Backend
    await NodeConfigure.dashboard.backend.pingIP(NodeConfigure.uid)


# @QtCore.pyqtSlot(QtCore.QObject)
# def meshtastic_refresh(NodeConfigure: QtCore.QObject):
#     """ 
#     Refreshes the list of potential serial ports in the combobox.
#     """
#     # Move Page to the Right
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     serial_port_widget = getattr(NodeConfigure, f"comboBox_meshtastic_port_{tab_index+1}")

#     # ports = [port.device for port in serial.tools.list_ports.comports()]

#     # Only include /dev/ttyACM* and /dev/ttyUSB*
#     ports = [
#         port.device 
#         for port in serial.tools.list_ports.comports() 
#         if '/dev/ttyACM' in port.device or '/dev/ttyUSB' in port.device
#     ]
#     ports.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])

#     serial_port_widget.clear()
#     serial_port_widget.addItems(ports if ports else ["No ports found"])


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_info(NodeConfigure: QtCore.QObject):
#     """ 
#     Opens a pop up with serial port and device information.
#     """
#     # Issue the Command
#     path = "/dev/serial/by-id/"
#     if os.path.exists(path):
#         output_text = os.popen(f"ls -l {path}").read()
#     else:
#         output_text = "No serial devices found"

#     # Open a Dialog
#     ret = await fissure.Dashboard.UI_Components.Qt5.async_ok_dialog(NodeConfigure, output_text)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_recall_info(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve sensor node information from its config file.
#     """
#     # Send Message to Backend
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     await NodeConfigure.dashboard.backend.recallInfoMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_recall_hardware(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve sensor node information from its config file.
#     """
#     # Send Message to Backend
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     await NodeConfigure.dashboard.backend.recallHardwareMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_recall_status(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve sensor node status.
#     """
#     # Send Message to Backend
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     await NodeConfigure.dashboard.backend.recallStatusMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_gps_beacon_enable(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to enable the GPS TAK beacon.
#     """
#     # Send Message to Backend
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     await NodeConfigure.dashboard.backend.gpsBeaconEnableMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_gps_beacon_disable(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to disable the GPS TAK beacon.
#     """
#     # Send Message to Backend
#     tab_index = NodeConfigure.tabWidget_nodes.currentIndex()
#     await NodeConfigure.dashboard.backend.gpsBeaconDisableMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_reboot(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to reboot the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.rebootMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_uptime(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the uptime of the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.uptimeMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_memory(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the memory usage of the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.memoryMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_disk(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the disk usage of the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.diskMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_cpu(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the CPU percentage of the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.cpuMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_processes(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the processes on the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.processesMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_ifconfig(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the ifconfig output on the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.ifconfigMeshtasticLT(NodeConfigure.uid)


# @qasync.asyncSlot(QtCore.QObject)
# async def meshtastic_iwconfig(NodeConfigure: QtCore.QObject):
#     """
#     Sends a message to the HIPRFISR to retrieve the iwconfig output on the sensor node.
#     """
#     # Send Message to Backend
#     await NodeConfigure.dashboard.backend.iwconfigMeshtasticLT(NodeConfigure.uid)