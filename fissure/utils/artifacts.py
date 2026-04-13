#!/usr/bin/env python3
"""Artifact Management for FISSURE Operations
"""
import json
import os
import uuid
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Union, Tuple
import logging
import gzip
import re
import zipfile

ARTIFACT_NODE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + "/artifacts_node"
ARTIFACT_SYSTEM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + "/artifacts_system"


def calculate_file_checksum(file_path: str) -> str:
    """Calculate SHA256 checksum of a file.
    
    Parameters
    ----------
    file_path : str
        Path to the file

    Returns
    -------
    str
        SHA256 checksum of the file
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@dataclass
class Artifact:
    """Represents an artifact created by an operation."""
    id: str  # Unique ID for the artifact
    source_id: str  # ID of the source that created the artifact
    operation_id: str  # ID of the operation that created the artifact
    name: str  # Human-readable name for the artifact
    file_path: str  # Path to the artifact file
    artifact_type: str  # Type of artifact (e.g., "log", "data", "image")
    file_size: int  # Size of the artifact file in bytes
    created_at: str  # ISO formatted creation timestamp
    modified_at: str  # ISO formatted modification timestamp
    metadata: Dict[str, Any]  # Additional metadata for the artifact
    checksum: str  # SHA256 checksum of the artifact file

    def __post_init__(self):
        """Validate that no fields are None."""
        for field_name, field_value in self.__dict__.items():
            if field_value is None:
                raise ValueError(f"Field '{field_name}' cannot be None")

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], enforce_fields: bool = False) -> 'Artifact':
        """Create artifact from dictionary.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary representation of the artifact
        enforce_fields : bool, optional
            Whether to enforce presence of all fields, by default False
        """
        if 'id' not in data or data['id'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: id")
            data['id'] = str(uuid.uuid4())

        if 'source_id' not in data or data['source_id'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: source_id")
            data['source_id'] = "unknown_source"

        if 'operation_id' not in data or data['operation_id'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: operation_id")
            data['operation_id'] = "unknown_operation"

        if 'name' not in data or data['name'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: name")
            data['name'] = "unknown_artifact"

        if 'file_path' not in data or data['file_path'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: file_path")
            data['file_path'] = ""

        if 'artifact_type' not in data or data['artifact_type'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: artifact_type")
            data['artifact_type'] = "unknown_type"

        if 'file_size' not in data or data['file_size'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: file_size")
            if 'file_path' in data and os.path.exists(data['file_path']):
                data['file_size'] = os.path.getsize(data['file_path'])
            else:
                data['file_size'] = 0

        if 'created_at' not in data or data['created_at'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: created_at")
            data['created_at'] = datetime.now().isoformat()

        if 'modified_at' not in data or data['modified_at'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: modified_at")
            data['modified_at'] = data['created_at']

        if 'metadata' not in data or data['metadata'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: metadata")
            data['metadata'] = {}

        if 'checksum' not in data or data['checksum'] is None:
            if enforce_fields:
                raise ValueError("Missing required field: checksum")
            if 'file_path' in data and os.path.exists(data['file_path']):
                data['checksum'] = calculate_file_checksum(data['file_path'])
            else:
                data['checksum'] = ""

        return cls(**data)


class ArtifactManager(object):
    """Manages artifacts on the sensor node."""
    
    def __init__(self, base_dir: str = ARTIFACT_NODE_DIR, logger: Union[logging.Logger, None] = None):
        """Initialize the artifact manager.
        
        Parameters
        ----------
        base_dir : Union[str, None], optional
            Base directory for storing artifacts, defaults to ARTIFACT_NODE_DIR
        logger : Union[logging.Logger, None], optional
            Logger instance, defaults to None to use module logger
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self.index_file = os.path.join(base_dir, "index.json")
        self._artifacts = self._load_index()

    def _load_index(self) -> Dict[str, Artifact]:
        """Load the artifact index from disk.
        
        Returns
        -------
        Dict[str, Artifact]
            Mapping of artifact IDs to Artifact instances
        """
        if not os.path.exists(self.index_file):
            return {}
        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
            return {aid: Artifact.from_dict(artifact_data) for aid, artifact_data in data.items()}
        except Exception as e:
            self.logger.error(f"Failed to load artifact index: {e}")
            return {}
    
    def _save_index(self) -> None:
        """Save the artifact index to disk."""
        try:
            data = {aid: artifact.to_dict() for aid, artifact in self._artifacts.items()}
            with open(self.index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save artifact index: {e}")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file.
        
        Parameters
        ----------
        file_path : str
            Path to the file

        Returns
        -------
        str
            SHA256 checksum of the file
        """
        try:
            return calculate_file_checksum(file_path)
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _get_operation_dir(self, operation_id: str) -> str:
        """Get the directory path for an operation's artifacts.

        Parameters
        ----------
        operation_id : str
            The operation ID

        Returns
        -------
        str
            The directory path for the operation's artifacts
        """
        return os.path.join(self.base_dir, operation_id)

    def create_operation_dir(self, operation_id: str) -> Tuple[str, str]:
        """Create directory for an operation's artifacts.

        Parameters
        ----------
        operation_id : str
            The operation ID

        Returns
        -------
        str, str
            The directory path for the operation's artifacts and the directory path for the operation's files
        """
        op_dir = self._get_operation_dir(operation_id)
        os.makedirs(op_dir, exist_ok=True)
        file_dir = os.path.join(op_dir, "files")
        os.makedirs(file_dir, exist_ok=True)
        return op_dir, file_dir

    def get_filename_for_artifact(self, operation_id: str, ext: str) -> str:
        """Generate a unique filename for an artifact file.

        Parameters
        ----------
        operation_id : str
            The operation ID
        ext : str
            The file extension

        Returns
        -------
        str
            Unique filename
        """
        _, file_dir = self.create_operation_dir(operation_id)
        return os.path.join(file_dir, str(uuid.uuid4()) + ext)

    def create_artifact(self, source_id: str, operation_id: str, file_path: str, name: str, artifact_type: str, metadata: Union[Dict[str, Any], None] = None) -> str:
        """Create a new artifact record.
        
        Parameters
        ----------
        source_id : str
            ID of the source that created the artifact
        operation_id : str
            ID of the operation that created the artifact
        file_path : str
            Path to the artifact file
        name : str
            Human-readable name for the artifact
        artifact_type : str
            Type of artifact (e.g., "log", "data", "image")
        metadata : Dict[str, Any], optional
            Additional metadata for the artifact
            
        Returns
        -------
        str
            The artifact ID
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Artifact file does not exist: {file_path}")
            return ""
        
        # Check if file_path basename is a UUID4
        basename = os.path.basename(file_path)
        basename_no_ext = os.path.splitext(basename)[0]
        try:
            parsed_uuid = uuid.UUID(basename_no_ext, version=4)
            # Verify it's actually a UUID4
            if parsed_uuid.version != 4:
                self.logger.debug(f"File basename '{basename_no_ext}' is a UUID but not version 4; will generate new UUID for artifact ID")
                artifact_id = str(uuid.uuid4())
            else:
                self.logger.info(f"File basename '{basename_no_ext}' is a valid UUID4 and will be used as artifact ID")
                artifact_id = basename_no_ext
        except ValueError:
            self.logger.debug(f"File basename '{basename_no_ext}' is not a valid UUID4; will generate new UUID for artifact ID")
            artifact_id = str(uuid.uuid4())
        
        # Create operation directory if it doesn't exist
        _ = self.create_operation_dir(operation_id)

        # Calculate file size and checksum
        file_size = os.path.getsize(file_path)
        checksum = self._calculate_checksum(file_path)

        # Create artifact record
        created_at = datetime.now().isoformat()
        artifact = Artifact(
            id=artifact_id,
            source_id=source_id,
            operation_id=operation_id,
            name=name,
            file_path=file_path,
            artifact_type=artifact_type,
            created_at=created_at,
            modified_at=created_at,
            file_size=file_size,
            checksum=checksum,
            metadata=metadata or {}
        )

        # Store in index
        self._artifacts[artifact_id] = artifact
        self._save_index()
        
        self.logger.info(f"Created artifact {artifact_id}: {name} ({artifact_type})")
        return artifact_id

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get an artifact by ID.
        
        Parameters
        ----------
        artifact_id : str
            The artifact ID
            
        Returns
        -------
        Optional[Artifact]
            The artifact or None if not found
        """
        return self._artifacts.get(artifact_id)
    
    def get_artifacts_by_operation(self, operation_id: str) -> List[Artifact]:
        """Get all artifacts for a specific operation.
        
        Parameters
        ----------
        operation_id : str
            The operation ID
            
        Returns
        -------
        List[Artifact]
            List of artifacts for the operation
        """
        return [artifact for artifact in self._artifacts.values() 
                if artifact.operation_id == operation_id]
    
    def get_all_artifacts(self) -> List[Artifact]:
        """Get all artifacts.
        
        Returns
        -------
        List[Artifact]
            List of all artifacts
        """
        return list(self._artifacts.values())

    def get_data(self, artifact_id: str, compress: bool = False) -> Optional[bytes]:
        """Retrieve data from an artifact's file.

        Parameters
        ----------
        artifact_id : str
            The artifact ID
        compress : bool, optional
            Whether to compress the data after retrieval, by default False

        Returns
        -------
        Optional[bytes]
            The artifact data or None if not found/error
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            self.logger.error(f"Artifact not found: {artifact_id}")
            return None

        if re.match(r'^sensor-[\w-]+://', artifact.file_path):
            self.logger.error(f"Cannot retrieve data from remote artifact: {artifact.file_path}")
            return None
        elif not os.path.exists(artifact.file_path):
            self.logger.error(f"Artifact file does not exist: {artifact.file_path}")
            return None
        
        try:
            with open(artifact.file_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read data from artifact {artifact_id}: {e}")
            return None

        if compress:
            data = gzip.compress(data)

        return data

    def update_artifact(self, artifact_id: str, file_path: Union[str, None] = None, metadata: Union[Dict[str, Any], None] = None) -> bool:
        """Update an artifact's metadata and optionally its file.
        
        Parameters
        ----------
        artifact_id : str
            The artifact ID
        file_path : Union[str, None], optional
            New file path for the artifact, by default None
        metadata : Union[Dict[str, Any], None], optional
            New metadata to merge into existing metadata, by default None
            
        Returns
        -------
        bool
            True if updated successfully, False otherwise
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            self.logger.error(f"Artifact not found: {artifact_id}")
            return False
        
        if file_path:
            if not os.path.exists(file_path):
                self.logger.error(f"New artifact file does not exist: {file_path}")
                return False
            artifact.file_path = file_path
        else:
            file_path = artifact.file_path
        artifact.file_size = os.path.getsize(file_path)
        artifact.checksum = self._calculate_checksum(file_path)
        
        if metadata:
            artifact.metadata.update(metadata)

        artifact.modified_at = datetime.now().isoformat()
        
        self._save_index()
        
        self.logger.info(f"Updated artifact {artifact_id}: {artifact.name}")
        return True

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact and its file.
        
        Parameters
        ----------
        artifact_id : str
            The artifact ID
            
        Returns
        -------
        bool
            True if deleted successfully, False otherwise
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            self.logger.error(f"Artifact not found: {artifact_id}")
            return False
        
        # Remove file if it exists
        if os.path.exists(artifact.file_path):
            try:
                os.remove(artifact.file_path)
            except Exception as e:
                self.logger.error(f"Failed to delete artifact file {artifact.file_path}: {e}")
                return False
        
        # Remove from index
        del self._artifacts[artifact_id]
        self._save_index()
        
        self.logger.info(f"Deleted artifact {artifact_id}: {artifact.name}")
        return True
    
    def cleanup_operation(self, operation_id: str) -> int:
        """Delete all artifacts for an operation.
        
        Parameters
        ----------
        operation_id : str
            The operation ID
            
        Returns
        -------
        int
            Number of artifacts deleted
        """
        artifacts = self.get_artifacts_by_operation(operation_id)
        deleted_count = 0
        
        for artifact in artifacts:
            if self.delete_artifact(artifact.id):
                deleted_count += 1
        
        # Remove operation directory if empty
        op_dir = self._get_operation_dir(operation_id)
        if os.path.exists(op_dir) and not os.listdir(op_dir):
            try:
                os.rmdir(op_dir)
            except Exception as e:
                self.logger.error(f"Failed to remove operation directory {op_dir}: {e}")
        
        return deleted_count


    def create_zip_artifact_from_folder(
        self,
        source_id: str,
        operation_id: str,
        folder: str,
        name: str,
        metadata: dict,
        arc_prefix: Optional[str] = None,
    ):
        """
        Zips up a folder and creates an artifact for the zip file. Used in sending SOI evidence to TAK.
        
        :param self: Description
        :param source_id: Description
        :type source_id: str
        :param operation_id: Description
        :type operation_id: str
        :param folder: Description
        :type folder: str
        :param name: Description
        :type name: str
        :param metadata: Description
        :type metadata: dict
        :param arc_prefix: Description
        :type arc_prefix: str | None
        """

        zip_path = self.get_filename_for_artifact(operation_id, ".zip")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(folder):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, folder)
                    arcname = os.path.join(arc_prefix or "", rel)
                    zf.write(full, arcname=arcname)

        return self.create_artifact(
            source_id=source_id,
            operation_id=operation_id,
            file_path=zip_path,
            name=name,
            artifact_type="application/zip",
            metadata=metadata,
        )


class ArtifactTracker(object):
    """Tracks artifacts across the system."""
    def __init__(self, base_dir: str = ARTIFACT_SYSTEM_DIR, logger: Union[logging.Logger, None] = None):
        """Initialize the artifact tracker.
        
        Parameters
        ----------
        base_dir : Union[str, None], optional
            Base directory for storing artifacts, defaults to ARTIFACT_SYSTEM_DIR
        logger : Union[logging.Logger, None], optional
            Logger instance, defaults to None to use module logger
        """
        self.base_dir = base_dir
        self.logger = logger or logging.getLogger(__name__)
        self.index_file = os.path.join(base_dir, "index.json")
        
        # Ensure base directory exists
        os.makedirs(base_dir, exist_ok=True)
        
        # Load existing index
        self._artifacts = self._load_index()

    def _load_index(self) -> Dict[str, Artifact]:
        """Load the artifact index from disk.
        
        Returns
        -------
        Dict[str, Artifact]
            Mapping of artifact IDs to Artifact instances
        """
        if not os.path.exists(self.index_file):
            return {}
        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
            return {aid: Artifact.from_dict(artifact_data) for aid, artifact_data in data.items()}
        except Exception as e:
            self.logger.error(f"Failed to load artifact index: {e}")
            return {}
    
    def _save_index(self) -> None:
        """Save the artifact index to disk."""
        try:
            data = {aid: artifact.to_dict() for aid, artifact in self._artifacts.items()}
            with open(self.index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save artifact index: {e}")

    def sync_index(self, artifacts: List[Union[Artifact, dict]]) -> None:
        """Update the artifact index with a provided list of artifacts.

        Parameters
        ----------
        artifacts : List[Union[Artifact, dict]]
            List of artifacts to sync
        """
        for artifact in artifacts:
            self.add_artifact(artifact, update_index=False)
        self._save_index()

    def add_artifact(self, artifact: Union[Artifact, dict], update_index: bool = True) -> None:
        """Add an artifact to the tracker.

        Parameters
        ----------
        artifact : Union[Artifact, dict]
            The artifact to add, either as an Artifact instance or a dictionary
        update_index : bool, optional
            Whether to update the index file after adding, by default True
        """
        if isinstance(artifact, dict):
            artifact = Artifact.from_dict(artifact)
        if artifact.id in self._artifacts and self._artifacts[artifact.id].checksum == artifact.checksum:
            self.logger.debug(f"Artifact {artifact.id} already exists with same checksum; skipping add")
            return  # No action needed for duplicate with same checksum
        self.logger.debug(f"Adding artifact {artifact.id}: {artifact.name}")
        self._artifacts[artifact.id] = artifact
        if update_index:
            self.logger.info(f"Artifact {artifact.id} added to tracker")
            self._save_index()

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get an artifact by ID.
        
        Parameters
        ----------
        artifact_id : str
            The artifact ID
            
        Returns
        -------
        Optional[Artifact]
            The artifact or None if not found
        """
        return self._artifacts.get(artifact_id)

    def update_artifact(self, artifact: Union[Artifact, dict]) -> bool:
        """Update an artifact's metadata and optionally its file.
        
        Parameters
        ----------
        artifact : Union[Artifact, dict]
            The artifact to update, either as an Artifact instance or a dictionary

        Returns
        -------
        bool
            True if updated successfully, False otherwise
        """
        if isinstance(artifact, dict):
            artifact = Artifact.from_dict(artifact)

        existing_artifact = self._artifacts.get(artifact.id)
        if not existing_artifact:
            self.add_artifact(artifact)
            return True

        existing_artifact.name = artifact.name
        existing_artifact.artifact_type = artifact.artifact_type
        existing_artifact.metadata.update(artifact.metadata)
        if artifact.file_path:
            existing_artifact.file_path = artifact.file_path
        existing_artifact.file_size = artifact.file_size
        existing_artifact.modified_at = artifact.modified_at
        existing_artifact.checksum = artifact.checksum

        self._save_index()
        self.logger.info(f"Updated artifact {artifact.id}: {artifact.name}")
        return True

    def save_data(self, artifact_id: str, data: bytes, compressed: bool = False) -> bool:
        """Save data to an artifact's file.

        Parameters
        ----------
        artifact_id : str
            The artifact ID
        data : bytes
            The data to write to the artifact file
        compressed : bool, optional
            Whether to compress the data before saving, by default False

        Returns
        -------
        bool
            True if saved successfully, False otherwise
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            self.logger.error(f"Artifact not found: {artifact_id}")
            return False
        
        target_path = os.path.join(self.base_dir, artifact.source_id, artifact.operation_id, os.path.basename(artifact.file_path))

        if compressed:
            data = gzip.decompress(data)

        try:
            with open(target_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            self.logger.error(f"Failed to save data to artifact {artifact_id}: {e}")
            return False

        artifact.file_path = target_path

        file_size = os.path.getsize(target_path)
        if file_size != artifact.file_size:
            self.logger.warning(f"File size mismatch when saving data to artifact {artifact_id}: expected {artifact.file_size}, got {file_size}")
            artifact.file_size = file_size
        
        checksum_calc = calculate_file_checksum(target_path)
        if checksum_calc != artifact.checksum:
            self.logger.warning(f"Checksum mismatch when saving data to artifact {artifact_id}: expected {artifact.checksum}, got {checksum_calc}")
            artifact.checksum = checksum_calc
        
        self._artifacts[artifact_id] = artifact
        self._save_index()
        self.logger.info(f"Saved data to artifact {artifact_id}: {artifact.name}")
        return True

    def get_data(self, artifact_id: str, compress: bool = False) -> Optional[bytes]:
        """Retrieve data from an artifact's file.

        Parameters
        ----------
        artifact_id : str
            The artifact ID
        compress : bool, optional
            Whether to compress the data after retrieval, by default False

        Returns
        -------
        Optional[bytes]
            The artifact data or None if not found/error
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            self.logger.error(f"Artifact not found: {artifact_id}")
            return None

        if re.match(r'^sensor-[\w-]+://', artifact.file_path):
            self.logger.error(f"Cannot retrieve data from remote artifact: {artifact.file_path}")
            return None
        elif not os.path.exists(artifact.file_path):
            self.logger.error(f"Artifact file does not exist: {artifact.file_path}")
            return None
        
        try:
            with open(artifact.file_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read data from artifact {artifact_id}: {e}")
            return None

        if compress:
            data = gzip.compress(data)

        return data

    def get_artifacts_source_id(self, source_id: str, sortby: Optional[str] = None) -> List[Artifact]:
        """Get all artifacts created by a specific source.

        Parameters
        ----------
        source_id : str
            The source ID
        sortby : Optional[str], optional
            Metadata key to sort by, by default None

        Returns
        -------
        List[Artifact]
            List of artifacts created by the source
        """
        artifacts = [artifact for artifact in self._artifacts.values() if artifact.source_id == source_id]

        if sortby is not None:
            artifacts = sorted(artifacts, key=lambda x: x.__getattribute__(sortby))

        return artifacts

# Global artifact manager instance
_artifact_manager = None

def get_artifact_manager() -> ArtifactManager:
    """Get the global artifact manager instance.
    
    Returns
    -------
    ArtifactManager
        The global artifact manager instance
    """
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager()
    return _artifact_manager

