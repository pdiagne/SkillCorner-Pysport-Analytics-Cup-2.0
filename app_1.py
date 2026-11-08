import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# ------------------------------------------------------------------
# 1. Load SkillCorner Data
# ------------------------------------------------------------------
from AC2_2 import build_home_away_table

# This builds the aggregates
df = build_home_away_table(save_outputs=True)
df["is_home"] = df["is_home"].astype(str).str.lower().isin(["true", "1", "yes"])

EXCLUDE = {
    "player_id", "team_id", "is_home", "matches_played",
    "minutes_played", "minutes_tip",
}
METRICS = [
    c for c in df.columns
    if pd.api.types.is_numeric_dtype(df[c]) and c not in EXCLUDE
]

DEFAULTS = [
    "passes_attempted_p90", "passes_completed_p90", "passes_progressive_p90",
    "passes_line_breaking_p90", "obr_count_p90", "obr_runs_breaking_line_p90",
    "pass_completion_pct", "epv_total_sum_p90"
]
DEFAULTS = [m for m in DEFAULTS if m in METRICS]

TEAMS = sorted(df["team_name"].dropna().unique())


def eligible_teams(frame):
    ok = []
    for team, sub in frame.groupby("team_name"):
        if sub["is_home"].nunique() >= 2:
            ok.append(team)
    return sorted(ok)


ELIGIBLE_TEAMS = eligible_teams(df)
EXCLUDED_TEAMS = sorted(set(TEAMS) - set(ELIGIBLE_TEAMS))


# ------------------------------------------------------------------
# 2. Aggregation Functions
# ------------------------------------------------------------------
def aggregate(team, metrics):
    sub = df[df["team_name"] == team]
    if sub.empty or not metrics:
        return pd.DataFrame(), 0

    if sub["is_home"].nunique() < 2:
        return pd.DataFrame(), 0

    all_players = sub["player_name"].nunique()
    sides_per_player = sub.groupby("player_name")["is_home"].nunique()
    paired_players = sides_per_player[sides_per_player == 2].index
    n_excluded = all_players - len(paired_players)

    sub = sub[sub["player_name"].isin(paired_players)]
    if sub.empty:
        return pd.DataFrame(), n_excluded

    g = sub.groupby(["player_name", "is_home"])[metrics].mean().reset_index()
    wide = g.pivot(index="player_name", columns="is_home", values=metrics)
    wide.columns = [f"{m}_{'home' if h else 'away'}" for m, h in wide.columns]
    wide = wide.reset_index()

    for m in metrics:
        for side in ("home", "away"):
            c = f"{m}_{side}"
            if c not in wide.columns:
                wide[c] = np.nan
        wide[f"{m}_delta"] = wide[f"{m}_home"] - wide[f"{m}_away"]

    return wide, n_excluded


def aggregate_league(metrics):
    if df.empty or not metrics:
        return pd.DataFrame()

    sides_per_player = df.groupby(["team_name", "player_name"])["is_home"].nunique()
    paired_players = sides_per_player[sides_per_player == 2].reset_index()
    sub = df.merge(paired_players[["team_name", "player_name"]], on=["team_name", "player_name"])

    if sub.empty:
        return pd.DataFrame()

    g = sub.groupby(["team_name", "player_name", "is_home"])[metrics].mean().reset_index()
    wide = g.pivot(index=["team_name", "player_name"], columns="is_home", values=metrics)
    wide.columns = [f"{m}_{'home' if h else 'away'}" for m, h in wide.columns]
    wide = wide.reset_index()

    for m in metrics:
        for side in ("home", "away"):
            c = f"{m}_{side}"
            if c not in wide.columns:
                wide[c] = np.nan
        wide[f"{m}_delta"] = wide[f"{m}_home"] - wide[f"{m}_away"]

    return wide


def get_top_bottom_5(s_df, col):
    s_pos = s_df[s_df[col] > 0].nlargest(5, col)
    s_neg = s_df[s_df[col] < 0].nsmallest(5, col)
    return pd.concat([s_neg, s_pos]).sort_values(col).reset_index(drop=True)


# ------------------------------------------------------------------
# 3. GUI Setup
# ------------------------------------------------------------------
root = tk.Tk()
root.title("Home vs Away Dashboard")
root.geometry("1400x900")

