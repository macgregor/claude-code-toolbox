#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles all hook events via LifecycleOrchestrator.
"""

import json
import sys

from lifecycle import LifecycleOrchestrator, BlockingError, NonBlockingError


def main():
    """Read hook input and dispatch to orchestrator."""
    try:
        hook_input = json.load(sys.stdin)
        orchestrator = LifecycleOrchestrator()
        orchestrator.process(hook_input)
        sys.exit(0)
    except BlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except NonBlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
