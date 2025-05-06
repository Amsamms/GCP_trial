import streamlit as st
from booking.db import reserve_slot, db
from booking.auth import login
import openai, os, google.cloud.secretmanager

def get_openai_key():
    client = google.cloud.secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.environ['GCP_PROJECT']}/secrets/openai-key/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode()

openai.api_key = get_openai_key()

login()
if "user" not in st.session_state:
    st.stop()

st.title("📅 Chat‑powered Booking")

if st.session_state["is_admin"]:
    st.subheader("Reserved slots")
    docs = db.collection("reservations").stream()
    for d in docs:
        st.write(d.id, "→", d.to_dict()["user"])
else:
    date = st.date_input("Pick a date").isoformat()
    time = st.time_input("Pick a time").isoformat(timespec="minutes")
    if st.button("Reserve"):
        try:
            reserve_slot(st.session_state["user"], date, time)
            st.success("Booked!")
        except ValueError as e:
            st.error(str(e))

