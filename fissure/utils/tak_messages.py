#!/usr/bin/env python3
import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
import datetime
import hashlib
import os
import pytak
import ssl
import tempfile
from typing import Union, Tuple
import xml.etree.ElementTree as ET
import xml.dom.minidom
import zipfile

from fissure.utils.artifacts import Artifact
from fissure.utils.common import extractFrequencyFromUID, get_fissure_config
from fissure.utils.library import classifyFrequencyFromTextDirect

import fissure.comms

# ---------------------------------------------------------
# Base COT builder
# ---------------------------------------------------------

def _build_base_event(uid: str, stale: int):
    """
    Creates base CoT event using pytak.gen_cot_xml().
    Returns (msg, detail).
    NOTE: pytak.gen_cot_xml() in your version does NOT accept "type",
          so CoT type must be set manually afterward.
    """
    msg = pytak.gen_cot_xml(uid=uid, stale=stale)

    # Normalize in case pytak returned a string or None
    if msg is None:
        # Create minimal CoT structure if pytak fails
        msg = ET.Element("event")
        msg.set("version", "2.0")
        msg.set("uid", uid)
        msg.set("time", "2025-01-01T00:00:00.000Z")
        msg.set("start", "2025-01-01T00:00:00.000Z") 
        msg.set("stale", f"2025-01-01T{stale:02d}:00:00.000Z")
    elif not isinstance(msg, ET.Element):
        msg = ET.fromstring(msg)

    detail = msg.find("detail")
    if detail is None:
        detail = ET.SubElement(msg, "detail")

    return msg, detail


# ---------------------------------------------------------
# Point helpers
# ---------------------------------------------------------

def _set_point_pin(msg, lat, lon, alt):
    """Map-visible pin."""
    pt = msg.find("point")
    if pt is None:
        pt = ET.SubElement(msg, "point")

    pt.set("lat", str(lat))
    pt.set("lon", str(lon))
    pt.set("hae", str(alt))
    pt.set("ce", "0")
    pt.set("le", "0")

def _set_point_suppressed(msg):
    """Event NOT visible on map."""
    pt = msg.find("point")
    if pt is None:
        pt = ET.SubElement(msg, "point")

    pt.set("lat", "0")
    pt.set("lon", "0")
    pt.set("hae", "0")
    pt.set("ce", "9999999")
    pt.set("le", "9999999")


# ---------------------------------------------------------
# Transmission helper
# ---------------------------------------------------------

async def _dispatch_cot(
    component,
    msg,
    destination="broadcast",
    requester_uid=None,
):
    msg_bytes = ET.tostring(msg, encoding="utf-8")

    component.logger.debug(
        "Sending TAK message:\n" + msg_bytes.decode("utf-8")
    )

    component.write_cot_log(msg_bytes)

    # -------------------------------------------------
    # TAK
    # -------------------------------------------------
    if destination in ("broadcast", "tak"):
        if hasattr(component, "clitool") and component.clitool is not None:
            component.clitool.tx_queue.put_nowait(msg_bytes)

    # -------------------------------------------------
    # Dashboard
    # -------------------------------------------------
    if destination in ("broadcast", "dashboard"):
        if component.dashboard_connected:

            PARAMETERS = {
                "raw_xml": msg_bytes.decode("utf-8")
            }

            if requester_uid is not None:
                PARAMETERS["requester_uid"] = requester_uid

            dashboard_msg = {
                fissure.comms.MessageFields.IDENTIFIER: component.identifier,
                fissure.comms.MessageFields.MESSAGE_NAME: "dashboardCoT_Message",
                fissure.comms.MessageFields.PARAMETERS: PARAMETERS,
            }

            await component.dashboard_socket.send_msg(
                fissure.comms.MessageTypes.COMMANDS,
                dashboard_msg
            )


# ---------------------------------------------------------
# Main entrypoint: send()
# ---------------------------------------------------------

