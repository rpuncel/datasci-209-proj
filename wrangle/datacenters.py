"""Derived frames and summary stats for Epoch AI's frontier data center data.

Logic is ported from the dashboard's former inline ``exploratory-setup`` cell;
each accessor is memoized so all documents share one computation per render.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
import pgeocode

import datasets
from constants import STATE_ABBRS, STATE_NAMES

POWER = "Current power (MW)"
H100 = "Current H100 equivalents"
CAPEX = "Current total capital cost (2025 USD billions)"

# Only genuine aliases where the raw label differs from the canonical one.
# Companies not listed here pass through under their own name — no maintenance
# needed when Epoch adds a new operator.
_OWNER_ALIASES = {
    "aws": "Amazon",
    "facebook": "Meta",
    "spacexai": "xAI",
    "spacex": "xAI",
}

# Sites Epoch leaves without an Owner: the operator brand leads the site Name.
_NAME_OWNER_FALLBACK = {
    "QTS": "QTS",
    "STACK": "STACK",
    "Stream": "Stream",
    "Vantage": "Vantage",
    "DayOne": "DayOne",
}

_CONTINENTS = {
    "United States": "North America",
    "Malaysia": "Asia",
    "China": "Asia",
    "Indonesia": "Asia",
    "Portugal": "Europe",
    "United Arab Emirates": "Asia",
}


def clean_party(value):
    """Collapse free-text owner/user strings onto a canonical company label."""
    if pd.isna(value):
        return "Unknown"
    text = re.sub(r"#\w+", "", str(value).split(",")[0]).strip()
    for needle, label in _OWNER_ALIASES.items():
        if needle in text.lower():
            return label
    return text or "Unknown"

def fill_unknown_owners_from_name(df: pd.DataFrame):
    def known_owner_from_name(s: pd.Series):
        def f(value: str):
            for n in _NAME_OWNER_FALLBACK:
                if value.startswith(n):
                    return _NAME_OWNER_FALLBACK[n]
        return s.map(f)
    return df["owner_clean"].where(~(df["owner_clean"].isna() | (df["owner_clean"] == 'Unknown')), known_owner_from_name(df["Name"]))

def extract_state(row):
    """Best-effort U.S. state abbreviation from address, name, and notes."""
    if row.get("Country") != "United States":
        return "Non-U.S."
    text = " ".join(
        str(row.get(col, ""))
        for col in ["Address", "Name", "Notes"]
        if pd.notna(row.get(col, pd.NA))
    )
    abbr_match = re.search(r"\b(" + "|".join(sorted(STATE_ABBRS)) + r")\b", text)
    if abbr_match:
        return abbr_match.group(1)
    for name, abbr in STATE_NAMES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", text, flags=re.IGNORECASE):
            return abbr
    return "Unknown"

def augment_geocoding(df: pd.DataFrame):
    df = df.copy()
    df["zip"] =  (
        df[df["Country"] == "United States"]
        ["Address"].str.extract(r"(\d{5})(?:-\d{4})?\s*$")
    )

    nomi = pgeocode.Nominatim("us")
    zip_lookup = nomi.query_postal_code(df["zip"].dropna().unique().tolist())[
        ["postal_code", "latitude", "longitude"]
    ].rename(
        columns={"postal_code": "zip", "latitude": "Latitude", "longitude": "Longitude"}
    )
    return df.merge(zip_lookup, on="zip", how="left")

def augment_site_power_rank(df: pd.DataFrame):
    centers = df.assign(
        rank=lambda x: x[POWER].rank(method='first', ascending=False, na_option='bottom')
    )
    #rank = (
    #    #centers[["Name", "owner_clean", POWER, H100, CAPEX, "Country"]]
    #    centers.dropna(subset=[POWER])
    #    .reset_index(drop=True)
    #)
    centers["cumulative_power_share"] = (
        centers.sort_values("rank")
        .pipe(lambda x: x[POWER].cumsum() / x[POWER].sum())
    )
    return centers

@lru_cache(maxsize=None)
def enriched_centers() -> pd.DataFrame:
    """Epoch data centers with numeric coercion and derived analysis columns."""
    centers = datasets.data_centers().copy()
    centers = centers.assign(
        **{
           POWER: lambda x: pd.to_numeric(x[POWER], errors="coerce"),
           H100: lambda x: pd.to_numeric(x[H100], errors="coerce"),
           CAPEX: lambda x: pd.to_numeric(x[CAPEX], errors="coerce")
        }
    ).assign(
        owner_clean = lambda x: x["Owner"].map(clean_party)
    ).assign(
        owner_clean = lambda x: fill_unknown_owners_from_name(x)
    )
    centers["user_clean"] = centers["Users"].map(clean_party)
    centers["state"] = centers.apply(extract_state, axis=1)
    centers["continent"] = centers["Country"].map(_CONTINENTS).fillna("Other")
    centers["h100_per_mw"] = centers[H100] / centers[POWER]
    centers["capex_per_mw"] = centers[CAPEX] / centers[POWER]
    centers = centers.replace([float("inf"), float("-inf")], pd.NA)
    centers = augment_site_power_rank(centers)
    centers = augment_geocoding(centers)
    return centers


@lru_cache(maxsize=None)
def timeline() -> pd.DataFrame:
    """Per-site timeline records with dates and metrics coerced to numerics."""
    frame = datasets.data_center_timelines().copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for col in [
        "Power (MW)",
        "H100 equivalents",
        "Total capital cost (2025 USD billions)",
    ]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


@lru_cache(maxsize=None)
def owner_summary() -> pd.DataFrame:
    centers = enriched_centers()
    summary = (
        centers.groupby("owner_clean", dropna=False)
        .agg(
            power_mw=(POWER, "sum"),
            capex_b=(CAPEX, "sum"),
            h100_eq=(H100, "sum"),
            sites=("Name", "count"),
        )
        .reset_index()
        .sort_values("power_mw", ascending=False)
    )
    summary["power_share"] = summary["power_mw"] / centers[POWER].sum()
    return summary



@lru_cache(maxsize=None)
def site_rank() -> pd.DataFrame:
    centers = enriched_centers()
    return centers.sort_values("rank")


@lru_cache(maxsize=None)
def yearly() -> pd.DataFrame:
    """Year-end portfolio totals from the latest timeline record per site."""
    records = timeline()
    year_rows = []
    for year in range(2019, 2031):
        latest = (
            records[records["Date"] <= pd.Timestamp(f"{year}-12-31")]
            .sort_values("Date")
            .groupby("Data center")
            .tail(1)
        )
        year_rows.append(
            {
                "date": pd.Timestamp(f"{year}-12-31"),
                "year": year,
                "power_mw": latest["Power (MW)"].sum(),
                "capex_b": latest["Total capital cost (2025 USD billions)"].sum(),
                "h100_eq": latest["H100 equivalents"].sum(),
                "data_centers": latest["Data center"].nunique(),
            }
        )
    frame = pd.DataFrame(year_rows)
    frame["added_power_mw"] = frame["power_mw"].diff().fillna(frame["power_mw"])
    frame["record_type"] = frame["year"].map(
        lambda y: "Observed / near-term" if y <= 2026 else "Planned"
    )
    return frame


@lru_cache(maxsize=None)
def events() -> pd.DataFrame:
    """Generative-AI milestones, with label heights scaled to the yearly power axis."""
    peak = yearly()["power_mw"].max()
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2017-06-12"),
                "event": "Attention Is All You Need",
                "label": "Attention paper\nJun 2017",
                "label_y": peak * 0.70,
            },
            {
                "date": pd.Timestamp("2022-11-30"),
                "event": "ChatGPT public launch",
                "label": "ChatGPT\nNov 2022",
                "label_y": peak * 0.42,
            },
            {
                "date": pd.Timestamp("2023-03-14"),
                "event": "GPT-4 launch",
                "label": "GPT-4\nMar 2023",
                "label_y": peak * 0.58,
            },
            {
                "date": pd.Timestamp("2025-11-24"),
                "event": "OpenClaw release",
                "label": "OpenClaw\nNov 2025",
                "label_y": peak * 0.82,
            },
        ]
    )


@lru_cache(maxsize=None)
def valid_density() -> pd.DataFrame:
    """Sites with usable power/density/capex, flagged for resource pressure."""
    centers = enriched_centers()
    frame = centers[
        (centers[POWER] > 0)
        & centers["h100_per_mw"].notna()
        & centers[CAPEX].notna()
    ].copy()
    median_density = frame["h100_per_mw"].median()
    median_power = frame[POWER].median()
    frame["resource_pressure"] = frame.apply(
        lambda row: "High power / lower density"
        if row[POWER] >= median_power and row["h100_per_mw"] < median_density
        else "Other sites",
        axis=1,
    )
    return frame


@lru_cache(maxsize=None)
def high_power_low_density() -> pd.DataFrame:
    frame = valid_density()
    return (
        frame[frame["resource_pressure"] == "High power / lower density"]
        .sort_values("h100_per_mw")
        .head(12)
    )


@lru_cache(maxsize=None)
def continent_summary() -> pd.DataFrame:
    centers = enriched_centers()
    summary = (
        centers.groupby("continent", as_index=False)
        .agg(power_mw=(POWER, "sum"), capex_b=(CAPEX, "sum"), sites=("Name", "count"))
        .sort_values("power_mw", ascending=False)
    )
    summary["power_share"] = summary["power_mw"] / centers[POWER].sum()
    return summary


@lru_cache(maxsize=None)
def state_summary() -> pd.DataFrame:
    """U.S. per-state totals, excluding sites whose state could not be inferred."""
    centers = enriched_centers()
    summary = (
        centers[centers["Country"] == "United States"]
        .groupby("state", as_index=False)
        .agg(power_mw=(POWER, "sum"), capex_b=(CAPEX, "sum"), sites=("Name", "count"))
        .sort_values("power_mw", ascending=False)
    )
    summary["power_share"] = summary["power_mw"] / summary["power_mw"].sum()
    return summary[summary["state"] != "Unknown"]


@dataclass(frozen=True)
class Stats:
    """Headline scalars for valueboxes and chart subtitles."""

    sites: int
    total_power: float
    total_capex: float
    top10_power_share: float
    top4_owner_share: float
    median_density: float
    median_power: float
    top_state_power_share: float


@lru_cache(maxsize=None)
def stats() -> Stats:
    centers = enriched_centers()
    total_power = centers[POWER].sum()
    density = valid_density()
    states = state_summary()
    return Stats(
        sites=len(centers),
        total_power=total_power,
        total_capex=centers[CAPEX].sum(),
        top10_power_share=centers.nlargest(10, POWER)[POWER].sum() / total_power,
        top4_owner_share=(
            centers.groupby("owner_clean")[POWER]
            .sum()
            .sort_values(ascending=False)
            .head(4)
            .sum()
            / total_power
        ),
        median_density=density["h100_per_mw"].median(),
        median_power=density[POWER].median(),
        top_state_power_share=(
            states.head(5)["power_mw"].sum() / states["power_mw"].sum()
        ),
    )