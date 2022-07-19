import streamlit as st


def _printMissionRow(rowClass,m,mgTitle,mTitle,tTitles):
    out  = f"<tr class='{rowClass}'><td>{mTitle}</td><td>{mgTitle}</td><td style='text-align:left'>"
    out += f"<ul class='{'singleExp' if m['singleExpedition'] else 'multiExp'}'>"
    for title,obj in zip(tTitles,m["objectives"]):
        out += f"<li class='{'completed' if obj['id'] in m['completedObjectives'] else 'incomplete'}'>{title}</li>"
    out += "</ul></td></tr>"
    return out

def render(session):
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

    html_tab = """
    <div id="scoped-content">
        <style type="text/css" scoped>
            tr.goodRow:nth-child(2n+0) {
                background-color: #ded
            } 
            tr.goodRow:nth-child(2n+1) {
                background-color: #cec
            } 
            tr.badRow:nth-child(2n+0) {
                background-color: #fee
            } 
            tr.badRow:nth-child(2n+1) {
                background-color: #fdd
            } 
            ul.multiExp {
                list-style: circle
            }
            ul.singleExp {
                list-style: disc
            }
            li.completed {
                text-decoration-line: line-through;
            }
            li.incomplete {
            }
        </style>
        <table>
    """

    for result in goodMissions:
        html_tab += _printMissionRow("goodRow",*result)

    for result in badMissions:
        html_tab += _printMissionRow("badRow",*result)

    html_tab += "</table></div>"     

    st.markdown(html_tab,unsafe_allow_html=True)