async def send(
    component,
    message: dict,
    destination="broadcast",
    requester_uid=None,
):
    """
    Unified TAK message sender.

    Expected input fields (all optional except msg_type and uid):

        msg_type    : "pin" | "event" | "track"
        uid         : CoT UID
        lat/lon/alt : floats
        time        : ISO 8601 string
        remarks     : text
        stale       : int (seconds)
        tak_icon    : CoT symbol type ("a-f-G-U-H", "b-m-p-w", etc.)
        callsign    : optional callsign override
        data        : dict for event messages
        how         : TAK "how" value (optional)
    """

    # -------------------------------------------------
    # Validate required fields
    # -------------------------------------------------
    if "msg_type" not in message:
        component.logger.error("TAK send() missing required field: msg_type")
        return
    if "uid" not in message:
        component.logger.error("TAK send() missing required field: uid")
        return

    mtype = message["msg_type"]
    uid   = message["uid"]

    # Common optional fields
    lat      = message.get("lat")
    lon      = message.get("lon")
    alt      = message.get("alt", 0)
    time     = message.get("time")
    stale    = message.get("stale")
    how      = message.get("how")
    remarks  = message.get("remarks", "")
    tak_icon = message.get("tak_icon")

    # =====================================================
    # 1. PIN (map-visible position marker)
    # =====================================================
    if mtype == "pin":

        # Callsign fallback for pins
        callsign = message.get("callsign", uid)

        # -------------------------------------
        # Apply frequency classification
        # -------------------------------------
        try:
            freq_hz = extractFrequencyFromUID(uid)
            if freq_hz:
                cls = classifyFrequencyFromTextDirect(freq_hz)
                if cls:
                    remarks = f"{remarks}\n{cls}" if remarks else cls
        except Exception as e:
            component.logger.error(f"[TAK] Frequency classification error: {e}")

        # Build base event
        msg, detail = _build_base_event(
            uid=uid,
            stale=stale if stale is not None else 999999999
        )

        msg.set("type", tak_icon or "a-f-G-U-H")
        if how:
            msg.set("how", how)

        ET.SubElement(detail, "contact", {"callsign": callsign})
        ET.SubElement(detail, "remarks").text = remarks

        # -------------------------------------
        # Optional: structured FISSURE alert block for pins
        # (lets WinTAK parse alerts without touching remarks)
        # -------------------------------------
        alert_kind = message.get("alert_kind")
        alert_summary = message.get("alert_summary")
        artifact_id = message.get("artifact_id")
        operation_id = message.get("operation_id")
        sensor_node_id = message.get("sensor_node_id")

        # Gate: only add fissure/alert if caller provided at least a kind or artifact_id
        if alert_kind or artifact_id:
            fiss = ET.SubElement(detail, "fissure")
            alert = ET.SubElement(fiss, "alert")

            if alert_kind:
                ET.SubElement(alert, "kind").text = str(alert_kind)

            if alert_summary:
                ET.SubElement(alert, "summary").text = str(alert_summary)

            if artifact_id:
                ET.SubElement(alert, "artifact_id").text = str(artifact_id)

            if operation_id:
                ET.SubElement(alert, "operation_id").text = str(operation_id)

            if sensor_node_id:
                ET.SubElement(alert, "sensor_node_id").text = str(sensor_node_id)


        _set_point_pin(msg, lat, lon, alt)

        return await _dispatch_cot(
            component,
            msg,
            destination=destination,
            requester_uid=requester_uid,
        )

    # =====================================================
    # 2. EVENT (structured, non-pin)
    # =====================================================
    if mtype == "event":

        msg, detail = _build_base_event(
            uid=uid,
            stale=stale if stale is not None else 30
        )

        msg.set("type", tak_icon or "b-f-t-r")
        if how:
            msg.set("how", how)

        fiss = ET.SubElement(detail, "fissure")

        # Structured FISSURE alert block for table-only alerts
        alert_kind = message.get("alert_kind")
        alert_summary = message.get("alert_summary")
        artifact_id = message.get("artifact_id")
        operation_id = message.get("operation_id")
        sensor_node_id = message.get("sensor_node_id")

        if alert_kind or artifact_id or alert_summary:
            alert = ET.SubElement(fiss, "alert")

            if alert_kind:
                ET.SubElement(alert, "kind").text = str(alert_kind)

            if alert_summary:
                ET.SubElement(alert, "summary").text = str(alert_summary)

            if artifact_id:
                ET.SubElement(alert, "artifact_id").text = str(artifact_id)

            if operation_id:
                ET.SubElement(alert, "operation_id").text = str(operation_id)

            if sensor_node_id:
                ET.SubElement(alert, "sensor_node_id").text = str(sensor_node_id)

            # Optional fallback so summary looks nicer if WinTAK checks contact
            ET.SubElement(detail, "contact", {"callsign": str(alert_summary or alert_kind or uid)})

        else:
            data = message.get("data", {})
            event_type = data.get("event_type", "generic")

            event_node = ET.SubElement(fiss, event_type)
            _serialize_payload(event_node, data, skip_keys={"event_type"})

        # _set_point_suppressed(msg)
        _set_point_pin(msg, lat, lon, alt)  # Include lat/lon/hae but do not plot

        return await _dispatch_cot(
            component,
            msg,
            destination=destination,
            requester_uid=requester_uid,
        )

    # =====================================================
    # 3. TRACK (auto-tracking)
    # =====================================================
    if mtype == "track":

        prefix = component.settings.get("callsign_prefix", "NODE")
        node_meta = component.nodes.get(uid, {})

        nickname = (
            message.get("callsign")
            or node_meta.get("callsign")
            or node_meta.get("nickname")
        )

        if not nickname:
            callsign = f"{prefix}-{uid[:8]}"
        else:
            if nickname.lower().startswith(prefix.lower() + "-"):
                callsign = nickname
            else:
                callsign = f"{prefix}-{nickname}"

        msg, detail = _build_base_event(
            uid=uid,
            stale=stale if stale is not None else 60
        )

        # msg.set("type", tak_icon or "b-m-p-w")
        msg.set("type", tak_icon)  # or "a-f-G-E")
        # msg.set("type", tak_icon or "a-f-G-E-X-M-C")
        if how:
            msg.set("how", how)

        # ET.SubElement(detail, "color", {"argb": "ff0000ff"})

        ET.SubElement(detail, "contact", {"callsign": callsign})
        _set_point_pin(msg, lat, lon, alt)

        status = message.get("status") or node_meta.get("status") or "UNK"
        version = message.get("version") or node_meta.get("version") or ""

        fiss = ET.SubElement(detail, "fissure")
        node = ET.SubElement(fiss, "node")
        ET.SubElement(node, "status").text = str(status)
        if version:
            ET.SubElement(node, "version").text = str(version)

        return await _dispatch_cot(
            component,
            msg,
            destination=destination,
            requester_uid=requester_uid,
        )

    # =====================================================
    # UNKNOWN MESSAGE TYPE
    # =====================================================
    component.logger.error(f"Unknown TAK message type: {mtype}")


