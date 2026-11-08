# ******************
# Load and Transform Data
# ******************

"""
SkillCorner Open Data — Home/Away Player Aggregates
====================================================

Outputs:
    skillcorner_match_data.csv      (per-match player stats for contextual joins)
    skillcorner_player_home_away.csv (aggregated season stats)
"""

import time
from io import StringIO
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
BASE_RAW = "https://raw.githubusercontent.com/SkillCorner/opendata/master/data"
MATCHES_JSON_URL = f"{BASE_RAW}/matches.json"
MATCHES_DIR = f"{BASE_RAW}/matches"

OBR_SUBTYPES = [
    "behind", "coming_short", "cross_receiver", "dropping_off",
    "overlap", "pulling_half_space", "pulling_wide",
    "run_ahead_of_the_ball", "support", "underlap",
]

PHASE_TYPES = [
    "build_up", "create", "finish",
    "transition", "chaotic", "direct",
]
PHASE_TYPES_USED = PHASE_TYPES


# ---------------------------------------------------------------------
# HTTP session with retries
# ---------------------------------------------------------------------
def _make_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = _make_session()


def fetch_json(url, timeout=30):
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_csv(url, timeout=60):
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text), low_memory=False)


# ---------------------------------------------------------------------
# Match metadata (Now includes Referee & Pitch Size)
# ---------------------------------------------------------------------
def load_matches():
    matches_json = fetch_json(MATCHES_JSON_URL)

    if isinstance(matches_json, dict) and "matches" in matches_json:
        matches_json = matches_json["matches"]

    rows = []
    for m in matches_json:
        mid = m.get("id") or m.get("match_id")

        home = m.get("home_team") or {}
        away = m.get("away_team") or {}
        home_id = home.get("id") if isinstance(home, dict) else None
        away_id = away.get("id") if isinstance(away, dict) else None
        home_name = home.get("name") if isinstance(home, dict) else home
        away_name = away.get("name") if isinstance(away, dict) else away

        if home_id is None:
            home_id = m.get("home_team_id")
        if away_id is None:
            away_id = m.get("away_team_id")

        if home_id is None and isinstance(m.get("home_team"), int):
            home_id = m["home_team"]
        if away_id is None and isinstance(m.get("away_team"), int):
            away_id = m["away_team"]

        rows.append({
            "match_id": mid,
            "date": m.get("date"),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team_name": home_name,
            "away_team_name": away_name,
            "referee": None,
            "pitch_length": None,
            "pitch_width": None,
        })

    df = pd.DataFrame(rows)

    # Fetch missing team info and new context data from match.json
    for i, row in df.iterrows():
        mid = row["match_id"]
        need_fetch = (
                pd.isna(row["home_team_id"]) or pd.isna(row["away_team_id"]) or
                pd.isna(row["home_team_name"]) or pd.isna(row["away_team_name"]) or
                pd.isna(row["referee"])
        )
        if need_fetch:
            try:
                mj = fetch_json(f"{MATCHES_DIR}/{mid}/{mid}_match.json")
                ht = mj.get("home_team") or {}
                at = mj.get("away_team") or {}
                df.at[i, "home_team_id"] = ht.get("id")
                df.at[i, "away_team_id"] = at.get("id")
                df.at[i, "home_team_name"] = ht.get("name")
                df.at[i, "away_team_name"] = at.get("name")
                df.at[i, "referee"] = mj.get("referee", {}).get("name", "Unknown")
                df.at[i, "pitch_length"] = mj.get("pitch_length")
                df.at[i, "pitch_width"] = mj.get("pitch_width")
            except Exception:
                pass
            time.sleep(0.2)

    team_lookup = {}
    for _, r in df.iterrows():
        if pd.notna(r["home_team_id"]) and pd.notna(r["home_team_name"]):
            team_lookup[int(r["home_team_id"])] = r["home_team_name"]
        if pd.notna(r["away_team_id"]) and pd.notna(r["away_team_name"]):
            team_lookup[int(r["away_team_id"])] = r["away_team_name"]

    return df, team_lookup


