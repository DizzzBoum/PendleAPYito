import streamlit as st


from ui.market_scan import render_market_scan

from ui.actions import render_actions
from ui.portfolio import render_portfolio
from ui.orders import render_orders
from ui._theme import apply_theme
from ui.cockpit_bar import render_cockpit_bar


st.set_page_config(page_title="PendleAPYito", layout="wide")

apply_theme()

st.title("PendleAPYito")
st.caption("Cockpit manuel Pendle — rapide, lisible, utile")

render_cockpit_bar()

tab1, tab2, tab3, tab4 = st.tabs([
    "Market Scan",
    "Portfolio",
    "Orders",
    "Actions",
])

with tab1:
    render_market_scan()

with tab2:
    render_portfolio()

with tab3:
    render_orders()

with tab4:
    render_actions()
