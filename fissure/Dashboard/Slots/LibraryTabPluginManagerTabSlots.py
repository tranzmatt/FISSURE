#!/usr/bin/env python3
from PyQt5 import QtCore, QtWidgets
import binascii
import os
import qasync
import tempfile
import zipfile

import fissure.comms
from fissure.utils.plugin import get_fissure_plugin_editor_plugins_path, launch_fissure_plugin_editor
from fissure.Dashboard.UI_Components.Qt5 import async_yes_no_dialog

def connect_slots(dashboard: QtCore.QObject):
    """Connect Slots for Library Tab Plugin Manager Tab
    
    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    # set tool button icons
    style = dashboard.style()
    if style is not None:
        dashboard.ui.toolButton_plugin_pkg_path_manual.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        dashboard.ui.toolButton_plugin_pkg_path_auto.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogHelpButton)
        )
        dashboard.ui.toolButton_plugin_pkg_path_refresh.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)
        )
        dashboard.ui.toolButton_plugins_upload.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowUp)
        )
        dashboard.ui.toolButton_plugin_pkgs_hiprfisr_refresh.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)
        )
        dashboard.ui.toolButton_plugin_pkgs_hiprfisr_download.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowDown)
        )
        dashboard.ui.toolButton_plugin_pkgs_hiprfisr_delete.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon)
        )
        dashboard.ui.toolButton_plugin_download_dir_auto.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogHelpButton)
        )
        dashboard.ui.toolButton_plugin_download_dir_manual.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        dashboard.ui.toolButton_plugin_editor.setIcon(
            style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogInfoView)
        )

    dashboard.ui.toolButton_plugin_pkg_path_auto.clicked.connect(
        lambda: _slot_local_plugin_pkg_path_auto(dashboard)
    )

    dashboard.ui.toolButton_plugin_pkg_path_manual.clicked.connect(
        lambda: _slot_local_plugin_pkg_path_manual(dashboard)
    )

    dashboard.ui.toolButton_plugin_pkg_path_refresh.clicked.connect(
        lambda: _slot_local_plugin_pkg_list_refresh(dashboard)
    )

    dashboard.ui.textEdit_plugin_pkg_path.textChanged.connect(
        lambda: _slot_plugin_pkg_path_changed(dashboard)
    )

    dashboard.ui.textEdit_plugin_pkg_path.textEdited.connect(
        lambda: _slot_plugin_pkg_path_changed(dashboard)
    )

    # dashboard.ui.toolButton_plugins_upload.clicked.connect(
    #     lambda: _slot_plugin_upload(dashboard)
    # )

    # dashboard.ui.toolButton_plugin_pkgs_hiprfisr_refresh.clicked.connect(
    #     lambda: _slot_request_hiprfisr_plugin_list(dashboard)
    # )

    # dashboard.ui.toolButton_plugin_pkgs_hiprfisr_delete.clicked.connect(
    #     lambda: _slot_request_hipfisr_plugin_delete(dashboard)
    # )

    dashboard.ui.toolButton_plugin_pkgs_hiprfisr_download.clicked.connect(
        lambda: _slot_request_hipfisr_plugin_download(dashboard)
    )

    dashboard.ui.toolButton_plugin_download_dir_auto.clicked.connect(
        lambda: _slot_plugin_download_dir_auto(dashboard)
    )

    dashboard.ui.toolButton_plugin_download_dir_manual.clicked.connect(
        lambda: _slot_plugin_download_dir_manual(dashboard)
    )

    dashboard.ui.lineEdit_plugin_download_dir.textChanged.connect(
        lambda: _slot_plugin_download_dir_changed(dashboard)
    )

    dashboard.ui.toolButton_plugin_editor.clicked.connect(
        lambda: _slot_plugin_editor(dashboard)
    )

    # # trigger hiprfisr automatic plugin list refresh on tab change
    # _slot_local_plugin_pkg_path_auto(dashboard, False)
    # _slot_plugin_download_dir_auto(dashboard, False)

@qasync.asyncSlot(QtCore.QObject)
async def _slot_local_plugin_pkg_path_auto(dashboard: QtCore.QObject, verbose: bool = True):
    """Set Local Plugin Package Path to Default

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    verbose : bool, optional
        If True, show a message box if the plugin editor is not found, by default True
    """
    plugin_dir = await get_fissure_plugin_editor_plugins_path()
    if plugin_dir is None and verbose:
        dashboard.logger.warning("FISSURE Plugin Editor `fissure-plugin-editor` is not installed or not found in PATH.")
    elif plugin_dir:
        dashboard.ui.textEdit_plugin_pkg_path.setText(plugin_dir)

@qasync.asyncSlot(QtCore.QObject)
async def _slot_plugin_download_dir_auto(dashboard: QtCore.QObject, verbose: bool = True):
    """Set Local Plugin Download Directory to Default

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    verbose : bool, optional
        If True, show a message box if the plugin editor is not found, by default True
    """
    plugin_dir = await get_fissure_plugin_editor_plugins_path()
    if plugin_dir is None and verbose:
        dashboard.logger.warning("FISSURE Plugin Editor `fissure-plugin-editor` is not installed or not found in PATH.")
    elif plugin_dir and os.path.exists(plugin_dir):
        dashboard.ui.lineEdit_plugin_download_dir.setText(plugin_dir)

    if plugin_dir is None:
        dashboard.ui.lineEdit_plugin_download_dir.setText(os.path.join(os.path.expanduser("~"), "Downloads"))

@QtCore.pyqtSlot(QtCore.QObject)
def _slot_local_plugin_pkg_path_manual(dashboard: QtCore.QObject):
    """Set Local Plugin Package Path Manually

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    start_dir = dashboard.ui.textEdit_plugin_pkg_path.text().strip()
    if not start_dir:
        start_dir = QtCore.QDir.homePath()
    # Select a Directory
    dialog = QtWidgets.QFileDialog(dashboard)
    dialog.setWindowTitle("Select Plugin Directory")
    dialog.setDirectory(start_dir)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)

    if dialog.exec_():
        for d in dialog.selectedFiles():
            folder = d
        # Hide Success Label
        dashboard.ui.label2_iq_transfer_folder_success.setVisible(False)

        # Set the text in the text edit
        if folder:
            dashboard.ui.textEdit_plugin_pkg_path.setText(folder)
            _slot_plugin_pkg_path_changed(dashboard)