tk.Label(root, text="Team:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
team_var = tk.StringVar(value=ELIGIBLE_TEAMS[0] if ELIGIBLE_TEAMS else "")
team_cb = ttk.Combobox(root, textvariable=team_var, values=ELIGIBLE_TEAMS, width=45, state="readonly")
team_cb.grid(row=0, column=1, sticky="w", padx=6, pady=6)

tk.Label(root, text="Metrics:").grid(row=1, column=0, sticky="nw", padx=6, pady=6)

metric_container = tk.Frame(root)
metric_container.grid(row=1, column=1, sticky="w", padx=6, pady=6)
scrollbar = tk.Scrollbar(metric_container, orient="vertical")
metric_listbox = tk.Listbox(metric_container, selectmode="extended", yscrollcommand=scrollbar.set, width=45, height=12,
                            exportselection=False)
scrollbar.config(command=metric_listbox.yview)
metric_listbox.pack(side="left", fill="y")
scrollbar.pack(side="right", fill="y")

for m in METRICS: metric_listbox.insert("end", m)
for i, m in enumerate(METRICS):
    if m in DEFAULTS: metric_listbox.selection_set(i)

# --- Overlap Info Panel ---
tk.Label(root, text="Players in Both\nTeam & League Charts").grid(row=1, column=2, sticky="nw", padx=6, pady=6)

overlap_frame = tk.Frame(root)
overlap_frame.grid(row=1, column=3, sticky="nw", padx=6, pady=6)
overlap_scroll = tk.Scrollbar(overlap_frame, orient="vertical")
overlap_text = tk.Text(overlap_frame, width=45, height=12, state="disabled", bg="#f0f0f0", font=("TkDefaultFont", 9),
                       wrap="word", yscrollcommand=overlap_scroll.set)
overlap_scroll.config(command=overlap_text.yview)
overlap_text.pack(side="left", fill="y")
overlap_scroll.pack(side="right", fill="y")
overlap_text.tag_configure("metric_header", font=("TkDefaultFont", 9, "bold"), spacing1=6)


def on_recalc():
    recalc()


btn = tk.Button(root, text="Recalculate", command=on_recalc, bg="#2ecc71", fg="white", padx=12, pady=4)
btn.grid(row=2, column=0, pady=8, padx=6, sticky="w")

if EXCLUDED_TEAMS:
    excluded_note = "Excluded teams (no home/away split in data): " + ", ".join(EXCLUDED_TEAMS)
    tk.Label(root, text=excluded_note, fg="#c0392b", font=("TkDefaultFont", 8), anchor="w", justify="left",
             wraplength=900).grid(row=2, column=1, sticky="w", padx=6, pady=8, columnspan=3)

# --- Scrollable Plot Area ---
plot_outer = tk.Frame(root)
plot_outer.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
plot_canvas = tk.Canvas(plot_outer, highlightthickness=0, bg="#f0f0f0")
plot_scroll = tk.Scrollbar(plot_outer, orient="vertical", command=plot_canvas.yview)
plot_canvas.configure(yscrollcommand=plot_scroll.set)

plot_scroll.pack(side="right", fill="y")
plot_canvas.pack(side="left", fill="both", expand=True)

plot_inner = tk.Frame(plot_canvas, bg="#f0f0f0")
plot_inner_id = plot_canvas.create_window((0, 0), window=plot_inner, anchor="nw")


def _on_canvas_configure(event):
    plot_canvas.itemconfigure(plot_inner_id, width=event.width)


plot_canvas.bind("<Configure>", _on_canvas_configure)


def _on_inner_configure(event):
    plot_canvas.configure(scrollregion=plot_canvas.bbox("all"))


plot_inner.bind("<Configure>", _on_inner_configure)


def _on_mousewheel(event):
    if event.delta: plot_canvas.yview_scroll(int(-event.delta / 120), "units")


def _on_button4(_): plot_canvas.yview_scroll(-1, "units")


def _on_button5(_): plot_canvas.yview_scroll(1, "units")


for w in (plot_canvas, plot_inner):
    w.bind("<MouseWheel>", _on_mousewheel)
    w.bind("<Button-4>", _on_button4)
    w.bind("<Button-5>", _on_button5)

figure_canvas = None
canvas_widget = None
root.rowconfigure(3, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(3, weight=1)


# ------------------------------------------------------------------
# 4. Main Recalculate Logic
# ------------------------------------------------------------------
def recalc():
    global figure_canvas, canvas_widget

    selected = [metric_listbox.get(i) for i in metric_listbox.curselection()]
    team = team_var.get()

    if canvas_widget is not None:
        canvas_widget.destroy()
        figure_canvas = None
        canvas_widget = None

    team_rows = df[df["team_name"] == team]
    agg_team = pd.DataFrame()
    plottable = []
    suptitle = ""
    overlap_results = {}

    if team_rows.empty:
        suptitle = f"{team} — no data"
    elif team_rows["is_home"].nunique() < 2:
        suptitle = f"{team} — excluded (no home/away split in data)"
    else:
        agg_team, n_excluded = aggregate(team, selected)
        if agg_team.empty or not selected:
            suptitle = f"{team} — no paired players"
        else:
            plottable = [m for m in selected if f"{m}_delta" in agg_team.columns]
            if not plottable:
                suptitle = f"{team} — no plottable metrics"

    # --- Plotting ---
    if plottable:
        agg_league = aggregate_league(plottable)
        n_rows = len(plottable)
        fig_height = max(6.0, 3.8 * n_rows + 0.6)
        fig = plt.Figure(figsize=(16, fig_height), dpi=100)

        gs = fig.add_gridspec(n_rows, 2, hspace=0.6, wspace=0.35, top=0.95, bottom=0.05, left=0.08, right=0.95)

        for i, m in enumerate(plottable):
            col = f"{m}_delta"
            ax_team = fig.add_subplot(gs[i, 0])
            s_team = agg_team[["player_name", col]].dropna().copy()

            ax_league = fig.add_subplot(gs[i, 1])
            s_league = agg_league[["team_name", "player_name", col]].dropna().copy()

            if s_team.empty:
                ax_team.set_title(f"Δ {m} (no paired data)", fontsize=10)
                ax_team.axis("off")
            elif s_league.empty:
                ax_league.set_title(f"League Δ {m} (no paired data)", fontsize=10)
                ax_league.axis("off")
            else:
                s_team_top5 = get_top_bottom_5(s_team, col)
                s_league_top5 = get_top_bottom_5(s_league, col)

                team_players_set = set(s_team_top5["player_name"])
                league_overlap = s_league_top5[s_league_top5["player_name"].isin(team_players_set)].copy()

                if not league_overlap.empty:
                    overlap_results[m] = league_overlap

                # Plot Team
                colors = ["#c0392b" if x < 0 else "#2980b9" for x in s_team_top5[col]]
                bars = ax_team.barh(s_team_top5["player_name"], s_team_top5[col], color=colors)
                ax_team.axvline(0, color="black", linewidth=0.6)
                ax_team.set_yticks([])

                x_max = s_team_top5[col].max() if not s_team_top5.empty else 1
                x_min = s_team_top5[col].min() if not s_team_top5.empty else 0
                x_range = x_max - x_min if x_max != x_min else 1

                for bar, player in zip(bars, s_team_top5["player_name"]):
                    val = bar.get_width()
                    y = bar.get_y() + bar.get_height() / 2
                    if val > 0:
                        ax_team.text(val + x_range * 0.02, y, player, va="center", ha="left", fontsize=8)
                    else:
                        ax_team.text(val - x_range * 0.02, y, player, va="center", ha="right", fontsize=8)

                ax_team.set_xlim(x_min - x_range * 0.4 - 0.5, x_max + x_range * 0.4 + 0.5)
                ax_team.set_title(f"{team}\nΔ {m}", fontsize=10, fontweight="bold")
                ax_team.set_xlabel("Home − Away", fontsize=8)
                for sp in ax_team.spines.values(): sp.set_visible(False)

                # Plot League
                s_league_top5["display_name"] = s_league_top5["player_name"] + " (" + s_league_top5["team_name"] + ")"
                colors = ["#c0392b" if x < 0 else "#2980b9" for x in s_league_top5[col]]
                bars = ax_league.barh(s_league_top5["display_name"], s_league_top5[col], color=colors)
                ax_league.axvline(0, color="black", linewidth=0.6)
                ax_league.set_yticks([])

                x_max = s_league_top5[col].max() if not s_league_top5.empty else 1
                x_min = s_league_top5[col].min() if not s_league_top5.empty else 0
                x_range = x_max - x_min if x_max != x_min else 1

                for bar, disp_name in zip(bars, s_league_top5["display_name"]):
                    val = bar.get_width()
                    y = bar.get_y() + bar.get_height() / 2
                    if val > 0:
                        ax_league.text(val + x_range * 0.02, y, disp_name, va="center", ha="left", fontsize=8)
                    else:
                        ax_league.text(val - x_range * 0.02, y, disp_name, va="center", ha="right", fontsize=8)

                ax_league.set_xlim(x_min - x_range * 0.5 - 1, x_max + x_range * 0.5 + 1)
                ax_league.set_title(f"League Wide\nΔ {m}", fontsize=10, fontweight="bold")
                ax_league.set_xlabel("Home − Away", fontsize=8)
                for sp in ax_league.spines.values(): sp.set_visible(False)
    else:
        fig = plt.Figure(figsize=(12, 1.6), dpi=100)
        ax = fig.add_subplot(111)
        ax.axis("off")
        ax.text(0.5, 0.5, suptitle, ha="center", va="center", fontsize=12, color="#c0392b", transform=ax.transAxes)

    # --- Update Overlap Panel ---
    overlap_text.config(state="normal")
    overlap_text.delete("1.0", tk.END)
    if overlap_results:
        for m, df_overlap in overlap_results.items():
            overlap_text.insert(tk.END, f"• {m}\n", "metric_header")
            for _, row in df_overlap.iterrows():
                overlap_text.insert(tk.END, f"   - {row['player_name']} ({row[f'{m}_delta']:+.2f})\n")
    else:
        overlap_text.insert(tk.END, "No overlaps found in Top/Bottom 5.")
    overlap_text.config(state="disabled")

    figure_canvas = FigureCanvasTkAgg(fig, master=plot_inner)
    canvas_widget = figure_canvas.get_tk_widget()
    canvas_widget.pack(fill="both", expand=False)

    canvas_widget.bind("<MouseWheel>", _on_mousewheel)
    canvas_widget.bind("<Button-4>", _on_button4)
    canvas_widget.bind("<Button-5>", _on_button5)

    plot_inner.update_idletasks()
    plot_canvas.configure(scrollregion=plot_canvas.bbox("all"))


recalc()
root.mainloop()