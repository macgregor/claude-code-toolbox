import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.errors import BlockingError, NonBlockingError


class TestLifecycleErrors(unittest.TestCase):
    def test_blocking_error_is_exception(self):
        """BlockingError should be an Exception subclass."""
        err = BlockingError("test message")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "test message")

    def test_nonblocking_error_is_exception(self):
        """NonBlockingError should be an Exception subclass."""
        err = NonBlockingError("test message")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "test message")

    def test_blocking_error_can_be_raised(self):
        """BlockingError should be raisable."""
        with self.assertRaises(BlockingError) as ctx:
            raise BlockingError("validation failed")
        self.assertEqual(str(ctx.exception), "validation failed")

    def test_nonblocking_error_can_be_raised(self):
        """NonBlockingError should be raisable."""
        with self.assertRaises(NonBlockingError) as ctx:
            raise NonBlockingError("io failed")
        self.assertEqual(str(ctx.exception), "io failed")


if __name__ == "__main__":
    unittest.main()
