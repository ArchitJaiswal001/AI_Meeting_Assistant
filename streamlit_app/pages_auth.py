"""
Phase 3: Login / Register screen, shown before the user can access
the rest of the app.

On success, stores the JWT token + email in Streamlit session state.
Every backend request is handled through api_client.py.
"""

import streamlit as st

import api_client as api
from style import section_label


def render():

    # --------------------------------------------------
    # Header
    # --------------------------------------------------

    st.markdown(
        """
        <div style="
            text-align:center;
            margin-top:3rem;
            margin-bottom:1.5rem;
        ">
            <span style="font-size:40px;">🗓️</span>

            <div style="
                font-size:24px;
                font-weight:700;
                color:#0B1A3D;
            ">
                AI Meeting Assistant
            </div>

            <div style="
                font-size:13px;
                color:#5B6B8C;
            ">
                Sign in to continue
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # --------------------------------------------------
    # Login / Register Container
    # --------------------------------------------------

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        with st.container(border=True):

            tab1, tab2 = st.tabs(
                ["Log in", "Create account"]
            )


            # ==================================================
            # LOGIN
            # ==================================================

            with tab1:

                section_label("Log in")

                email = st.text_input(
                    "Email",
                    key="login_email"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password"
                )


                if st.button(
                    "Log in",
                    type="primary",
                    use_container_width=True
                ):

                    if not email or not password:

                        st.warning(
                            "Enter both email and password"
                        )

                    else:

                        try:

                            result = api.login(
                                email,
                                password
                            )

                            # Store JWT token
                            st.session_state.auth_token = (
                                result["access_token"]
                            )

                            # Store email
                            st.session_state.user_email = (
                                result["email"]
                            )

                            # Redirect to main application
                            st.rerun()

                        except Exception as e:

                            st.error(str(e))


            # ==================================================
            # REGISTER
            # ==================================================

            with tab2:

                section_label(
                    "Create account"
                )

                new_email = st.text_input(
                    "Email",
                    key="register_email"
                )

                new_password = st.text_input(
                    "Password",
                    type="password",
                    key="register_password",
                    help="At least 8 characters"
                )

                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    key="register_confirm"
                )


                if st.button(
                    "Create account",
                    type="primary",
                    use_container_width=True
                ):

                    if not new_email or not new_password:

                        st.warning(
                            "Enter both email and password"
                        )

                    elif new_password != confirm_password:

                        st.warning(
                            "Passwords don't match"
                        )

                    else:

                        try:

                            result = api.register(
                                new_email,
                                new_password
                            )

                            # Store JWT token
                            st.session_state.auth_token = (
                                result["access_token"]
                            )

                            # Store email
                            st.session_state.user_email = (
                                result["email"]
                            )

                            # Redirect to main application
                            st.rerun()

                        except Exception as e:

                            st.error(str(e))