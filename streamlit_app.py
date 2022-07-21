import json
import re
import requests
import urllib
import time
import datetime

import pandas as pd

import streamlit as st

import hunter_session

import missions
import expeditions
import kills


st.set_page_config(page_title="The Hunter Dashboard",layout="wide")


if 'session' not in st.session_state:
    session = hunter_session.Session(mongo_url=st.secrets["MONGO_URL"])
    st.session_state['session'] = session
else:
    session = st.session_state['session']


with st.sidebar:
    st.title("The Hunter Dashboard")

    with st.form("login"):

        username    = st.text_input('Username')
        password    = st.text_input('Password', type='password')
        submit      = st.form_submit_button("Connect")
        placeholder = st.empty()

        if submit:
            try:
                session.connect(username,password)
            except RuntimeError as err:
                error = st.error(err)

connected = session.token_data is not None
if not connected:
    placeholder.info("Not connected")
else:
    placeholder.success(f":white_check_mark: Connected")

    st.sidebar.selectbox(
        label       = "Select App:", 
        options     = ["Missions","Expeditions","Scores"],
        key         = 'app_select'
    )

    session.load_app()
    session.load_me()
    
    if   st.session_state.app_select == "Missions":
        session.load_missions()
        missions.render(session)        

    else:
        session.load_expeditions(session.me["id"])
        
        if st.session_state.app_select == "Scores":
            kills.render(session)
        
        elif st.session_state.app_select == "Expeditions":
            expeditions.render(session)