@QtCore.pyqtSlot(QtCore.QObject)
def _slot_plugin_download_dir_manual(dashboard: QtCore.QObject):
    """Set Local Plugin Download Directory Manually

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    start_dir = dashboard.ui.lineEdit_plugin_download_dir.text().strip()
    if not start_dir:
        start_dir = QtCore.QDir.homePath()
    # Select a Directory
    dialog = QtWidgets.QFileDialog(dashboard)
    dialog.setWindowTitle("Select Plugin Directory")
    dialog.setDirectory(start_dir)
    dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)

    if dialog.exec_():
        for d in dialog.selectedFiles():
            folder = d
        # Hide Success Label
        dashboard.ui.label2_iq_transfer_folder_success.setVisible(False)

        # Set the text in the text edit
        if folder:
            dashboard.ui.lineEdit_plugin_download_dir.setText(folder)

@QtCore.pyqtSlot(QtCore.QObject)
def _slot_local_plugin_pkg_list_refresh(dashboard: QtCore.QObject):
    """Refresh Local Plugin Package List

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    _slot_plugin_pkg_path_changed(dashboard)

@qasync.asyncSlot(QtCore.QObject)
async def _slot_plugin_pkg_path_changed(dashboard: QtCore.QObject):
    dir_path = dashboard.ui.textEdit_plugin_pkg_path.text().strip()
    if QtCore.QDir(dir_path).exists():
        dir_obj = QtCore.QDir(dir_path)
        dir_obj.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        directories = dir_obj.entryList()
        plugin_manager_table: QtWidgets.QTableWidget = dashboard.ui.tableWidget_plugin_pkgs_local
        plugin_manager_table.clearContents()
        plugin_manager_table.setRowCount(0)
        plugin_manager_table.setColumnCount(1)
        for plugin_name in directories:
            plugin_manager_table.insertRow(plugin_manager_table.rowCount())
            plugin_manager_table.setItem(plugin_manager_table.rowCount() - 1, 0, QtWidgets.QTableWidgetItem(plugin_name))

        plugin_manager_table.setHorizontalHeaderLabels(["Plugin Name"])
        plugin_manager_table.resizeColumnsToContents()    
        plugin_manager_table.horizontalHeader().setVisible(True)
        plugin_manager_table.verticalHeader().setVisible(False)
        dashboard.ui.toolButton_plugin_pkg_path_refresh.setEnabled(True)
    else:
        dashboard.ui.toolButton_plugin_pkg_path_refresh.setEnabled(False)

@qasync.asyncSlot(QtCore.QObject)
async def _slot_plugin_download_dir_changed(dashboard: QtCore.QObject):
    dir_path = dashboard.ui.lineEdit_plugin_download_dir.text().strip()
    if QtCore.QDir(dir_path).exists():
        dashboard.ui.toolButton_plugin_pkgs_hiprfisr_download.setEnabled(True)
    else:
        dashboard.ui.toolButton_plugin_pkgs_hiprfisr_download.setEnabled(False)

# @qasync.asyncSlot(QtCore.QObject)
# async def _slot_plugin_upload(dashboard: QtCore.QObject):
#     """Upload Plugin to Central Hub

#     Parameters
#     ----------
#     dashboard : QtCore.QObject
#         FISSURE dashboard
#     """
#     # check if the plugin directory exists
#     plugin_dir = dashboard.ui.textEdit_plugin_pkg_path.text().strip()
#     if not plugin_dir:
#         QtCore.QMessageBox.warning(
#             dashboard,
#             "No Plugin Directory",
#             "Please set a valid plugin directory."
#         )
#         return
    
#     # get selected plugins
#     selected_indexes = dashboard.ui.tableWidget_plugin_pkgs_local.selectedIndexes()
#     selected_plugins = [index.data() for index in selected_indexes]

