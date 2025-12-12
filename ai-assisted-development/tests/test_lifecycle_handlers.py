import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.handlers import EventHandler
from lifecycle.models import RequestContext, EventData


class TestEventHandler(unittest.TestCase):
    def test_is_abstract(self):
        """EventHandler should be abstract base class."""
        with self.assertRaises(TypeError):
            EventHandler()

    def test_requires_handle_method(self):
        """EventHandler subclass must implement handle()."""
        class IncompleteHandler(EventHandler):
            pass

        with self.assertRaises(TypeError):
            IncompleteHandler()

    def test_concrete_implementation_works(self):
        """EventHandler subclass with handle() should work."""
        class ConcreteHandler(EventHandler):
            def handle(self, context: RequestContext, event: EventData) -> RequestContext:
                return context

        handler = ConcreteHandler()
        ctx = RequestContext(
            session_id="s",
            request_id="r",
            request_dir=Path("/tmp"),
            transcript_path=Path("/tmp/t"),
            agent_types={},
            start_uuid=None
        )
        event = EventData(
            hook_event_name="Test",
            raw_hook_input={}
        )
        result = handler.handle(ctx, event)
        self.assertEqual(result, ctx)


if __name__ == "__main__":
    unittest.main()
