import datetime

import streamlit as st
import pandas    as pd


def render(session):
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
            e            = session.myExpeditions[k["expeditionId"]]
            reserveName  = session.reserves[e["reserve"]]["name"]
            harvestTime  = datetime.datetime.fromtimestamp(k["kill"]["confirmTs"]) 
            harvestValue = f"{k['kill']['trophy_integrity']:.0f}%"
            woundTime    = str(datetime.timedelta(seconds=k['kill']['wound_time']))
            numHits      = len(k["hits"])
            distance     = ", ".join(f"{h['distance']/1000:.1f}m" for h in k["hits"])
            gender       = "M" if k["gender"] == 0 else "W"
            score        = k["kill"]["score"]

            L[kid] = (reserveName,score,gender,numHits,distance,harvestTime,harvestValue,woundTime)

        df = pd.DataFrame.from_dict(L,orient="index",columns=["Reserve","Score","Gender","#Hits","Distance","Harvest time","Harvest value","Wound time"])
        st.dataframe(df)