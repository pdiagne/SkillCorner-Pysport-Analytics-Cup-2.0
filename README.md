# SkillCorner PySport Analytics Cup 2.0 - Home vs. Away Dashboard
This repository contains my submission to the SkillCorner PySport Analytics Cup 2.0

## What problem did you address?

In sports analytics, evaluating player performance is often done through season-long averages, which can mask critical context. A player’s performance can fluctuate drastically based on whether they are playing at home or away. This project addresses the Home Advantage phenomenon by quantifying the exact performance gaps for individual players.

## What did you build or discover?

I built an interactive Python/Tkinter dashboard that pulls raw tracking and event data from the SkillCorner Open Data repository (A-League 2024/2025) and processes it into per-90 metrics, Expected Possession Value (EPV), and Off-Ball Run (OBR) data, among other metrics.

The dashboard features several key analytical tools:

*Top/Bottom 5 Facet Grids: When multiple metrics are selected, the dashboard automatically generates a grid. For every metric, it displays the Top 5 positive and Bottom 5 negative Home-Away deltas for the selected team, alongside the same league-wide comparison.

*Overlap Detection: A dedicated text panel identifies "Players in Both," highlighting when a team's worst-performing player on the road is also among the league's worst for that specific metric.

*Clean Spatial Visualizations: We utilized custom side-by-side bar charts with inline text labels and removed bounding boxes to ensure that when comparing players, their names and values are perfectly readable without overlapping.

**Key Finding Example**: As seen in the Auckland FC screenshot, the dashboard easily isolates players like F. Gallegos, whose Off-Ball Run volume (obr_count_p90) and overall impact (epv_total_sum_p90) drops massively when playing away from home, placing him in both the team and league-wide bottom 5 for those metrics.

<img width="1107" height="1027" alt="Dashboard_Sample" src="https://github.com/user-attachments/assets/63e5899b-33b8-4c77-82bc-2da362d65ef1" />

## Why does it matter?

For coaches, scouts, and front offices, understanding why a player performs differently is just as important as knowing that they perform differently.

*Tactical Adjustments: Coaches can use this to identify players who need different tactical instructions when playing away to compensate for a loss in pass volume or off-ball aggression.

*Recruitment & Scouting: Scouts can filter out players whose impressive season stats are heavily inflated by home games. A player with a massive negative EPV delta away from home might struggle with crowd pressure or unfamiliar pitches.

*Sports Science & Fatigue: The addition of pitch dimensions and referee data allows analysts to start asking why the drop-off occurs. Is it travel fatigue, a tighter pitch, or a referee who allows more physical play?

By making these hidden deltas instantly visible, this tool turns raw tracking data into actionable intelligence for player management and game preparation.

## Python code to create/view dashboard
Run setup_env.py to install all the relevant libraries.
Run app_1.py to access the dashboard. AC2_2.py is called within app_1.py 

