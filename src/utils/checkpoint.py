"""Checkpoint manager for crash recovery.

Saves progress after each major pipeline step so audits can be resumed
after failures without re-running completed work.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(".audit_checkpoints")


def _checkpoint_path(contract_path: str) -> Path:
    name = Path(contract_path).stem
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    return CHECKPOINT_DIR / f"{name}.json"


def save_checkpoint(contract_path: str, mode: str, step: str, data: dict):
    """Save checkpoint after completing a step.

    Failures are logged but never propagate — checkpoint I/O must not
    block or crash the main audit flow.
    """
    try:
        path = _checkpoint_path(contract_path)
        existing = load_checkpoint(contract_path) or {
            "contract_path": contract_path,
            "mode": mode,
            "started_at": datetime.now().isoformat(),
            "last_completed_step": None,
            "steps": {},
        }
        existing["steps"][step] = {
            "completed": True,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        existing["last_completed_step"] = step
        path.write_text(json.dumps(existing, indent=2, default=str))
        logger.debug("Checkpoint saved: %s → %s", contract_path, step)
    except Exception:
        logger.warning("Failed to save checkpoint for step %s", step, exc_info=True)


def load_checkpoint(contract_path: str) -> dict | None:
    """Load checkpoint if it exists."""
    path = _checkpoint_path(contract_path)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            logger.warning("Corrupt checkpoint file: %s", path, exc_info=True)
    return None


def clear_checkpoint(contract_path: str):
    """Remove checkpoint after successful completion."""
    try:
        path = _checkpoint_path(contract_path)
        if path.exists():
            path.unlink()
            logger.debug("Checkpoint cleared: %s", contract_path)
    except Exception:
        logger.warning("Failed to clear checkpoint for %s", contract_path, exc_info=True)


def get_last_step(contract_path: str) -> str | None:
    """Get the last completed step name."""
    cp = load_checkpoint(contract_path)
    return cp["last_completed_step"] if cp else None
