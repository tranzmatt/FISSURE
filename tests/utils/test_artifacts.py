#!/usr/bin/env python3
"""Tests for the FISSURE artifact management system."""

import pytest
import tempfile
import os
import uuid
import shutil
from unittest.mock import patch

# Import the modules we're testing
from fissure.utils.artifacts import Artifact, ArtifactManager, get_artifact_manager


class TestArtifact:
    """Test cases for the Artifact dataclass."""
    
    def test_artifact_creation(self):
        """Test creating an Artifact instance."""
        artifact = Artifact(
            id="test-id",
            source_id="source-123",
            operation_id="op-123",
            name="Test Artifact",
            file_path="/tmp/test.log",
            artifact_type="log",
            created_at="2024-01-01T00:00:00",
            file_size=1024,
            metadata={"test": True},
            checksum="abc123",
            modified_at="2024-01-01T01:00:00"
        )
        
        assert artifact.id == "test-id"
        assert artifact.source_id == "source-123"
        assert artifact.operation_id == "op-123"
        assert artifact.name == "Test Artifact"
        assert artifact.artifact_type == "log"
        assert artifact.file_size == 1024
        assert artifact.metadata == {"test": True}
        assert artifact.modified_at == "2024-01-01T01:00:00"
    
    def test_artifact_creation_without_modified_at(self):
        """Test creating an Artifact instance with modified_at same as created_at."""
        artifact = Artifact(
            id="test-id",
            source_id="source-123",
            operation_id="op-123",
            name="Test Artifact",
            file_path="/tmp/test.log",
            artifact_type="log",
            created_at="2024-01-01T00:00:00",
            file_size=1024,
            metadata={"test": True},
            checksum="abc123",
            modified_at="2024-01-01T00:00:00"  # Same as created_at
        )
        
        assert artifact.modified_at == artifact.created_at
    
    def test_artifact_to_dict(self):
        """Test converting artifact to dictionary."""
        artifact = Artifact(
            id="test-id",
            source_id="source-123",
            operation_id="op-123",
            name="Test Artifact",
            file_path="/tmp/test.log",
            artifact_type="log",
            created_at="2024-01-01T00:00:00",
            file_size=1024,
            metadata={"test": True},
            checksum="abc123",
            modified_at="2024-01-01T01:00:00"
        )
        
        artifact_dict = artifact.to_dict()
        
        assert isinstance(artifact_dict, dict)
        assert artifact_dict["id"] == "test-id"
        assert artifact_dict["source_id"] == "source-123"
        assert artifact_dict["operation_id"] == "op-123"
        assert artifact_dict["metadata"] == {"test": True}
        assert artifact_dict["modified_at"] == "2024-01-01T01:00:00"
    
    def test_artifact_from_dict(self):
        """Test creating artifact from dictionary."""
        data = {
            "id": "test-id",
            "source_id": "source-123",
            "operation_id": "op-123",
            "name": "Test Artifact",
            "file_path": "/tmp/test.log",
            "artifact_type": "log",
            "created_at": "2024-01-01T00:00:00",
            "file_size": 1024,
            "metadata": {"test": True},
            "checksum": "abc123",
            "modified_at": "2024-01-01T01:00:00"
        }
        
        artifact = Artifact.from_dict(data)
        
        assert artifact.id == "test-id"
        assert artifact.source_id == "source-123"
        assert artifact.operation_id == "op-123"
        assert artifact.metadata == {"test": True}
        assert artifact.modified_at == "2024-01-01T01:00:00"


