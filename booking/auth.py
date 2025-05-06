# ----- booking/auth.py -----
import streamlit as st

ADMINS = {"ahmedsabri85@gmail.com"}   # put your own e‑mail here

def login():
    email = st.text_input("Email").strip().lower()
    if st.button("Sign in"):
        st.session_state["user"] = email
        st.session_state["is_admin"] = email in ADMINS
