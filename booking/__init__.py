"""
Package initialiser for the `booking` helper package.

Currently it just exposes the Firestore client (`db`) and the
`reserve_slot` function so other modules—or Streamlit itself—can do:

    from booking import db, reserve_slot
"""
from .db import db, reserve_slot   # re‑export for convenience
__all__ = ["db", "reserve_slot"]