class TestArtifactManager:
    """Test cases for the ArtifactManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def artifact_manager(self, temp_dir):
        """Create an ArtifactManager instance with temporary directory."""
        return ArtifactManager(base_dir=temp_dir)
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file."""
        test_file_path = os.path.join(temp_dir, "test_file.txt")
        with open(test_file_path, 'w') as f:
            f.write("This is a test file for artifact testing.")
        return test_file_path
    
    def test_artifact_manager_init(self, temp_dir):
        """Test ArtifactManager initialization."""
        am = ArtifactManager(base_dir=temp_dir)
        
        assert am.base_dir == temp_dir
        assert os.path.exists(temp_dir)
        assert isinstance(am._artifacts, dict)
    
    def test_artifact_manager_init_default_path(self):
        """Test ArtifactManager initialization with default path."""
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = "/mock/path"
            with patch('os.makedirs'):
                am = ArtifactManager()
                expected_path = "/mock/path/artifacts"
                assert expected_path in am.base_dir
    
    def test_create_operation_dir(self, artifact_manager, temp_dir):
        """Test creating operation directory."""
        operation_id = "test-op-123"
        
        op_dir, file_dir = artifact_manager.create_operation_dir(operation_id)
        
        assert os.path.exists(op_dir)
        assert os.path.exists(file_dir)
        assert op_dir == os.path.join(temp_dir, operation_id)
        assert file_dir == os.path.join(temp_dir, operation_id, "files")
    
    def test_get_filename_for_artifact(self, artifact_manager):
        """Test generating filename for artifact."""
        operation_id = "test-op-123"
        ext = ".log"
        
        filename = artifact_manager.get_filename_for_artifact(operation_id, ext)
        
        assert filename.endswith(ext)
        assert operation_id in filename
        assert "files" in filename
        # Check that it's a UUID in the filename
        basename = os.path.basename(filename)
        uuid_part = os.path.splitext(basename)[0]
        uuid.UUID(uuid_part)  # This will raise if not a valid UUID
    
    def test_create_artifact_success(self, artifact_manager, test_file):
        """Test creating an artifact successfully."""
        operation_id = "test-op-123"
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log",
            metadata={"source": "test"}
        )
        
        assert artifact_id != ""
        assert uuid.UUID(artifact_id)  # Valid UUID
        
        # Check artifact was stored
        artifact = artifact_manager.get_artifact(artifact_id)
        assert artifact is not None
        assert artifact.name == "Test Log"
        assert artifact.operation_id == operation_id
        assert artifact.artifact_type == "log"
        assert artifact.metadata == {"source": "test"}
        assert artifact.file_size > 0
        assert artifact.checksum != ""
    
    def test_create_artifact_with_uuid_filename(self, artifact_manager, temp_dir):
        """Test creating an artifact with UUID filename uses that UUID as artifact ID."""
        operation_id = "test-op-123"
        test_uuid = str(uuid.uuid4())
        test_file_path = os.path.join(temp_dir, f"{test_uuid}.txt")
        
        with open(test_file_path, 'w') as f:
            f.write("Test content")
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file_path,
            name="Test File",
            artifact_type="data"
        )
        
        assert artifact_id == test_uuid
    
    def test_create_artifact_nonexistent_file(self, artifact_manager):
        """Test creating artifact with nonexistent file."""
        operation_id = "test-op-123"
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path="/nonexistent/file.txt",
            name="Missing File",
            artifact_type="log"
        )
        
        assert artifact_id == ""
    
    def test_get_artifact(self, artifact_manager, test_file):
        """Test getting an artifact by ID."""
        operation_id = "test-op-123"
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log"
        )
        
        artifact = artifact_manager.get_artifact(artifact_id)
        
        assert artifact is not None
        assert artifact.id == artifact_id
        assert artifact.name == "Test Log"
    
    def test_get_nonexistent_artifact(self, artifact_manager):
        """Test getting a nonexistent artifact."""
        artifact = artifact_manager.get_artifact("nonexistent-id")
        assert artifact is None
    
    def test_get_artifacts_by_operation(self, artifact_manager, test_file, temp_dir):
        """Test getting artifacts by operation ID."""
        operation_id = "test-op-123"
        other_operation_id = "other-op-456"
        
        # Create test files
        test_file2 = os.path.join(temp_dir, "test_file2.txt")
        with open(test_file2, 'w') as f:
            f.write("Another test file")
        
        # Create artifacts for first operation
        id1 = artifact_manager.create_artifact("test-source", operation_id, test_file, "File 1", "log")
        id2 = artifact_manager.create_artifact("test-source", operation_id, test_file2, "File 2", "data")
        
        # Create artifact for second operation
        id3 = artifact_manager.create_artifact("test-source", other_operation_id, test_file, "File 3", "log")
        
        artifacts = artifact_manager.get_artifacts_by_operation(operation_id)
        
        assert len(artifacts) == 2
        artifact_ids = [a.id for a in artifacts]
        assert id1 in artifact_ids
        assert id2 in artifact_ids
        assert id3 not in artifact_ids
    
    def test_get_all_artifacts(self, artifact_manager, test_file):
        """Test getting all artifacts."""
        operation_id1 = "test-op-123"
        operation_id2 = "test-op-456"
        
        artifact_manager.create_artifact("test-source", operation_id1, test_file, "File 1", "log")
        artifact_manager.create_artifact("test-source", operation_id2, test_file, "File 2", "data")
        
        all_artifacts = artifact_manager.get_all_artifacts()
        
        assert len(all_artifacts) == 2
    
    def test_delete_artifact(self, artifact_manager, test_file):
        """Test deleting an artifact."""
        operation_id = "test-op-123"
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log"
        )
        
        # Verify artifact exists
        assert artifact_manager.get_artifact(artifact_id) is not None
        
        # Delete artifact
        result = artifact_manager.delete_artifact(artifact_id)
        
        assert result is True
        assert artifact_manager.get_artifact(artifact_id) is None
        assert not os.path.exists(test_file)  # File should be deleted
    
    def test_delete_nonexistent_artifact(self, artifact_manager):
        """Test deleting a nonexistent artifact."""
        result = artifact_manager.delete_artifact("nonexistent-id")
        assert result is False
    
    def test_cleanup_operation(self, artifact_manager, test_file, temp_dir):
        """Test cleaning up all artifacts for an operation."""
        operation_id = "test-op-123"
        other_operation_id = "other-op-456"
        
        # Create additional test file
        test_file2 = os.path.join(temp_dir, "test_file2.txt")
        with open(test_file2, 'w') as f:
            f.write("Another test file")
        
        # Create artifacts for target operation
        artifact_manager.create_artifact("test-source", operation_id, test_file, "File 1", "log")
        artifact_manager.create_artifact("test-source", operation_id, test_file2, "File 2", "data")
        
        # Create artifact for other operation
        artifact_manager.create_artifact("test-source", other_operation_id, test_file, "File 3", "log")
        
        # Verify initial state
        target_artifacts = artifact_manager.get_artifacts_by_operation(operation_id)
        other_artifacts = artifact_manager.get_artifacts_by_operation(other_operation_id)
        assert len(target_artifacts) == 2
        assert len(other_artifacts) == 1
        
        # Cleanup target operation
        deleted_count = artifact_manager.cleanup_operation(operation_id)
        
        assert deleted_count == 2
        assert len(artifact_manager.get_artifacts_by_operation(operation_id)) == 0
        assert len(artifact_manager.get_artifacts_by_operation(other_operation_id)) == 1
    
    def test_index_persistence(self, temp_dir, test_file):
        """Test that the artifact index persists across manager instances."""
        operation_id = "test-op-123"
        
        # Create artifact with first manager instance
        am1 = ArtifactManager(base_dir=temp_dir)
        artifact_id = am1.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Persistent Test",
            artifact_type="log"
        )
        
        # Create second manager instance
        am2 = ArtifactManager(base_dir=temp_dir)
        
        # Verify artifact is accessible from second instance
        artifact = am2.get_artifact(artifact_id)
        assert artifact is not None
        assert artifact.name == "Persistent Test"
    
    def test_checksum_calculation(self, artifact_manager, temp_dir):
        """Test checksum calculation."""
        test_content = "This is test content for checksum calculation."
        test_file_path = os.path.join(temp_dir, "checksum_test.txt")
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        checksum = artifact_manager._calculate_checksum(test_file_path)
        
        assert checksum != ""
        assert len(checksum) == 64  # SHA256 hex string length
        
        # Verify checksum is consistent
        checksum2 = artifact_manager._calculate_checksum(test_file_path)
        assert checksum == checksum2
    
    def test_update_artifact_metadata_only(self, artifact_manager, test_file):
        """Test updating artifact metadata without changing file."""
        operation_id = "test-op-123"
        
        # Create artifact
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log",
            metadata={"version": 1, "source": "test"}
        )
        
        # Get original artifact
        original_artifact = artifact_manager.get_artifact(artifact_id)
        original_modified_at = original_artifact.modified_at
        assert original_modified_at == original_artifact.created_at  # Initially same
        original_checksum = original_artifact.checksum
        
        # Update metadata
        result = artifact_manager.update_artifact(
            artifact_id=artifact_id,
            metadata={"version": 2, "updated_by": "test_suite"}
        )
        
        assert result is True
        
        # Verify updates
        updated_artifact = artifact_manager.get_artifact(artifact_id)
        assert updated_artifact.modified_at != original_modified_at  # Should be different now
        assert updated_artifact.metadata["version"] == 2
        assert updated_artifact.metadata["source"] == "test"  # Original metadata preserved
        assert updated_artifact.metadata["updated_by"] == "test_suite"
        assert updated_artifact.checksum == original_checksum  # File unchanged
    
    def test_update_artifact_with_new_file(self, artifact_manager, test_file, temp_dir):
        """Test updating artifact with a new file."""
        operation_id = "test-op-123"
        
        # Create artifact
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log"
        )
        
        # Create new file with different content
        new_test_file = os.path.join(temp_dir, "new_test_file.txt")
        with open(new_test_file, 'w') as f:
            f.write("This is updated content for the test file.")
        
        # Get original artifact
        original_artifact = artifact_manager.get_artifact(artifact_id)
        original_size = original_artifact.file_size
        original_checksum = original_artifact.checksum
        
        # Update with new file
        result = artifact_manager.update_artifact(
            artifact_id=artifact_id,
            file_path=new_test_file,
            metadata={"updated_reason": "new_content"}
        )
        
        assert result is True
        
        # Verify updates
        updated_artifact = artifact_manager.get_artifact(artifact_id)
        assert updated_artifact.modified_at is not None
        assert updated_artifact.file_path == new_test_file
        assert updated_artifact.file_size != original_size
        assert updated_artifact.checksum != original_checksum
        assert updated_artifact.metadata["updated_reason"] == "new_content"
    
    def test_update_nonexistent_artifact(self, artifact_manager):
        """Test updating a nonexistent artifact."""
        result = artifact_manager.update_artifact(
            artifact_id="nonexistent-id",
            metadata={"test": "data"}
        )
        assert result is False
    
    def test_update_artifact_with_nonexistent_file(self, artifact_manager, test_file):
        """Test updating artifact with nonexistent new file."""
        operation_id = "test-op-123"
        
        # Create artifact
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log"
        )
        
        # Try to update with nonexistent file
        result = artifact_manager.update_artifact(
            artifact_id=artifact_id,
            file_path="/nonexistent/file.txt"
        )
        
        assert result is False
    
    def test_create_artifact_has_modified_at_set_to_created_at(self, artifact_manager, test_file):
        """Test that newly created artifacts have modified_at set to created_at."""
        operation_id = "test-op-123"
        
        artifact_id = artifact_manager.create_artifact(
            source_id="test-source",
            operation_id=operation_id,
            file_path=test_file,
            name="Test Log",
            artifact_type="log"
        )
        
        artifact = artifact_manager.get_artifact(artifact_id)
        assert artifact.modified_at == artifact.created_at


class TestGlobalArtifactManager:
    """Test cases for the global artifact manager."""
    
    def test_get_artifact_manager_singleton(self):
        """Test that get_artifact_manager returns the same instance."""
        am1 = get_artifact_manager()
        am2 = get_artifact_manager()
        
        assert am1 is am2
    
    def test_get_artifact_manager_type(self):
        """Test that get_artifact_manager returns ArtifactManager instance."""
        am = get_artifact_manager()
        assert isinstance(am, ArtifactManager)


if __name__ == "__main__":
    pytest.main([__file__])