"""Live SPC dashboard. Run: streamlit run dashboard.py"""
import numpy as np
import matplotlib.pyplot as plt  # type: ignore[reportMissingModuleSource]
import streamlit as st
import spc

st.set_page_config(layout="wide", page_title="Live SPC Dashboard")
st.title("Production Line Monitor: X-bar, R and CUSUM")

ss = st.session_state
if "lim" not in ss:
    ss.rng = np.random.default_rng(42)
    ss.lim = spc.fit_limits(spc.make_subgroups(25, rng=ss.rng))  # Phase I baseline
    ss.data = []
    ss.con = spc.connect()

st.sidebar.header("Controls")
running = st.sidebar.checkbox("Stream running", True)
st.sidebar.slider("Inject mean shift (in sigma)", 0.0, 3.0, 0.0, 0.1, key="shift")
if st.sidebar.button("Reset chart"):
    ss.data = []
lim = ss.lim
st.sidebar.write(f"CL = {lim['cl']:.2f}  UCL = {lim['ucl']:.2f}  LCL = {lim['lcl']:.2f}")
st.sidebar.write(f"R-bar = {lim['rbar']:.2f}  R-UCL = {lim['r_ucl']:.2f}")


@st.fragment(run_every=1)
def live():
    if running:  # a new subgroup arrives every second
        row = spc.make_subgroups(1, shift=ss.shift, rng=ss.rng)[0]
        ss.data.append(row)
        spc.save(ss.con, row)
    if len(ss.data) < 2:
        return
    X = np.array(ss.data)
    xb, r = X.mean(axis=1), np.ptp(X, axis=1)
    flags = spc.check_rules(xb, lim)
    cp, cm, alarm = spc.cusum(xb, lim)
    W = 100
    idx = np.arange(len(xb))[-W:]
    bad = np.array([bool(f) for f in flags])

    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ax[0].plot(idx, xb[-W:], "o-", ms=3)
    ax[0].scatter(idx[bad[-W:]], xb[-W:][bad[-W:]], c="red", zorder=3)
    for y, ls in ((lim["ucl"], "--"), (lim["cl"], "-"), (lim["lcl"], "--")):
        ax[0].axhline(y, color="k", ls=ls, lw=1)
    ax[0].set_ylabel("X-bar")
    ax[1].plot(idx, r[-W:], "o-", ms=3, color="tab:green")
    ax[1].axhline(lim["r_ucl"], color="k", ls="--")
    ax[1].axhline(lim["rbar"], color="k")
    ax[1].set_ylabel("Range")
    ax[2].plot(idx, cp[-W:], label="C+")
    ax[2].plot(idx, -cm[-W:], label="C-")
    ax[2].axhline(5, color="r", ls="--")
    ax[2].axhline(-5, color="r", ls="--")
    ax[2].set_ylabel("CUSUM")
    ax[2].legend(loc="upper left")
    ax[2].set_xlabel("Subgroup number")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    c1, c2, c3 = st.columns(3)
    c1.metric("Subgroups seen", len(xb))
    c2.metric("X-bar rule alarms", int(bad.sum()))
    c3.metric("CUSUM alarms", int(alarm.sum()))
    if bad[-1] or alarm[-1]:
        st.error(f"OUT OF CONTROL: {', '.join(flags[-1]) or 'CUSUM'}")
    else:
        st.success("Process in control")


live()