# ---------------------------------------------------------------------
# Minutes played (with minutes_tip)
# ---------------------------------------------------------------------
def minutes_played_for_match(match_id):
    url = f"{MATCHES_DIR}/{match_id}/{match_id}_match.json"
    match_json = fetch_json(url)
    rows = []
    for p in match_json.get("players", []):
        pt_total = ((p.get("playing_time") or {}).get("total")) or {}
        role = p.get("player_role") or {}
        rows.append({
            "match_id": match_id,
            "player_id": p.get("id"),
            "team_id": p.get("team_id"),
            "player_name": p.get("player_name") or p.get("short_name"),
            "position_group": role.get("position_group"),
            "position_name": role.get("name"),
            "minutes_played": pt_total.get("minutes_played"),
            "minutes_tip": pt_total.get("minutes_tip"),
        })
    df = pd.DataFrame(rows)
    df["minutes_played"] = pd.to_numeric(df["minutes_played"], errors="coerce")
    df["minutes_tip"] = pd.to_numeric(df["minutes_tip"], errors="coerce")
    return df


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _dedupe_columns(df):
    return df.loc[:, ~df.columns.duplicated(keep="first")].copy()


def _coerce_keys(df):
    for k in ("player_id", "match_id", "team_id"):
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce").astype("Int64")
    return df


# ---------------------------------------------------------------------
# Dynamic events
# ---------------------------------------------------------------------
def load_match_events(match_id, home_team_id):
    url = f"{MATCHES_DIR}/{match_id}/{match_id}_dynamic_events.csv"
    de = fetch_csv(url)
    de = _dedupe_columns(de)
    de["match_id"] = match_id
    de["is_home"] = de["team_id"] == home_team_id
    return de


# ---------------------------------------------------------------------
# Passing metrics (Now includes EPV)
# ---------------------------------------------------------------------
def passing_metrics_for_match(de):
    passes = de[
        (de["event_type"] == "player_possession") &
        (de["end_type"] == "pass")
        ].copy()

    if passes.empty:
        return pd.DataFrame()

    passes["is_complete"] = passes["pass_outcome"].eq("successful")
    passes["is_progressive"] = passes["pass_ahead"].fillna(False).astype(bool)
    passes["is_line_breaking"] = passes["furthest_line_break"].notna()

    rng = passes["pass_range"].fillna("unknown")
    passes["is_short"] = rng.eq("short")
    passes["is_medium"] = rng.eq("medium")
    passes["is_long"] = rng.eq("long")

    pid = pd.to_numeric(passes.get("pass_direction_id"), errors="coerce")
    passes["is_forward"] = pid.eq(1)
    passes["is_backward"] = pid.eq(2)
    passes["is_sideways"] = pid.isin([3, 4])

    if "team_in_possession_phase_type" in passes.columns:
        phase = passes["team_in_possession_phase_type"].fillna("unknown")
    else:
        phase = pd.Series("unknown", index=passes.index)
    for p in PHASE_TYPES_USED:
        passes[f"phase_{p}"] = phase.eq(p)

    for c in ("xthreat", "xpass_completion", "n_opponents_bypassed", "possession_epv_total"):
        if c in passes.columns:
            passes[c] = pd.to_numeric(passes[c], errors="coerce")

    group_keys = ["match_id", "player_id", "team_id", "is_home"]

    agg_dict = dict(
        passes_attempted=("event_id", "count"),
        passes_completed=("is_complete", "sum"),
        passes_progressive=("is_progressive", "sum"),
        passes_line_breaking=("is_line_breaking", "sum"),
        passes_short=("is_short", "sum"),
        passes_medium=("is_medium", "sum"),
        passes_long=("is_long", "sum"),
        passes_forward=("is_forward", "sum"),
        passes_backward=("is_backward", "sum"),
        passes_sideways=("is_sideways", "sum"),
        n_opponents_bypassed_sum=("n_opponents_bypassed", "sum"),
        epv_total_sum=("possession_epv_total", "sum"),
    )

    for p in PHASE_TYPES_USED:
        agg_dict[f"passes_{p}"] = (f"phase_{p}", "sum")

    grouped = passes.groupby(group_keys, dropna=False).agg(**agg_dict).reset_index()

    grouped["pass_completion_pct"] = (
            grouped["passes_completed"] / grouped["passes_attempted"] * 100
    ).round(2)

    for p in PHASE_TYPES_USED:
        col = f"passes_{p}"
        if col in grouped.columns:
            grouped[f"pct_{col}"] = (
                    grouped[col] / grouped["passes_attempted"] * 100
            ).round(2)

    return grouped


