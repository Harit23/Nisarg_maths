"""Guided SPC dashboard. Run:  streamlit run dashboard.py
Walks through the project step by step (one step per presenter), then the live monitor."""
import numpy as np
import matplotlib.pyplot as plt  # type: ignore[reportMissingModuleSource]
import streamlit as st
import spc

st.set_page_config(layout="wide", page_title="Bolt Factory Quality Monitor")

INK, OK, BAD, ACC, GREY = "#22272B", "#2E8B57", "#D1495B", "#E8871E", "#8A9299"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GREY, "font.size": 10})

ss = st.session_state
if "lim" not in ss:
    ss.rng = np.random.default_rng(42)
    ss.baseline = spc.make_subgroups(25, rng=ss.rng)       # Phase I: 25 good subgroups
    ss.lim = spc.fit_limits(ss.baseline)
    ss.data = []
    ss.con = spc.connect()
lim = ss.lim


def say(text):
    """Green box: what to say to sir."""
    st.success("**Say this:** " + text)


def limits(ax, lo=True):
    ax.axhline(lim["ucl"], color=BAD, ls="--", lw=1)
    ax.axhline(lim["cl"], color=INK, lw=1)
    if lo:
        ax.axhline(lim["lcl"], color=BAD, ls="--", lw=1)
    x1 = ax.get_xlim()[1]
    ax.text(x1, lim["ucl"], " UCL", va="center", color=BAD, fontsize=9)
    ax.text(x1, lim["cl"], " CL", va="center", color=INK, fontsize=9)
    if lo:
        ax.text(x1, lim["lcl"], " LCL", va="center", color=BAD, fontsize=9)


@st.cache_data
def demo(shift=1.0):
    """30 normal subgroups, then 40 with the machine shifted by `shift` sigma."""
    r = np.random.default_rng(7)
    return np.vstack([spc.make_subgroups(30, rng=r), spc.make_subgroups(40, shift=shift, rng=r)])


STEPS = ["1. The problem", "2. Good baseline → limits", "3. X-bar & R charts",
         "4. CUSUM for small drifts", "5. Theory vs experiment", "6. Live monitor"]
