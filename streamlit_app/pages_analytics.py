"""
Phase 4: Analytics dashboard — turns raw meeting history into a few
at-a-glance stats and charts using data you're already collecting.

Uses Streamlit's native chart functions, so no extra plotting library
is needed.
"""

import streamlit as st
import pandas as pd

import api_client as api
from style import section_label, stat_chip


def render():

    # --------------------------------------------------
    # Load Analytics
    # --------------------------------------------------

    try:
        data = api.get_analytics()

    except Exception as e:
        st.error(f"Could not load analytics: {e}")
        return


    # --------------------------------------------------
    # No Meetings
    # --------------------------------------------------

    if data["total_meetings"] == 0:
        st.info(
            "No meetings yet — process one to see analytics here."
        )
        return


    # --------------------------------------------------
    # Overview
    # --------------------------------------------------

    with st.container(border=True):

        section_label("Overview")

        c1, c2, c3 = st.columns(3)

        # Total Meetings
        with c1:
            stat_chip(
                data["total_meetings"],
                "Total meetings"
            )

        # Total Action Items
        with c2:
            stat_chip(
                data["total_action_items"],
                "Action items"
            )

        # Completed Action Items
        with c3:

            pct = (
                round(
                    100
                    * data["completed_action_items"]
                    / data["total_action_items"]
                )
                if data["total_action_items"]
                else 0
            )

            stat_chip(
                f"{pct}%",
                "Items completed"
            )


    st.write("")


    # --------------------------------------------------
    # Charts
    # --------------------------------------------------

    col1, col2 = st.columns(2)


    # --------------------------------------------------
    # Meetings by Type
    # --------------------------------------------------

    with col1:

        with st.container(border=True):

            section_label("Meetings by type")

            if data["by_type"]:

                df = pd.DataFrame(
                    {
                        "Type": list(
                            data["by_type"].keys()
                        ),
                        "Count": list(
                            data["by_type"].values()
                        ),
                    }
                ).set_index("Type")

                st.bar_chart(
                    df,
                    use_container_width=True
                )

            else:

                st.caption(
                    "No completed meetings yet."
                )


    # --------------------------------------------------
    # Meeting Status
    # --------------------------------------------------

    with col2:

        with st.container(border=True):

            section_label("Meeting status")

            if data["by_status"]:

                df = pd.DataFrame(
                    {
                        "Status": list(
                            data["by_status"].keys()
                        ),
                        "Count": list(
                            data["by_status"].values()
                        ),
                    }
                ).set_index("Status")

                st.bar_chart(
                    df,
                    use_container_width=True
                )

            else:

                st.caption(
                    "No meeting status data yet."
                )


    st.write("")


    # --------------------------------------------------
    # Meetings Per Week
    # --------------------------------------------------

    with st.container(border=True):

        section_label(
            "Meetings per week (last 8 weeks)"
        )

        if data["per_week"]:

            df = pd.DataFrame(
                data["per_week"]
            ).set_index("week")

            st.line_chart(
                df,
                use_container_width=True
            )

        else:

            st.caption(
                "Not enough history yet."
            )