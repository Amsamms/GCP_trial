"""
Firestore helper layer used by the Streamlit app.

Functions
---------
reserve_slot(user_email, date_iso, time_iso)
    Atomically creates a reservation document whose ID is
    "{YYYY‑MM‑DD}_{HH:MM}" if it doesn't exist.  Raises ValueError
    when the slot is already taken.

Attributes
----------
db : google.cloud.firestore.Client
    Singleton Firestore client built with Application Default
    Credentials (ADC).  Works both locally and on Cloud Run.
"""

from google.cloud import firestore
from google.cloud import exceptions as gexc
from google.cloud.firestore import transactional

# ---- 1️⃣ build the client using ADC (same code runs locally & in Cloud Run)
db = firestore.Client()                 # project ID inferred from ADC
# docs: https://cloud.google.com/python/docs/reference/firestore/latest#using-the-client :contentReference[oaicite:1]{index=1}


# ---- 2️⃣ reserve_slot helper with optimistic concurrency control
def reserve_slot(user_email: str, date_iso: str, time_iso: str) -> None:
    """
    Try to book a slot; fail if someone else snapped it first.

    Parameters
    ----------
    user_email : str
        E‑mail of the person making the booking.
    date_iso : str
        Date in ISO‑8601 format ("2025‑05‑07").
    time_iso : str
        Time in ISO‑8601 ("13:30" or "13:30:00").
    """

    slot_id = f"{date_iso}_{time_iso}"
    doc_ref = db.collection("reservations").document(slot_id)

    # Firestore transactions retry automatically on contention
    @transactional
    def _txn(transaction, ref):
        snapshot = ref.get(transaction=transaction)
        if snapshot.exists:
            # slot already booked — bubble up to Streamlit
            raise ValueError("Slot already taken")
        transaction.set(ref, {"user": user_email})

    try:
        _txn(db.transaction(), doc_ref)
    except gexc.GoogleCloudError as err:          # network / perms
        raise RuntimeError(f"Firestore error: {err}") from err