st.sidebar.title("Bolt factory monitor")
st.sidebar.caption("Project 9 · Control charts. Go through the steps in order.")
step = st.sidebar.radio("Step", STEPS, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown(f"**Control limits (from the baseline)**  \n"
                    f"CL = {lim['cl']:.2f} mm  \nUCL = {lim['ucl']:.2f} mm  \nLCL = {lim['lcl']:.2f} mm  \n"
                    f"R-bar = {lim['rbar']:.2f} mm · R-UCL = {lim['r_ucl']:.2f} mm")

# ---------------------------------------------------------------- 1
if step == STEPS[0]:
    st.title("Is the bolt machine still making good bolts?")
    st.markdown("""
A factory makes metal bolts. Each bolt should be **50 mm** wide.
Machines slowly drift (the tool wears out, the temperature changes). If nobody notices, the factory makes thousands of bad bolts.

**Our tool:** every few minutes, a worker measures **5 bolts** (one *subgroup*).
The tool stores them in a database, compares them with what "normal" looks like, and raises an **alarm** the moment something changes.
""")
    c = st.columns(5)
    for i, (col, (t, d)) in enumerate(zip(c, [("Measure", "5 bolts at a time"), ("Store", "SQLite with a timestamp"),
                                ("Set limits", "from 25 good subgroups"), ("Check", "X-bar, R and CUSUM"),
                                ("Alarm", "red point + message")])):
        col.markdown(f"**{i + 1}. {t}**  \n{d}")
    row = ss.baseline[0]
    st.markdown("**One subgroup looks like this:**")
    st.table({"Bolt": [1, 2, 3, 4, 5], "Width (mm)": [f"{v:.2f}" for v in row]})
    st.markdown(f"Average (**X-bar**) = **{row.mean():.2f} mm** · Range (**R**, largest − smallest) = **{np.ptp(row):.2f} mm**")
    say("We built a tool that watches a production line. It measures 5 bolts at a time and warns "
        "the factory as soon as the machine starts drifting, before bad bolts are made.")

# ---------------------------------------------------------------- 2
elif step == STEPS[1]:
    st.title("Step 2: learn what 'normal' looks like")
    st.markdown("First we run the machine when we **know it is fine** and take **25 subgroups**. "
                "From them we calculate three lines: the centre line and the upper and lower control limits.")
    xb = ss.baseline.mean(axis=1)
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(range(1, 26), xb, "o-", color=INK, ms=4)
    limits(ax)
    ax.set_xlabel("Baseline subgroup"); ax.set_ylabel("Average width (mm)")
    st.pyplot(fig); plt.close(fig)
    c1, c2, c3 = st.columns(3)
    c1.metric("Centre line (CL)", f"{lim['cl']:.2f} mm")
    c2.metric("Upper limit (UCL)", f"{lim['ucl']:.2f} mm")
    c3.metric("Lower limit (LCL)", f"{lim['lcl']:.2f} mm")
    st.markdown("**How:** CL = average of the 25 averages · R-bar = average range = "
                f"{lim['rbar']:.2f} mm · UCL/LCL = CL ± 0.577 × R-bar. "
                "(0.577 is a fixed constant for subgroups of 5, from the standard control-chart table.)")
    st.subheader("Why the average of 5 bolts? (Central Limit Theorem)")
    r = np.random.default_rng(3)
    single = r.normal(50, 2, 20000)
    means = r.normal(50, 2, (20000, 5)).mean(axis=1)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    ax.hist(single, 80, alpha=.5, color=GREY, label="one bolt")
    ax.hist(means, 80, alpha=.7, color=ACC, label="average of 5 bolts")
    ax.set_xlabel("Width (mm)"); ax.legend(frameon=False); ax.set_yticks([])
    st.pyplot(fig); plt.close(fig)
    st.markdown("The average of 5 bolts moves much less than a single bolt (spread ÷ √5). "
                "It also forms a **bell curve**, so 99.73% of normal averages fall within **3 sigma** of the centre. "
                "That is why the limits are at ±3 sigma: only **0.27%** of normal points cross them by luck.")
    say("We first collected 25 good subgroups and computed the centre line and the 3-sigma limits. "
        "Because we chart averages of 5, the Central Limit Theorem makes them bell-shaped, "
        "so a point outside the limits is very unlikely unless something really changed.")

# ---------------------------------------------------------------- 3
elif step == STEPS[2]:
    st.title("Step 3: watch the average and the spread")
    shift = st.slider("Make the machine drift after subgroup 30 by (sigma)", 0.0, 2.0, 1.0, 0.25)
    X = demo(shift)
    xb, r = X.mean(axis=1), np.ptp(X, axis=1)
    flags = spc.check_rules(xb, lim)
    bad = np.array([bool(f) for f in flags])
    idx = np.arange(1, len(xb) + 1)
    fig, ax = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    ax[0].axvspan(30.5, len(xb) + .5, color=ACC, alpha=.08)
    ax[0].plot(idx, xb, "o-", color=INK, ms=3)
    ax[0].scatter(idx[bad], xb[bad], color=BAD, zorder=3, s=30)
    limits(ax[0]); ax[0].set_ylabel("X-bar (mm)")
    ax[0].text(31, ax[0].get_ylim()[0], "machine drifted →", va="bottom", color=ACC)
    ax[1].plot(idx, r, "o-", color=OK, ms=3)
    ax[1].axhline(lim["r_ucl"], color=BAD, ls="--", lw=1); ax[1].axhline(lim["rbar"], color=INK, lw=1)
    ax[1].set_ylabel("Range R (mm)"); ax[1].set_xlabel("Subgroup")
    st.pyplot(fig); plt.close(fig)
    first = next((i + 1 for i in range(30, len(xb)) if bad[i]), None)
    st.info(f"False alarms in the 30 normal subgroups: **{int(bad[:30].sum())}** · "
            f"First alarm after the drift: **{'subgroup ' + str(first) if first else 'none'}**")
    st.markdown("""
- **X-bar chart** (top) watches the **average**: has the machine shifted?
- **R chart** (bottom) watches the **spread**: has the machine become shaky?
- A point turns **red** when one of the **run rules** fires:
    - **R1:** one point outside the 3-sigma limits.
    - **R2:** 2 of the last 3 points beyond 2 sigma on the same side.
    - **R3:** 8 points in a row on the same side of the centre line.

R2 and R3 can turn a point red even when it is **inside** the limits: they catch patterns, not just single extreme points.
""")
    say("The X-bar chart checks if the average moved; the R chart checks if the spread grew. "
        "Run rules catch patterns, like 8 points in a row above the centre, which is why some red points are inside the limits.")

# ---------------------------------------------------------------- 4
elif step == STEPS[3]:
    st.title("Step 4: CUSUM catches small drifts")
    shift = st.slider("Small drift after subgroup 30 (sigma)", 0.0, 1.0, 0.3, 0.1)
    X = demo(shift)
    xb = X.mean(axis=1)
    cp, cm, alarm = spc.cusum(xb, lim)
    flags = spc.check_rules(xb, lim)
    r1 = np.array(["R1" in f for f in flags])
    idx = np.arange(1, len(xb) + 1)
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axvspan(30.5, len(xb) + .5, color=ACC, alpha=.08)
    ax.plot(idx, cp, color=ACC, label="C+ (running total upwards)")
    ax.plot(idx, -cm, color=GREY, label="C− (running total downwards)")
    ax.axhline(5, color=BAD, ls="--"); ax.axhline(-5, color=BAD, ls="--")
    ax.set_ylabel("CUSUM"); ax.set_xlabel("Subgroup"); ax.legend(frameon=False, loc="upper left")
    st.pyplot(fig); plt.close(fig)
    fc = next((i + 1 for i in range(30, len(xb)) if alarm[i]), None)
    fx = next((i + 1 for i in range(30, len(xb)) if r1[i]), None)
    c1, c2 = st.columns(2)
    c1.metric("CUSUM first alarm", f"subgroup {fc}" if fc else "not caught in 40 subgroups")
    c2.metric("3-sigma rule first alarm", f"subgroup {fx}" if fx else "not caught in 40 subgroups")
    st.markdown("""
**Idea:** instead of judging each point alone, CUSUM keeps a **running total** of how far each average is above (or below) normal.
Tiny shifts add up, and when the total passes **5** we raise the alarm.

Each step it adds the new deviation, minus a small allowance **k = 0.5** so normal noise doesn't build up, and never goes below 0.

*Like a bank balance:* one small withdrawal isn't worrying, but if it keeps dropping a little every day, you notice.
""")
    say("The X-bar chart is good for big jumps but slow for small drifts. CUSUM adds up small deviations over time, "
        "so a small drift is caught much sooner.")

# ---------------------------------------------------------------- 5
elif step == STEPS[4]:
    st.title("Step 5: does theory match the experiment?")
    st.subheader("A. False-alarm rate")
    c1, c2 = st.columns(2)
    c1.metric("Theory (3-sigma limits)", "0.27%")
    c2.metric("Our simulation (2,000,000 points)", "0.27%")
    st.caption("Theory: 0.27% means about 1 false alarm every 370 points. Our simulation matched it exactly.")
    st.subheader("B. Average run length (ARL)")
    st.markdown("**ARL** = how many subgroups go by, on average, before an alarm (5,000 simulated runs each). "
                "With no drift we want it **big** (few false alarms). With a drift we want it **small** (caught fast).")
    shifts = ["0.5 SE", "1 SE", "2 SE"]
    xbar_obs, xbar_th, cus = [155.9, 43.8, 6.6], [155.2, 43.9, 6.3], [39.0, 10.5, 4.0]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x = np.arange(3)
    b1 = ax.bar(x - .2, xbar_obs, .38, color=GREY, label="X-bar chart")
    b2 = ax.bar(x + .2, cus, .38, color=ACC, label="CUSUM")
    ax.bar_label(b1, fmt="%.1f"); ax.bar_label(b2, fmt="%.1f")
    ax.set_xticks(x, [f"drift {s}" for s in shifts]); ax.set_ylabel("subgroups until alarm")
    ax.legend(frameon=False)
    st.pyplot(fig); plt.close(fig)
    st.table({"Drift": ["none (ARL0)"] + shifts,
              "X-bar: simulation": [f"{v:g}" for v in [366, *xbar_obs]],
              "X-bar: theory": [f"{v:g}" for v in [370, *xbar_th]],
              "CUSUM: simulation": [f"{v:g}" for v in [485, *cus]]})
    st.markdown("SE = standard error = sigma ÷ √5, the spread of an average of 5 bolts. "
                "So a drift of 1 sigma in one bolt = about 2.2 SE for the average.")
    say("Theory says 3-sigma limits give 0.27% false alarms, and our simulation gave exactly 0.27%. "
        "The X-bar run lengths match the formula. For a small 0.5 SE drift, CUSUM needed about 39 subgroups "
        "and X-bar about 156, so CUSUM is about 4 times faster.")

# ---------------------------------------------------------------- 6
else:
    st.title("Step 6: live production line")
    st.markdown("A new subgroup of 5 bolts arrives **every second** and is saved in the SQLite database. "
                "Move the slider to make the machine drift and watch the alarms.")
    c1, c2, c3 = st.columns([1, 2, 1])
    running = c1.toggle("Machine running", True)
    c2.slider("Make the machine drift (sigma)", 0.0, 3.0, 0.0, 0.1, key="shift")
    if c3.button("Reset chart"):
        ss.data = []

    @st.fragment(run_every=1)
    def live():
        if running:
            row = spc.make_subgroups(1, shift=ss.shift, rng=ss.rng)[0]
            ss.data.append(row)
            spc.save(ss.con, row)
        if len(ss.data) < 2:
            st.caption("Waiting for data…")
            return
        X = np.array(ss.data)
        xb, r = X.mean(axis=1), np.ptp(X, axis=1)
        flags = spc.check_rules(xb, lim)
        cp, cm, alarm = spc.cusum(xb, lim)
        bad = np.array([bool(f) for f in flags])
        if bad[-1] or alarm[-1]:
            st.error(f"OUT OF CONTROL: stop and check the machine ({', '.join(flags[-1]) or 'CUSUM'})")
        else:
            st.success("In control: the machine is making good bolts")
        W = 60
        idx = np.arange(1, len(xb) + 1)[-W:]
        fig, ax = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
        ax[0].plot(idx, xb[-W:], "o-", color=INK, ms=3)
        ax[0].scatter(idx[bad[-W:]], xb[-W:][bad[-W:]], color=BAD, zorder=3)
        limits(ax[0]); ax[0].set_ylabel("Average (mm)")
        ax[1].plot(idx, r[-W:], "o-", color=OK, ms=3)
        ax[1].axhline(lim["r_ucl"], color=BAD, ls="--", lw=1); ax[1].axhline(lim["rbar"], color=INK, lw=1)
        ax[1].set_ylabel("Range (mm)")
        ax[2].plot(idx, cp[-W:], color=ACC, label="C+"); ax[2].plot(idx, -cm[-W:], color=GREY, label="C−")
        ax[2].axhline(5, color=BAD, ls="--"); ax[2].axhline(-5, color=BAD, ls="--")
        ax[2].set_ylabel("CUSUM"); ax[2].set_xlabel("Subgroup"); ax[2].legend(frameon=False, loc="upper left")
        plt.tight_layout(); st.pyplot(fig); plt.close(fig)
        k1, k2, k3 = st.columns(3)
        k1.metric("Subgroups measured", len(xb))
        k2.metric("X-bar rule alarms", int(bad.sum()))
        k3.metric("CUSUM alarms", int(alarm.sum()))

    live()
    say("This is the live version. Every second a new subgroup is measured and stored. "
        "When I add a drift with the slider, the points go red and the CUSUM line crosses 5: the tool tells the factory to stop and check.")
