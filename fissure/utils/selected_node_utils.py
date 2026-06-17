


def get_selected_node_settings(dashboard):
    settings = getattr(dashboard, "selected_node_settings", {}) or {}

    if not isinstance(settings, dict):
        return {}

    return settings


def get_selected_node_hardware_settings(dashboard):
    settings = get_selected_node_settings(dashboard)

    sensor_node_settings = settings.get("Sensor Node", {}) or {}

    if not isinstance(sensor_node_settings, dict):
        return {}

    hardware_settings = sensor_node_settings.get("hardware", {}) or {}

    if not isinstance(hardware_settings, dict):
        return {}

    return hardware_settings


def get_selected_node_wifi_interfaces(dashboard):
    interfaces = []

    hardware_settings = get_selected_node_hardware_settings(dashboard)

    wifi_adapters = hardware_settings.get("wifi_adapters", {}) or {}

    if not isinstance(wifi_adapters, dict):
        return interfaces

    for uid, entry in wifi_adapters.items():
        if not isinstance(entry, dict):
            continue

        interface = str(entry.get("interface", "") or "").strip()

        if interface:
            interfaces.append(interface)

    return interfaces


def get_selected_node_local_remote(dashboard):
    settings = get_selected_node_settings(dashboard)

    return str(
        settings
        .get("Sensor Node", {})
        .get("local_remote", "")
    ).strip().lower()


def selected_node_is_local(dashboard):
    return get_selected_node_local_remote(dashboard) == "local"


def selected_node_is_remote(dashboard):
    return get_selected_node_local_remote(dashboard) == "remote"


def get_selected_node_network_type(dashboard):
    settings = get_selected_node_settings(dashboard)

    return str(
        settings
        .get("Sensor Node", {})
        .get("network_type", "")
    ).strip().lower()


def selected_node_is_ip(dashboard):
    return get_selected_node_network_type(dashboard) == "ip"


def selected_node_is_meshtastic(dashboard):
    return get_selected_node_network_type(dashboard) == "meshtastic"


def cycleSelectedNodeWifiInterface(owner, text_widget):
    """
    Cycles through configured Wi-Fi interfaces for the selected node and writes
    the result into the provided text widget.
    """
    dashboard = owner.dashboard

    if not getattr(dashboard, "selected_node_uid", ""):
        return

    interfaces = get_selected_node_wifi_interfaces(
        dashboard,
    )

    if not interfaces:
        return

    if not hasattr(owner, "guess_index"):
        owner.guess_index = 0

    if owner.guess_index >= len(interfaces):
        owner.guess_index = 0

    text_widget.setPlainText(interfaces[owner.guess_index])

    owner.guess_index += 1


def cycleSelectedNodeWifiInterfaceIntoTable(owner, table_widget, row, column):
    """
    Cycles through configured Wi-Fi interfaces for the selected node and writes
    the result into a table cell.
    """
    dashboard = owner.dashboard

    if not getattr(dashboard, "selected_node_uid", ""):
        return

    interfaces = get_selected_node_wifi_interfaces(
        dashboard,
    )

    if not interfaces:
        return

    if not hasattr(owner, "guess_index"):
        owner.guess_index = 0

    if owner.guess_index >= len(interfaces):
        owner.guess_index = 0

    table_item = QtWidgets.QTableWidgetItem(interfaces[owner.guess_index])
    table_item.setTextAlignment(QtCore.Qt.AlignCenter)
    table_widget.setItem(row, column, table_item)

    owner.guess_index += 1


def refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def get_selected_node_display_name(dashboard, node=None):
    """
    Resolve display name for the dashboard-selected node.
    """
    node = node or {}

    settings = get_selected_node_settings(dashboard)

    nickname = (
        settings
        .get("Sensor Node", {})
        .get("nickname", "")
    )

    return (
        nickname
        or node.get("nickname")
        or node.get("callsign")
        or getattr(dashboard, "selected_node_uid", "")
        or "Selected Node"
    )


def set_selected_node_connection_state(dashboard, connected: bool, node=None):
    """
    Update the selected-node top-card connection display.
    """
    node = node or {}

    if not getattr(dashboard, "selected_node_uid", None):
        return

    display_name = get_selected_node_display_name(dashboard, node)

    ip_text = (
        node.get("node_ip_address")
        or node.get("ip")
        or getattr(dashboard, "selected_node_ip", "")
        or ""
    )

    if ip_text == "ipc":
        ip_text = "Local Process"

    frame = dashboard.ui.frame_top_configure_node

    frame.setProperty("selected", "true")
    frame.setProperty("connected", "true" if connected else "false")
    frame.setProperty("pressed", "false")

    if connected:
        dashboard.ui.label_top_configure_node_title.setText(
            f"{display_name}  (Online)"
        )
        dashboard.ui.label_top_configure_node_subtitle.setText(str(ip_text))
        dashboard.ui.label_top_configure_node_subtitle2.setText(
            "Click to view and configure this node"
        )
        frame.setToolTip("Click to view and configure this node.")
    else:
        dashboard.ui.label_top_configure_node_title.setText(
            f"{display_name}  (Disconnected)"
        )
        dashboard.ui.label_top_configure_node_subtitle.setText(str(ip_text))
        dashboard.ui.label_top_configure_node_subtitle2.setText(
            "Last heartbeat timed out"
        )
        frame.setToolTip("Selected sensor node is disconnected.")

    refresh_widget_style(frame)