def _serialize_payload(parent, data, skip_keys=None):
    """
    Recursively serialize Python dict/lists/scalars into XML.

    parent     = XML node to attach elements to
    data       = python value (dict, list, scalar)
    skip_keys  = keys you do not want to serialize (e.g., event_type)
    """

    if skip_keys is None:
        skip_keys = set()

    if isinstance(data, dict):
        for key, value in data.items():

            if key in skip_keys:
                continue

            # LIST → multiple child nodes
            if isinstance(value, list):
                # Example: "plugins" → <plugin name="...">
                singular = key[:-1] if key.endswith("s") else key
                for item in value:
                    child = ET.SubElement(parent, singular)
                    _serialize_payload(child, item)
                continue

            # DICT → nested structure
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                _serialize_payload(child, value)
                continue

            # SCALAR → simple text node
            child = ET.SubElement(parent, key)
            child.text = str(value)
        return

    # LIST OF NON-DICT ITEMS
    if isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _serialize_payload(child, item)
        return

    # SCALAR VALUE (fallback)
    parent.text = str(data)


def _format_xml_pretty(element: ET.Element) -> str:
    """Format XML element with proper indentation
    
    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        XML element to format
    """
    rough_string = ET.tostring(element, encoding='UTF-8', xml_declaration=True)
    reparsed = xml.dom.minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='UTF-8').decode('UTF-8')