#     for plugin in selected_plugins:
#         if dashboard.backend.hiprfisr_connected is True:
#             plugin_path = os.path.join(plugin_dir, plugin)
#             if not os.path.exists(plugin_path):
#                 QtCore.QMessageBox.warning(
#                     dashboard,
#                     "Plugin Not Found",
#                     f"Plugin directory '{plugin_path}' does not exist."
#                 )
#                 continue

#             # Create a temporary zip file for the plugin directory
#             with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
#                 with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
#                     for root, dirs, files in os.walk(plugin_path):
#                         for file in files:
#                             file_path = os.path.join(root, file)
#                             arcname = os.path.relpath(file_path, plugin_path)
#                             zipf.write(file_path, arcname)
#                 with open(temp_zip.name, "rb") as f:
#                     zip_data = f.read()
#                 hex_zip_data = binascii.hexlify(zip_data).decode("utf-8").upper()

#             PARAMETERS = {
#                 "plugin_name": plugin,
#                 "plugin_data": hex_zip_data,
#             }
#             msg = {
#                 fissure.comms.MessageFields.IDENTIFIER: fissure.comms.Identifiers.DASHBOARD,
#                 fissure.comms.MessageFields.MESSAGE_NAME: "savePlugin",
#                 fissure.comms.MessageFields.PARAMETERS: PARAMETERS,
#             }
#             await dashboard.backend.hiprfisr_socket.send_msg(
#                 fissure.comms.MessageTypes.COMMANDS, msg
#             )
#     await _slot_request_hiprfisr_plugin_list(dashboard)

# @qasync.asyncSlot(QtCore.QObject)
# async def _slot_request_hiprfisr_plugin_list(dashboard: QtCore.QObject):
#     """Refresh List of Sensor Nodes on HIPRFISR

#     Parameters
#     ----------
#     dashboard : QtCore.QObject
#         FISSURE dashboard
#     """
#     # gray all rows prior to requesting update
#     table: QtWidgets.QTableWidget = dashboard.ui.tableWidget_plugin_pkgs_hiprfisr
#     table.clearContents()
#     table.setRowCount(0)

#     # request update
#     await dashboard.backend.requestPluginNamesHiprfisr()

# @qasync.asyncSlot(QtCore.QObject)
# async def _slot_request_hipfisr_plugin_delete(dashboard: QtCore.QObject):
#     """Delete Selected Plugins from HIPRFISR

#     Parameters
#     ----------
#     dashboard : QtCore.QObject
#         FISSURE dashboard
#     """
#     table: QtWidgets.QTableWidget = dashboard.ui.tableWidget_plugin_pkgs_hiprfisr
#     # Prompt user if all items are selected for deletion
#     selected_items = [item.text() for item in [table.item(i, 0) for i in range(table.rowCount())] if item.isSelected()]
#     if len(selected_items) > 0:
#         reply = await async_yes_no_dialog(
#             dashboard,
#             "You are about to delete the following plugins from HIPRFISR. Are you sure?\n\n" + "\n".join(selected_items)
#         )
#         if reply != QtWidgets.QMessageBox.Yes:
#             return
#     else:
#         return

#     for plugin_name in selected_items:
#         if dashboard.backend.hiprfisr_connected is True:
#             PARAMETERS = {
#                 "plugin_name": plugin_name,
#                 "delete_from_library": True
#             }
#             msg = {
#                 fissure.comms.MessageFields.IDENTIFIER: fissure.comms.Identifiers.DASHBOARD,
#                 fissure.comms.MessageFields.MESSAGE_NAME: "pluginDelete",
#                 fissure.comms.MessageFields.PARAMETERS: PARAMETERS,
#             }
#             await dashboard.backend.hiprfisr_socket.send_msg(
#                 fissure.comms.MessageTypes.COMMANDS, msg
#             )

@qasync.asyncSlot(QtCore.QObject)
async def _slot_request_hipfisr_plugin_download(dashboard: QtCore.QObject):
    """Download Selected Plugins from HIPRFISR

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    table: QtWidgets.QTableWidget = dashboard.ui.tableWidget_plugin_pkgs_hiprfisr
    for item in [table.item(i, 0) for i in range(table.rowCount())]:
        if item.isSelected():
            plugin_name = item.text()
            if dashboard.backend.hiprfisr_connected is True:
                PARAMETERS = {
                    "plugin_name": plugin_name,
                }
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: fissure.comms.Identifiers.DASHBOARD,
                    fissure.comms.MessageFields.MESSAGE_NAME: "sendPlugin",
                    fissure.comms.MessageFields.PARAMETERS: PARAMETERS,
                }
                await dashboard.backend.hiprfisr_socket.send_msg(
                    fissure.comms.MessageTypes.COMMANDS, msg
                )

@qasync.asyncSlot(QtCore.QObject)
async def _slot_plugin_editor(dashboard: QtCore.QObject):
    """Launch the FISSURE Plugin Editor

    Parameters
    ----------
    dashboard : QtCore.QObject
        FISSURE dashboard
    """
    if not launch_fissure_plugin_editor():
        dashboard.logger.warning("FISSURE Plugin Editor `fissure-plugin-editor` is not installed or not found in PATH.")