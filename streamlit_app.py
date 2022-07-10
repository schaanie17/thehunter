import json
import re
import requests
import urllib
import time
import datetime

import pandas as pd

import streamlit as st

import hunter_session

st.set_page_config(layout="wide")
st.title("The Hunter Mission Dashboard")

st.text_input('Username', '', key='username')
st.text_input('Password', '', key='password', type='password')

if 'session' not in st.session_state:
    session = hunter_session.Session()
    st.session_state['session'] = session
else:
    session = st.session_state['session']

def connect_cb():
    session.connect(
        st.session_state.username,
        st.session_state.password,
    )
    session.load_app()

st.button('Connect', on_click=connect_cb)

if session.token_data is None:
    st.info("Not connected")
else:
    st.success(f":white_check_mark: Connected")
    session.load_me()
    session.load_missions()
    session.load_expeditions()
    
    # ---------------------------------------------------------
    with st.expander("Missions"):
        st.selectbox(
            label       = 'Select Reserve:',
            options     = session.reserves.keys(),
            format_func = lambda id: session.reserves[id]["name"],
            key         = 'reserve_id'
        )

        reserve_id = st.session_state.reserve_id

        #species = session.reserves[reserve_id]["species"]
        #cols = st.columns([1]*len(species) + [9])
        #for col,sid in zip(cols,species):
        #    with col:
        #        st.button(session.species[sid]["name"])

        session.collectBadKeywords(reserve_id)
        goodMissions,badMissions = session.filterMissions()
        html_tab = session.printMissionTable(goodMissions, badMissions)

        #    t = (mTitle,mgTitle)
        #out  = f"<tr class='{rowClass}'><td>{mTitle}</td><td>{mgTitle}</td><td style='text-align:left'>"
        #out += f"<ul class='{'singleExp' if m['singleExpedition'] else 'multiExp'}'>"
        #for title,obj in zip(tTitles,m["objectives"]):
        #    out += f"<li class='{'completed' if obj['id'] in m['completedObjectives'] else 'incomplete'}'>{title}</li>"
        #out += "</ul></td></tr>"
        #return out

        #L = {}    
        #for result in goodMissions:
        #    out += self._printMissionRow("goodRow",*result)

        #for result in badMissions:
        #    out += self._printMissionRow("badRow",*result)       

        st.markdown(html_tab,unsafe_allow_html=True)

    # ---------------------------------------------------------
    with st.expander("Scores"):
        st.selectbox(
            label       = 'Select Species:',
            options     = session.species.keys(),
            format_func = lambda id: session.species[id]["name"],
            key         = 'species_id'
        )

        species_id = st.session_state.species_id

        if species_id not in session.speciesKills:
            st.error(f"No {session.species[species_id]['name']} kills")
        
        else:
            L = {}
            for k in session.speciesKills[species_id]:
                kid = k["id"]
                e           = session.myExpeditions[k["expeditionId"]]
                reserveName = session.reserves[e["reserve"]]["name"]
                startTime   = datetime.datetime.fromtimestamp(e["start_ts"]) 
                endTime     = datetime.datetime.fromtimestamp(e["end_ts"]) 
                numHits     = len(k["hits"])
                distance    = min(h["distance"] for h in k["hits"])
                gender      = "M" if k["gender"] == 0 else "W"
                score       = k["kill"]["score"]

                L[kid] = (reserveName,score,gender,numHits,distance,startTime,endTime)

            df = pd.DataFrame.from_dict(L,orient="index",columns=["Reserve","Score","Gender","#Hits","Distance","Start","End"])
            st.dataframe(df)
        
    # ---------------------------------------------------------
    with st.expander("Expeditions"):
        L = {}
        for eid,e in session.myExpeditions.items():
            reserveName = session.reserves[e["reserve"]]["name"]
            kills       = e['kills']
            startTime   = datetime.datetime.fromtimestamp(e["start_ts"]) 
            endTime     = datetime.datetime.fromtimestamp(e["end_ts"]) 
            L[eid] = (reserveName,kills,startTime,endTime)       

        df = pd.DataFrame.from_dict(L,orient="index",columns=["Reserve","Kills","Start","End"])

        st.dataframe(df)