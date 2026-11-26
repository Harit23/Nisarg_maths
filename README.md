# Manufacturing Quality Control with Control Charts (Project 9)

A tool that watches a production line: it measures 5 bolts at a time, learns control limits from good data, and raises an alarm when the machine drifts. It uses X-bar and R charts with run rules, plus CUSUM for small drifts.

**Live website:** https://harit23.github.io/Nisarg_maths/ (the 6-step walkthrough and live monitor, works in any browser)

## Results

| | Theory | Our simulation |
|---|---|---|
| False-alarm rate of 3-sigma limits | 0.27% | 0.27% (2,000,000 points) |
| ARL with no drift, X-bar | 370 | 366 |

Subgroups until an alarm (average of 5,000 runs):

| Drift | X-bar | CUSUM |
|---|---|---|
| 0.5 SE (small) | 155.9 | 39.0 |
| 1 SE | 43.8 | 10.5 |
| 2 SE (big) | 6.6 | 4.0 |

CUSUM catches a small drift about **4x faster** than the X-bar chart.

## Files

| File | What it does |
|---|---|
| `spc.py` | Control limits, run rules, CUSUM, ARL, SQLite storage, deque rolling stats. `python spc.py` prints the theory-vs-experiment results. |
| `dashboard.py` | Guided Streamlit dashboard in 6 steps. `streamlit run dashboard.py` |
| `docs/index.html` | The same walkthrough as a static website (GitHub Pages). |
| `reports/` | Presentation, viva one-pager and beginner guide. |

## Run

```bash
pip install -r requirements.txt
python spc.py
streamlit run dashboard.py
```