def create_artifact_data_package(artifact: Union[Artifact, dict], file_data: bytes) -> Tuple[bytes, str]:
    """Create TAK-compatible data package for artifact
    
    Parameters
    ----------
    artifact : Union[Artifact, dict]
        Artifact object or dict
    file_data : bytes
        Raw bytes of the artifact file

    Returns
    -------
    Tuple[bytes, str]
        ZIP data as bytes and the artifact filename
    """
    if isinstance(artifact, dict):
        artifact = Artifact.from_dict(artifact)

    # Generate a proper package name
    package_name = f"DP-{artifact.name[:20].upper().replace(' ', '_')}"
    package_uid = artifact.id

    # Create subdirectory
    subdir = artifact.id.replace('-', '').replace('_', '')[:32]
    if not subdir:
        subdir = "artifacts"
    
    # Create temporary ZIP file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the artifact file in subdirectory structure
            artifact_filename = os.path.basename(artifact.file_path)
            # Ensure we have a valid filename
            if not artifact_filename:
                artifact_filename = f"{artifact.name}.bin"
            
            zip_entry_path = f"{subdir}/{artifact_filename}"
            zipf.writestr(zip_entry_path, file_data)

            # Create simple MANIFEST.xml
            manifest = ET.Element("MissionPackageManifest", version="2")
            
            # Configuration - name first, then uid
            config = ET.SubElement(manifest, "Configuration")
            ET.SubElement(config, "Parameter", name="name", value=package_name)
            ET.SubElement(config, "Parameter", name="uid", value=package_uid)
            
            # Contents section
            contents = ET.SubElement(manifest, "Contents")
            ET.SubElement(contents, "Content", 
                         zipEntry=zip_entry_path,
                         ignore="false")
            
            # Format XML
            manifest_xml = _format_xml_pretty(manifest)
            
            # Save manifest in MANIFEST folder
            zipf.writestr("MANIFEST/manifest.xml", manifest_xml.encode('UTF-8'))
        
        # Read the ZIP data
        with open(temp_zip.name, "rb") as f:
            zip_data = f.read()
            
        # Clean up temp file
        os.unlink(temp_zip.name)
    
    return zip_data, artifact_filename


