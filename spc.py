"""Core SPC maths: X-bar/R limits, run rules, CUSUM, ARL, SQLite storage.
Run `python spc.py` for the theory-vs-experiment results."""
import sqlite3
from math import erf, sqrt
import numpy as np

# Control-chart constants for subgroup size n = 5
N = 5
A2, D3, D4, D2 = 0.577, 0.0, 2.114, 2.326


def phi(x):
    """Standard normal CDF."""
    return 0.5 * (1 + erf(x / sqrt(2)))


def make_subgroups(k, mu=50.0, sigma=2.0, shift=0.0, rng=None, n=N):
    """k subgroups of n measurements; `shift` is in units of sigma."""
    rng = rng or np.random.default_rng(42)
    return rng.normal(mu + shift * sigma, sigma, (k, n))


def fit_limits(baseline):
    """Phase I: limits from an in-control baseline (rows = subgroups)."""
    xb = baseline.mean(axis=1)
    r = np.ptp(baseline, axis=1)
    cl, rbar = xb.mean(), r.mean()
    return dict(cl=cl, rbar=rbar, ucl=cl + A2 * rbar, lcl=cl - A2 * rbar,
                r_ucl=D4 * rbar, r_lcl=D3 * rbar,
                sigma=rbar / D2, n=baseline.shape[1])


def zscores(xbars, lim):
    """Subgroup means in units of the standard error sigma/sqrt(n) (CLT)."""
    return (np.asarray(xbars) - lim["cl"]) / (lim["sigma"] / sqrt(lim["n"]))


def check_rules(xbars, lim):
    """Per-point list of triggered rules.
    R1: beyond 3 sigma | R2: 2 of 3 beyond 2 sigma (same side) | R3: 8 in a row on one side."""
    z = zscores(xbars, lim)
    flags = [[] for _ in z]
    for i in range(len(z)):
        if abs(z[i]) > 3:
            flags[i].append("R1")
        w = z[max(0, i - 2):i + 1]
        if len(w) == 3 and ((w > 2).sum() >= 2 or (w < -2).sum() >= 2):
            flags[i].append("R2")
        w = z[max(0, i - 7):i + 1]
        if len(w) == 8 and ((w > 0).all() or (w < 0).all()):
            flags[i].append("R3")
    return flags


def cusum(xbars, lim, k=0.5, h=5.0):
    """Tabular CUSUM on standardised means. Returns (C+, C-, alarm_mask)."""
    z = zscores(xbars, lim)
    cp, cm = np.zeros(len(z)), np.zeros(len(z))
    p = m = 0.0
    for i, v in enumerate(z):
        p = max(0.0, p + v - k)
        m = max(0.0, m - v - k)
        cp[i], cm[i] = p, m
    return cp, cm, (cp > h) | (cm > h)


# ---------- ARL and false alarm rate ----------
def run_length(delta, chart, rng, k=0.5, h=5.0, cap=100_000):
    """Samples until first alarm. delta = mean shift in standard-error units."""
    p = m = 0.0
    for t in range(1, cap + 1):
        z = rng.normal(delta, 1.0)
        if chart == "xbar":
            if abs(z) > 3:
                return t
        else:
            p = max(0.0, p + z - k)
            m = max(0.0, m - z - k)
            if p > h or m > h:
                return t
    return cap


def arl(delta, chart, trials=5000, seed=1):
    rng = np.random.default_rng(seed)
    return float(np.mean([run_length(delta, chart, rng) for _ in range(trials)]))


def arl_theory_xbar(delta):
    return 1 / (phi(-3 - delta) + 1 - phi(3 - delta))


from collections import deque


class RollingStats:
    """Sliding-window mean/std using a deque (O(1) update with running sums)."""
    def __init__(self, size=20):
        self.w, self.size, self.s, self.s2 = deque(), size, 0.0, 0.0

    def push(self, x):
        self.w.append(x)
        self.s += x
        self.s2 += x * x
        if len(self.w) > self.size:
            old = self.w.popleft()
            self.s -= old
            self.s2 -= old * old
        n = len(self.w)
        mean = self.s / n
        var = max(0.0, (self.s2 - n * mean * mean) / (n - 1)) if n > 1 else 0.0
        return mean, var ** 0.5


# ---------- SQLite ----------
SCHEMA = """CREATE TABLE IF NOT EXISTS subgroups(
  id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP,
  x1 REAL, x2 REAL, x3 REAL, x4 REAL, x5 REAL, xbar REAL, r REAL);"""


def connect(path="spc.db"):
    con = sqlite3.connect(path, check_same_thread=False)
    con.execute(SCHEMA)
    return con


def save(con, row):
    con.execute("INSERT INTO subgroups(x1,x2,x3,x4,x5,xbar,r) VALUES(?,?,?,?,?,?,?)",
                (*map(float, row), float(np.mean(row)), float(np.ptp(row))))
    con.commit()


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    # 1) False-alarm rate of 3-sigma limits on normal data
    z = rng.normal(size=2_000_000)
    print(f"False-alarm rate: observed {np.mean(abs(z) > 3):.5f} | theory 0.00270")
    # 2) ARL0 and ARL1 (shift of 1 standard error)
    print(f"ARL0 X-bar: observed {arl(0, 'xbar'):.0f} | theory {arl_theory_xbar(0):.0f}")
    print(f"ARL0 CUSUM: observed {arl(0, 'cusum'):.0f} | literature ~465")
    for d in (0.5, 1.0, 2.0):
        print(f"shift {d} SE -> ARL1 X-bar {arl(d, 'xbar'):.1f} "
              f"(theory {arl_theory_xbar(d):.1f}) | CUSUM {arl(d, 'cusum'):.1f}")
