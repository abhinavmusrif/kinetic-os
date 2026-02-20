"""Tests for differential RollbackManager and symlink defense."""

from __future__ import annotations

import os
from pathlib import Path

from executor.rollback_manager import RollbackManager


def test_differential_rollback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    file1 = workspace / "file1.txt"
    file2 = workspace / "file2.txt"
    file1.write_text("orig1")
    file2.write_text("orig2")
    
    manager = RollbackManager(workspace)
    # create checkpoint of ONLY file1
    cp_id = manager.create_checkpoint([file1])
    
    # modify both
    file1.write_text("mod1")
    file2.write_text("mod2")
    
    result = manager.rollback(cp_id)
    assert result["success"] is True
    assert result["restored_files"] == 1
    
    # Only file1 should revert
    assert file1.read_text() == "orig1"
    assert file2.read_text() == "mod2"


def test_block_symlink_backup_and_restore(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    target_file = workspace / "target.txt"
    target_file.write_text("target_data")
    
    link_file = workspace / "link.txt"
    try:
        os.symlink(target_file, link_file)
    except OSError:
        # Some windows setups cannot create symlinks without admin
        # In that case, we can mock or just pass.
        return
        
    manager = RollbackManager(workspace)
    cp_id = manager.create_checkpoint([link_file, target_file])
    
    # Check that link.txt wasn't backed up as a symlink
    cp_dir = workspace / ".checkpoints" / cp_id
    backed_link = cp_dir / "link.txt"
    assert not backed_link.exists() # Symlinks should be ignored

    target_file.write_text("modified")
    
    # Even if an attacker somehow created a malicious backup with a symlink pointing outside or inside,
    # the restore should unlink existing symlinks and overwrite them as plain files if the source was a plain file
    
    # Now let's mock a malicious backup
    manager.rollback(cp_id)
    assert target_file.read_text() == "target_data"
