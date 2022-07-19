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


st.set_page_config(layout="wide")

with st.sidebar:
    st.title("The Hunter Mission Dashboard")

    st.text_input('Username', '', key='username')
    st.text_input('Password', '', key='password', type='password')

    if 'session' not in st.session_state:
        session = hunter_session.Session(mongo_url=st.secrets["MONGO_URL"])
        st.session_state['session'] = session
    else:
        session = st.session_state['session']

    def connect_cb():
        session.connect(
            st.session_state.username,
            st.session_state.password,
        )
    
    st.button('Connect', on_click=connect_cb)

if session.token_data is None:
    st.sidebar.info("Not connected")
else:
    st.sidebar.success(f":white_check_mark: Connected")

    st.sidebar.selectbox(
        label       = "Select App:", 
        options     = ["Missions","Expeditions","Scores"],
        key         = 'app_select'
    )

    session.load_app()
    session.load_me()
    session.load_missions()
    session.load_expeditions(session.me["id"])
    
    if   st.session_state.app_select == "Missions":
        missions.render(session)        

    elif st.session_state.app_select == "Scores":
        kills.render(session)
        
    elif st.session_state.app_select == "Expeditions":
        expeditions.render(session)