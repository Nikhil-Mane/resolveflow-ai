"""Public exports for the FastAPI interface.

The small path bootstrap also supports running ``uvicorn api:app`` while the
current directory is ``support_agent``. From the project root, the preferred
command remains ``uvicorn support_agent.api:app``.
"""

import sys
from pathlib import Path


if __package__ == "api":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from support_agent.api.app import app, conversation_key, create_app


__all__ = ["app", "conversation_key", "create_app"]
