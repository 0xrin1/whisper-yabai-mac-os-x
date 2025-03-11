"""Test that pre-commit is properly configured."""
import os
import unittest


class TestPreCommit(unittest.TestCase):
    """Ensure pre-commit is properly configured."""

    def test_pre_commit_config_exists(self):
        """Verify pre-commit config file exists in repo root."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        pre_commit_path = os.path.join(repo_root, ".pre-commit-config.yaml")
        self.assertTrue(
            os.path.exists(pre_commit_path), "Pre-commit config file not found"
        )


if __name__ == "__main__":
    unittest.main()