# ---------------------------------------------------------------------
# OBR metrics
# ---------------------------------------------------------------------
def obr_metrics_for_match(de):
    obr = de[de["event_type"] == "off_ball_run"].copy()
    if obr.empty:
        return pd.DataFrame()

    obr = _dedupe_columns(obr)

    obr["is_breaking_line"] = obr["break_defensive_line"].fillna(False).astype(bool)
    obr["is_pushing_line"] = obr["push_defensive_line"].fillna(False).astype(bool)
    obr["is_give_and_go"] = obr["give_and_go"].fillna(False).astype(bool)
    obr["is_intended_run_behind"] = obr["intended_run_behind"].fillna(False).astype(bool)

    for c in ("speed_avg", "distance_covered"):
        if c in obr.columns:
            obr[c] = pd.to_numeric(obr[c], errors="coerce")

    for s in OBR_SUBTYPES:
        obr[f"obr_{s}"] = obr["event_subtype"].eq(s)

    agg_cols = {
        "obr_count": ("event_id", "count"),
        "obr_runs_breaking_line": ("is_breaking_line", "sum"),
        "obr_runs_pushing_line": ("is_pushing_line", "sum"),
        "obr_give_and_go": ("is_give_and_go", "sum"),
        "obr_intended_run_behind": ("is_intended_run_behind", "sum"),
        "obr_speed_avg_mean": ("speed_avg", "mean"),
        "obr_distance_covered_sum": ("distance_covered", "sum"),
    }
    for s in OBR_SUBTYPES:
        agg_cols[f"obr_{s}"] = (f"obr_{s}", "sum")

    group_keys = ["match_id", "player_id", "team_id", "is_home"]
    return obr.groupby(group_keys, dropna=False).agg(**agg_cols).reset_index()