async def send_artifact_event(
    component: object,
    artifact: Union[Artifact, dict],
    artifact_data: bytes,
    destination="broadcast",
    requester_uid=None,
) -> None:
    """Send artifact event to TAK clients
    
    Parameters
    ----------
    component : object
        FISSURE component with TAK clitool
    artifact : Union[Artifact, dict]
        Artifact object or dict
    artifact_data : bytes
        Raw bytes of the artifact file
    """
    if isinstance(artifact, dict):
        artifact = Artifact.from_dict(artifact)

    artifact_id = artifact.id
    tak_data, _ = create_artifact_data_package(artifact, artifact_data)
    
    # Calculate SHA256 checksum
    sha256_hash = hashlib.sha256(tak_data).hexdigest()

    # Build CoT message manually for fileshare
    msg, detail = _build_base_event(
        uid=f"FISSURE-DP-{artifact_id}",  # More descriptive UID
        stale=300  # 5 minute stale time (longer for file transfers)
    )

    # Set proper CoT type for data package - WinTAK uses b-f-t-r for file transfers
    msg.set("type", "b-f-t-r")  # File transfer request
    msg.set("version", "2.0")
    
    # Set proper time attributes
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    msg.set("time", now)
    msg.set("start", now)
    stale_time = (datetime.datetime.utcnow() + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    msg.set("stale", stale_time)

    # Upload the data package to TAK server first
    package_filename = f"DP-{artifact.name[:20].upper().replace(' ', '_')}.zip"
    
    # Try to upload to TAK server
    sender_url = await upload_data_package_to_tak_server(tak_data, sha256_hash, package_filename, component)
    
    if not sender_url:
        component.logger.error("Failed to upload data package to TAK server. Artifact event not sent.") # type: ignore
        return

    # Create fileshare element directly under detail (TAK standard)
    fileshare = ET.SubElement(detail, "fileshare")
    
    # Add attributes
    fileshare.set("filename", package_filename)
    fileshare.set("senderUrl", sender_url)  
    fileshare.set("sizeInBytes", str(len(tak_data)))
    fileshare.set("sha256", sha256_hash)
    fileshare.set("senderUid", f"FISSURE-{artifact.source_id}")
    fileshare.set("senderCallsign", f"FISSURE-{artifact.source_id[:8]}")
    fileshare.set("name", f"DP-{artifact.name[:20].upper().replace(' ', '_')}")

    # Add ackrequest element
    ackrequest = ET.SubElement(detail, "ackrequest")
    ackrequest.set("uid", f"ack-{artifact_id[:8]}")
    ackrequest.set("ackrequested", "true")
    ackrequest.set("tag", f"DP-{artifact.name[:20].upper().replace(' ', '_')}")

    # Set point coordinates (0,0 with high uncertainty)
    point = msg.find("point")
    if point is None:
        point = ET.SubElement(msg, "point")
    point.set("lat", "0.0")
    point.set("lon", "0.0") 
    point.set("hae", "0.0")
    point.set("ce", "9999999.0")
    point.set("le", "9999999.0")

    await _dispatch_cot(
        component,
        msg,
        destination=destination,
        requester_uid=requester_uid,
    )


async def upload_data_package_to_tak_server(tak_data: bytes, sha256_hash: str, filename: str, component) -> Union[str, None]:
    """Upload data package to TAK server sync endpoint
    
    Parameters
    ----------
    tak_data : bytes
        Raw bytes of the TAK data package (ZIP)
    sha256_hash : str
        SHA256 hash of the data package
    filename : str
        Filename of the data package
    component : object
        FISSURE component with logger
    """     
    # Get TAK server configuration
    fissure_config = get_fissure_config()
    tak_config = fissure_config.get('tak', {})
    
    tak_internal_ip = tak_config.get('ip_addr', 'localhost')
    api_port = '8443'  # Standard TAK server HTTPS API port
    p12_cert_path = tak_config.get('webadmin_cert', '')

    # Get external/host IP address for clients to access
    external_ip = tak_config.get('external_ip')
    
    if not external_ip:
        component.logger.error("TAK external_ip not found in configuration")
        return None
    component.logger.info(f"TAK server - Internal IP: {tak_internal_ip}:{api_port}, External IP: {external_ip}")
    
    # Download URL for clients
    download_url = f"https://{external_ip}:{api_port}/Marti/sync/content?hash={sha256_hash}"
    
    # Check if P12 certificate exists
    if not p12_cert_path or not os.path.exists(p12_cert_path):
        component.logger.error(f"Client certificate not found: {p12_cert_path} - TAK server upload requires client certificate authentication")
        return None
    
    component.logger.info(f"Using client certificate: {p12_cert_path}")
    
    # Convert P12 certificate to PEM for aiohttp
    cert_pem_path = None
    key_pem_path = None
    
    try:
        # Import cryptography if available
        try:
            # Load P12 certificate
            with open(p12_cert_path, 'rb') as f:
                p12_data = f.read()
            
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                p12_data, b'atakatak'  # Standard TAK password
            )
            
            if private_key and certificate:
                # Convert to PEM format
                key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
                
                # Save to temporary files
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key') as key_file:
                    key_file.write(key_pem)
                    key_pem_path = key_file.name
                
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.crt') as cert_file:
                    cert_file.write(cert_pem)
                    cert_pem_path = cert_file.name
                
                component.logger.info("Successfully converted P12 to PEM format")
            else:
                raise Exception("Could not extract key/certificate from P12 file")
                
        except ImportError:
            component.logger.error("cryptography library not available - cannot convert P12 certificate")
            return download_url
        
        # Create SSL context with client certificate
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE  # Accept self-signed certs
        ssl_context.load_cert_chain(cert_pem_path, key_pem_path)
        
        component.logger.info("SSL context created with client certificate")
        
        # Prepare upload data
        data = aiohttp.FormData()
        data.add_field('assetfile', tak_data, filename=filename, content_type='application/zip')
        
        # Headers
        headers = {
            'User-Agent': 'FISSURE-TAK-Client/1.0',
            'Accept': 'application/json, */*',
            'Connection': 'close'
        }
        
        # Try upload to TAK server
        upload_url = f"https://{tak_internal_ip}:{api_port}/Marti/sync/upload"
        component.logger.info(f"Uploading to: {upload_url}")
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            
            component.logger.info(f"Uploading {len(tak_data)} bytes with client certificate...")
            
            async with session.post(upload_url, data=data, headers=headers) as response:
                component.logger.info(f"Upload response status: {response.status}")
                
                # Read response for debugging
                try:
                    response_text = await response.text()
                    if response_text:
                        component.logger.info(f"Upload response: {response_text[:300]}")
                except Exception as e:
                    component.logger.warning(f"Could not read response body: {e}")
                
                if response.status in [200, 201, 202]:
                    component.logger.info("Successfully uploaded data package to TAK server!")
                    return download_url
                elif response.status == 409:
                    component.logger.info("Data package already exists on TAK server")
                    return download_url
                elif response.status == 401:
                    component.logger.error("Authentication failed - check client certificate")
                    return download_url
                elif response.status == 403:
                    component.logger.error("Forbidden - check TAK server permissions")
                    return download_url
                else:
                    component.logger.error(f"Upload failed with HTTP {response.status}")
                    return download_url
        
    except Exception as e:
        component.logger.error(f"Certificate upload failed: {e}")
        return download_url
        
    finally:
        # Clean up temporary certificate files
        if cert_pem_path and os.path.exists(cert_pem_path):
            os.unlink(cert_pem_path)
        if key_pem_path and os.path.exists(key_pem_path):
            os.unlink(key_pem_path)
