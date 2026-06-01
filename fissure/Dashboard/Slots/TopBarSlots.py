from ..UI_Components import HardwareSelectDialog
from PyQt5 import QtCore, QtWidgets

import time


@QtCore.pyqtSlot(QtCore.QObject, int)
def sensor_node_leftClick(dashboard: QtCore.QObject, node_idx: int):
    button: QtWidgets.QPushButton = getattr(dashboard.ui, f"pushButton_top_node{node_idx+1}")
    dashboard.logger.debug(f"[Sensor Node {node_idx+1}] Clicked")

    button.setChecked(True)
    dashboard.openPopUp("HardwareSelectDialog", HardwareSelectDialog, node_idx)
    button.setChecked(False)


@QtCore.pyqtSlot(QtCore.QObject, int)
def sensor_node_rightClick(dashboard: QtCore.QObject, node_idx: int):
    """ 
    Highlight sensor node on right-click.
    """
    # Unhighlight
    if node_idx == -1:
        dashboard.active_sensor_node = -1
        dashboard.ui.pushButton_top_node1.setStyleSheet("")
        dashboard.configureTSI_Hardware(node_idx)
        dashboard.configurePD_Hardware(node_idx)
        dashboard.configureAttackHardware(node_idx)
        dashboard.configureIQ_Hardware(node_idx)
        dashboard.configureArchiveHardware(node_idx)
        dashboard.configureSensorNodeHardware(node_idx)
        dashboard.statusBar().dialog.label1_sensor_node.setText("No Sensor Nodes Connected")
        dashboard.refreshStatusBarText()
        return
        
    # Highlight
    top_buttons = [dashboard.ui.pushButton_top_node1, dashboard.ui.pushButton_top_node2, dashboard.ui.pushButton_top_node3, dashboard.ui.pushButton_top_node4, dashboard.ui.pushButton_top_node5]
    if str(top_buttons[node_idx].text()) != "New Sensor Node":
        dashboard.active_sensor_node = node_idx
        for n in range(0,5):
            if n == node_idx:
                top_buttons[node_idx].setStyleSheet("color: rgb(0,0,0); border: 2px solid darkGray; border-radius: 10px; border-style: outset; border-color: " + dashboard.backend.settings['color3'] + "; background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,stop: 0 #ffb477, stop: 1 #db8d4e); min-width: 80px;")
            else:
                top_buttons[n].setStyleSheet("")
            
        # TSI
        dashboard.configureTSI_Hardware(node_idx)
        
        # PD
        dashboard.configurePD_Hardware(node_idx)

        # Attack                
        dashboard.configureAttackHardware(node_idx)

        # IQ
        dashboard.configureIQ_Hardware(node_idx)

        # Archive
        dashboard.configureArchiveHardware(node_idx)
        
        # Sensor Node
        dashboard.configureSensorNodeHardware(node_idx)

        # Change Status Bar Text
        dashboard.statusBar().dialog.label1_sensor_node.setText("Sensor Node " + str(node_idx + 1))
        dashboard.refreshStatusBarText()

        # Swap Between High Throughput and Low Throughput Modes
        get_sensor_node = ['sensor_node1','sensor_node2','sensor_node3','sensor_node4','sensor_node5']
        if dashboard.backend.settings[get_sensor_node[node_idx]]["network_type"] == "IP":
            dashboard.configureHighThroughputWidgets()
        elif dashboard.backend.settings[get_sensor_node[node_idx]]["network_type"] == "Meshtastic":
            dashboard.configureLowThroughputWidgets()


@QtCore.pyqtSlot(QtCore.QObject)
def demoClicked(dashboard: QtCore.QObject):
    """ 
    Stops demo mode.
    """
    # Set the Flag
    dashboard.logger.info("Stop Demo Mode")
    dashboard.stop_demo_flag = True
    dashboard.ui.pushButton_demo.setText("Stopping...")
    
