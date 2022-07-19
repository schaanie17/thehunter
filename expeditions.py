import datetime

import pandas    as pd
import streamlit as st


def render(session):
    L = {}
    for eid,e in session.myExpeditions.items():
        reserveName = session.reserves[e["reserve"]]["name"]
        kills       = len(e['kills'])
        startTime   = datetime.datetime.fromtimestamp(e["start_ts"]) 
        endTime     = datetime.datetime.fromtimestamp(e["end_ts"]) 
        L[eid] = (reserveName,kills,startTime,endTime)       

    df = pd.DataFrame.from_dict(L,orient="index",columns=["Reserve","Kills","Start","End"])

    st.dataframe(df)