# ---------------------------------------------------------------------
# Build the tables
# ---------------------------------------------------------------------
def build_home_away_table(min_minutes=30, save_outputs=True):
    matches, team_lookup = load_matches()

    all_passing, all_obr, all_minutes = [], [], []

    for _, m in matches.iterrows():
        mid, home_id = m["match_id"], m["home_team_id"]
        try:
            de = load_match_events(mid, home_id)
            p = passing_metrics_for_match(de)
            o = obr_metrics_for_match(de)
            mn = minutes_played_for_match(mid)

            if not p.empty: all_passing.append(p)
            if not o.empty: all_obr.append(o)
            if not mn.empty: all_minutes.append(mn)

            time.sleep(0.3)
        except Exception:
            continue

    passing_df = pd.concat(all_passing, ignore_index=True) if all_passing else pd.DataFrame()
    obr_df = pd.concat(all_obr, ignore_index=True) if all_obr else pd.DataFrame()
    minutes_df = pd.concat(all_minutes, ignore_index=True) if all_minutes else pd.DataFrame()

    if minutes_df.empty:
        raise RuntimeError("No minutes loaded.")

    minutes_df = minutes_df[minutes_df["minutes_played"].fillna(0) >= min_minutes].copy()

    home_map = matches.set_index("match_id")["home_team_id"].to_dict()
    minutes_df["is_home"] = minutes_df.apply(
        lambda r: r["team_id"] == home_map.get(r["match_id"]), axis=1
    )

    p_side = passing_df.drop(columns=["team_id", "is_home"], errors="ignore")
    o_side = obr_df.drop(columns=["team_id", "is_home"], errors="ignore")

    minutes_df = _coerce_keys(minutes_df)
    p_side = _coerce_keys(p_side)
    o_side = _coerce_keys(o_side)

    combined = minutes_df.merge(p_side, on=["match_id", "player_id"], how="left")
    combined = combined.merge(o_side, on=["match_id", "player_id"], how="left")

    # Merge Referee and Pitch Size
    match_context = matches[["match_id", "referee", "pitch_length", "pitch_width"]]
    combined = combined.merge(match_context, on="match_id", how="left")

    for c in combined.columns:
        if c.startswith(("passes_", "obr_")) and not c.endswith(("_pct", "_mean", "_sum", "_min")):
            combined[c] = combined[c].fillna(0)

    combined["epv_total_sum"] = combined["epv_total_sum"].fillna(0)

    combined["team_name"] = combined["team_id"].astype(int).map(team_lookup)

    # -------------------------------------------------------------
    # Save Per-Match Data
    # -------------------------------------------------------------
    if save_outputs:
        date_map = matches.set_index("match_id")["date"].to_dict()
        combined["match_date"] = combined["match_id"].map(date_map)

        match_cols = [
            "match_id", "match_date", "player_id", "player_name",
            "team_id", "team_name", "position_group", "is_home",
            "referee", "pitch_length", "pitch_width",
            "minutes_played", "passes_attempted", "passes_completed",
            "passes_progressive", "obr_count", "obr_distance_covered_sum",
            "epv_total_sum"
        ]
        match_cols = [c for c in match_cols if c in combined.columns]
        combined[match_cols].to_csv("skillcorner_match_data.csv", index=False)
        print("Wrote skillcorner_match_data.csv")

    # -------------------------------------------------------------
    # Aggregate Season Data
    # -------------------------------------------------------------
    sum_cols = [
                   "minutes_played", "minutes_tip",
                   "passes_attempted", "passes_completed", "passes_progressive",
                   "passes_line_breaking", "passes_short", "passes_medium", "passes_long",
                   "passes_forward", "passes_backward", "passes_sideways",
                   "n_opponents_bypassed_sum", "epv_total_sum",
                   *[f"passes_{p}" for p in PHASE_TYPES_USED],
                   "obr_count", "obr_runs_breaking_line", "obr_runs_pushing_line",
                   "obr_give_and_go", "obr_intended_run_behind", "obr_distance_covered_sum",
               ] + [f"obr_{s}" for s in OBR_SUBTYPES]

    mean_cols = [
        "obr_speed_avg_mean", "pass_completion_pct",
        *[f"pct_passes_{p}" for p in PHASE_TYPES_USED],
    ]

    agg_dict = {c: "sum" for c in sum_cols if c in combined.columns}
    agg_dict.update({c: "mean" for c in mean_cols if c in combined.columns})

    player_ha = combined.groupby(
        ["player_id", "player_name", "team_id", "position_group", "is_home"],
        dropna=False
    ).agg({**agg_dict, "match_id": "nunique"}).reset_index()
    player_ha = player_ha.rename(columns={"match_id": "matches_played"})

    player_ha["team_id_int"] = pd.to_numeric(player_ha["team_id"], errors="coerce")
    player_ha["team_name"] = player_ha["team_id_int"].map(team_lookup)
    player_ha = player_ha.drop(columns=["team_id_int"])

    front_cols = ["player_id", "player_name", "team_id", "team_name",
                  "position_group", "is_home"]
    other_cols = [c for c in player_ha.columns if c not in front_cols]
    player_ha = player_ha[front_cols + other_cols]

    # Normalisations
    per90_targets = [
        "passes_attempted", "passes_completed", "passes_progressive",
        "passes_line_breaking", "obr_count", "obr_runs_breaking_line",
        "obr_give_and_go", "epv_total_sum", *[f"passes_{p}" for p in PHASE_TYPES_USED],
    ]
    for c in per90_targets:
        if c in player_ha.columns:
            player_ha[f"{c}_p90"] = (
                    player_ha[c] / player_ha["minutes_played"] * 90
            ).round(2)

    if save_outputs:
        player_ha.to_csv("skillcorner_player_home_away.csv", index=False)
        print("Wrote skillcorner_player_home_away.csv")

    return player_ha


if __name__ == "__main__":
    df = build_home_away_table(min_minutes=30)
    print("\nFinal shape:", df.shape)