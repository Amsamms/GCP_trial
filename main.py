"""
main.py  –  Streamlit booking app with ChatGPT function calling
────────────────────────────────────────────────────────────────
Requirements (add to requirements.txt):
    streamlit
    google-cloud-firestore
    google-cloud-secret-manager
    openai>=1.25
"""

import os, json, streamlit as st, openai, google.auth
from google.cloud import secretmanager

# local helper modules you created earlier
from booking.db import reserve_slot, db
from booking.auth import login
from booking.llm_funcs import openai_tools, FUNCTIONS


# ───────────────────────────────────────────────────────────────
# 1.  Retrieve the OpenAI secret key from Google Secret Manager
# ───────────────────────────────────────────────────────────────
def get_openai_key() -> str:
    _, project_id = google.auth.default()
    project_id = project_id or os.getenv("GCP_PROJECT")
    if not project_id:
        raise RuntimeError("GCP project ID not found")
    sm = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/openai-key/versions/latest"
    return sm.access_secret_version(name=name).payload.data.decode()


openai.api_key = get_openai_key()


# ───────────────────────────────────────────────────────────────
# 2.  Very small login pane (email + admin flag)
# ───────────────────────────────────────────────────────────────
login()
if "user" not in st.session_state:
    st.stop()                      # wait until user clicks “Sign in”


# ───────────────────────────────────────────────────────────────
# 3.  Classic manual booking widgets
# ───────────────────────────────────────────────────────────────
st.title("📅  Chat‑powered Booking")

if st.session_state["is_admin"]:
    st.subheader("Reserved slots (admin view)")
    for doc in db.collection("reservations").stream():
        st.write(doc.id, "→", doc.to_dict()["user"])
    st.divider()
else:
    date = st.date_input("Pick a date").isoformat()
    time = st.time_input("Pick a time").isoformat(timespec="minutes")
    if st.button("Reserve"):
        try:
            reserve_slot(st.session_state["user"], date, time)
            st.success("Booked!")
        except ValueError as e:
            st.error(str(e))


# ───────────────────────────────────────────────────────────────
# 4.  ChatGPT assistant with OpenAI 1.x client & function calling
# ───────────────────────────────────────────────────────────────
st.header("💬 Assistant")

# initialise message history once per session
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful booking assistant. "
                "Regular users can book a slot. "
                "Admins can also list all reservations."
            ),
        }
    ]


def _append_chat(msg_obj):
    """
    Convert ChatCompletionMessage → plain dict and store in
    st.session_state.messages (needed because Streamlit JSON‑serialises)
    """
    item = {"role": msg_obj.role}
    if msg_obj.content:
        item["content"] = msg_obj.content
    if msg_obj.tool_calls:
        item["tool_calls"] = [tc.model_dump() for tc in msg_obj.tool_calls]
    st.session_state.messages.append(item)
    return item


# render past conversation
for m in st.session_state.messages[1:]:
    st.chat_message(m["role"]).write(m.get("content", str(m.get("tool_calls", ""))))


# user prompt
if prompt := st.chat_input("Ask me anything about reservations…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # ── 1️⃣  first call to GPT – may include tool_calls
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages,
        tools=openai_tools,
        tool_choice="auto",
    )
    assistant_msg = resp.choices[0].message
    _append_chat(assistant_msg)

    # ── 2️⃣  execute each requested tool, if any
    if assistant_msg.tool_calls:
        for call in assistant_msg.tool_calls:
            fn_name = call.function.name
            args = json.loads(call.function.arguments or "{}")

            # inject caller email so model can’t spoof another user
            if fn_name == "reserve_slot":
                args["user_email"] = st.session_state["user"]

            # admin gate
            if fn_name == "list_reservations" and not st.session_state["is_admin"]:
                result = "❌ You are not authorised to view all reservations."
            else:
                result = FUNCTIONS[fn_name](**args) or "✅ Done"

            # build tool‑response message **and keep it in history**
            tool_response = {
                "role": "tool",
                "tool_call_id": call.id,
                "name": fn_name,
                "content": json.dumps(result),
            }
            st.session_state.messages.append(tool_response)

            # ── 3️⃣  second GPT call so it can craft a natural reply
            follow_up = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
            )
            final_msg = follow_up.choices[0].message
            _append_chat(final_msg)
            st.chat_message("assistant").write(final_msg.content)
    else:
        # simple answer with no tools
        st.chat_message("assistant").write(assistant_msg.content)
