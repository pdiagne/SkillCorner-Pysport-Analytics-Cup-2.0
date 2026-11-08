# SkillCorner PySport Analytics Cup 2.0 - Home vs. Away Dashboard
This repository contains my submission to the SkillCorner PySport Analytics Cup 2.0

## What problem did you address?

In sports analytics, evaluating player performance is often done through season-long averages, which can mask critical context. A player’s performance can fluctuate drastically based on whether they are playing at home or away. This project addresses the Home Advantage phenomenon by quantifying the exact performance gaps for individual players.

## What did you build or discover?

I built an interactive Python/Tkinter dashboard that pulls raw tracking and event data from the SkillCorner Open Data repository (A-League 2024/2025) and processes it into per-90 metrics, Expected Possession Value (EPV), and Off-Ball Run (OBR) data, among other metrics.

The dashboard features several key analytical tools:

*Advanced Data Engineering: The pipeline (AC2_2.py) ingests dynamic event data to calculate passing metrics, Expected Possession Value (EPV), and phase-of-play volumes, while also merging match context (Referee, Pitch Dimensions) for further analysis.

*Top/Bottom 5 Facet Grids: When multiple metrics are selected, the dashboard automatically generates a grid. For every metric, it displays the Top 5 positive and Bottom 5 negative Home-Away deltas for the selected team, alongside the same league-wide comparison.

*Overlap Detection: A dedicated text panel identifies "Players in Both," highlighting when a team's worst-performing player on the road is also among the league's worst for that specific metric.

*Clean Spatial Visualizations: We utilized custom side-by-side bar charts with inline text labels and removed bounding boxes to ensure that when comparing players, their names and values are perfectly readable without overlapping.



## Python code to create/view dashboard
Run setup_env.py to install all the relevant libraries.
Run app_1.py to access the dashboard. AC2_2.py is called within app_1.py 

