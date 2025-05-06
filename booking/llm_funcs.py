from booking.db import reserve_slot, db

# ---- JSON schemas shown to the model -------------------------------
openai_tools = [
    {
        "type": "function",
        "function": {
            "name": "reserve_slot",
            "description": "Book a date/time if available",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_iso": {"type": "string"},
                    "time_iso": {"type": "string"},
                },
                "required": ["date_iso", "time_iso"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reservations",
            "description": "Return every reserved slot",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ---- Python side ----------------------------------------------------
def list_reservations():
    return {
        doc.id: doc.to_dict()["user"]
        for doc in db.collection("reservations").stream()
    }

FUNCTIONS = {
    "reserve_slot": reserve_slot,
    "list_reservations": list_reservations,
}
