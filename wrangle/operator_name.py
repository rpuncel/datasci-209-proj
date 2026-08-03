"""Fill in missing ``operator_name`` values in the FracTracker data center database.

FracTracker's ``operator_name`` column is blank for roughly 45% of rows. Rather
than guess in one pass, each tier below is a separate, low-risk inference step:

1. :func:`fill_from_duplicate_facility_names` reuses an operator already on
   record for the same ``facility_name`` elsewhere in the dataset.
2. :func:`fill_from_facility_name_suffix` strips a trailing "Data Center(s)"
   phrase off the facility name when what's left isn't a place name.
3. :func:`fill_from_known_companies` matches a curated list of recognizable
   company names embedded in longer facility strings (e.g. "AWS Rockfish 1").

Facility names that are project codenames ("Project Tango"), developer/
landholder names, or site/subdivision names ("Regency HOA area") are
deliberately left untouched — they need real per-row research, not a
heuristic guess. Run :func:`fill_missing_operator_names` to apply all three
tiers and record which rows were touched via ``operator_name_source``.
"""

import re

import pandas as pd

# Facility-name values that are data-entry placeholders, not real names, and
# so must never be trusted as a stand-in for an operator's brand.
_GENERIC_FACILITY_NAMES = {
    "data center",
    "datacenter",
    "data centre",
    "colocation data center",
    "confidential",
    "unnamed",
    "tbd",
}

# Matches a trailing "Data Center"/"Data Centers"/"Datacenter"/"Data Centre".
_SUFFIX_PATTERN = re.compile(
    r"\s*(data\s*center(s)?|datacenter(s)?|data\s*centre(s)?)\s*$", re.IGNORECASE
)

# Words that show up in place names, roads, and geographic features rather
# than in company names — used to reject false-positive "brand" candidates.
_ROAD_OR_PLACE_PATTERN = re.compile(
    r"\b(rd|road|st|street|ave|avenue|blvd|boulevard|hwy|highway|dr|drive|ln|lane|"
    r"way|pkwy|parkway|twp|township|county|creek|hills|valley|springs|ridge|"
    r"route|pike|trail|loop)\b",
    re.IGNORECASE,
)

# Recognizable, verifiable company names that appear embedded in facility_name
# strings that don't cleanly match the "<Company> Data Center" pattern (e.g.
# "AWS Rockfish 1", "QTS- Fort Worth-Dallas", "Project Sharka: Google Data
# Center"). Longest names are matched first so "Digital Realty" wins over a
# bare "Realty" partial match, etc.
KNOWN_COMPANIES = [
    "CoreWeave", "Bitfarms", "Riot Platforms", "Applied Digital", "DataBank",
    "EdgeCore", "NJFX", "xAI", "QTS", "AWS", "Comcast", "Experian", "Citicorp",
    "Northern Data", "Simple Mining", "Compass", "DC Blox", "Nautilus",
    "Fluidstack", "Lancium", "AVAIO", "Telehouse", "Global AI", "CoreSite",
    "Digital Realty", "Iron Mountain", "Microsoft", "Google", "Amazon",
    "Meta", "Apple", "Oracle", "IBM",
]
_KNOWN_COMPANIES_BY_LENGTH = sorted(KNOWN_COMPANIES, key=len, reverse=True)


def _is_missing(series: pd.Series) -> pd.Series:
    """True where a free-text column is null or blank."""
    return series.isna() | (series.astype(str).str.strip() == "")


def _is_generic_facility_name(name) -> bool:
    return str(name).strip().lower() in _GENERIC_FACILITY_NAMES


def _strip_data_center_suffix(name) -> str:
    return _SUFFIX_PATTERN.sub("", str(name)).strip()


def _looks_like_place(candidate_name: str, city, county=None) -> bool:
    """True if a candidate operator name is really a city, county, or road."""
    candidate = candidate_name.strip().lower()
    city_parts = [part.strip() for part in str(city).lower().split(",")]
    if candidate in city_parts:
        return True
    if county and pd.notna(county) and candidate in str(county).lower():
        return True
    return bool(_ROAD_OR_PLACE_PATTERN.search(candidate_name))


def _find_known_company(name) -> str | None:
    for company in _KNOWN_COMPANIES_BY_LENGTH:
        if re.search(r"\b" + re.escape(company) + r"\b", str(name), re.IGNORECASE):
            return company
    return None


def fill_from_duplicate_facility_names(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill ``operator_name`` from other rows sharing the same facility_name.

    Only fills when every non-missing ``operator_name`` recorded under that
    facility_name elsewhere in the dataset agrees, and skips generic
    placeholder names (e.g. "Data center") that appear across many unrelated
    facilities and would otherwise cause false matches.
    """
    df = df.copy()
    missing = _is_missing(df["operator_name"])
    non_generic = ~df["facility_name"].map(_is_generic_facility_name)

    known = df[~missing & non_generic]
    operator_counts = known.groupby("facility_name")["operator_name"].nunique()
    consistent_names = operator_counts[operator_counts == 1].index
    lookup = (
        known[known["facility_name"].isin(consistent_names)]
        .groupby("facility_name")["operator_name"]
        .first()
    )

    fillable = missing & non_generic
    df.loc[fillable, "operator_name"] = df.loc[fillable, "operator_name"].fillna(
        df.loc[fillable, "facility_name"].map(lookup)
    )
    return df


def fill_from_facility_name_suffix(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill ``operator_name`` by stripping a trailing "Data Center" phrase.

    Only applies where the facility_name actually ends in that phrase and the
    remaining text doesn't look like a place, road, or county name (e.g.
    "Fort Meade Data Center" is left alone; "Brightspeed Data Center" becomes
    "Brightspeed").
    """
    df = df.copy()
    missing = _is_missing(df["operator_name"])
    has_suffix = df["facility_name"].map(
        lambda name: bool(_SUFFIX_PATTERN.search(str(name)))
    )
    candidate = df["facility_name"].map(_strip_data_center_suffix)

    place_like = pd.Series(
        [
            _looks_like_place(cand, city, county)
            for cand, city, county in zip(
                candidate, df["city"], df.get("county", pd.Series([None] * len(df)))
            )
        ],
        index=df.index,
    )

    fillable = missing & has_suffix & (candidate != "") & ~place_like
    df.loc[fillable, "operator_name"] = candidate[fillable]
    return df


def fill_from_known_companies(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill ``operator_name`` when facility_name embeds a known company.

    Handles facility names that don't fit the "<Company> Data Center" pattern,
    such as "AWS Rockfish 1", "QTS- Fort Worth-Dallas", or
    "Project Sharka: Google Data Center".
    """
    df = df.copy()
    missing = _is_missing(df["operator_name"])
    candidate = df["facility_name"].map(_find_known_company)
    fillable = missing & candidate.notna()
    df.loc[fillable, "operator_name"] = candidate[fillable]
    return df


def tag_operator_name_source(df: pd.DataFrame, original: pd.Series) -> pd.DataFrame:
    """Record whether operator_name was reported by FracTracker or inferred.

    ``original`` should be the ``operator_name`` column *before* any of the
    fill_from_* steps ran, so this must be called with that snapshot alongside
    the fully-filled frame.
    """
    df = df.copy()
    df["operator_name_source"] = "original"
    df.loc[_is_missing(original), "operator_name_source"] = "inferred"
    df.loc[
        _is_missing(original) & _is_missing(df["operator_name"]),
        "operator_name_source",
    ] = "missing"
    return df


def fill_missing_operator_names(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all operator_name inference tiers and tag each row's source.

    Roughly 45% of FracTracker rows arrive with no operator_name. This fills
    what can be inferred with reasonable confidence (about half of those) and
    tags the rest as ``"missing"`` in ``operator_name_source`` rather than
    guessing — project codenames, developer/landholder names, and site or
    subdivision names still need real research.
    """
    original = df["operator_name"].copy()
    result = (
        df.pipe(fill_from_manual_research)
        .pipe(fill_from_duplicate_facility_names)
        .pipe(fill_from_facility_name_suffix)
        .pipe(fill_from_known_companies)
    )
    return tag_operator_name_source(result, original)


# Rows resolved by hand via web research, keyed by (facility_name, city,
# state) since a facility_name alone can recur across unrelated sites (e.g.
# "Aligned" appears in several states). Add an entry here once a row's
# operator has been confirmed against a citable source, and note the source
# in a comment so the finding can be re-verified later.
RESEARCHED_OPERATORS: dict[tuple[str, str, str], str] = {
    # DCD: "Real estate developer Vintage Partners has decided to cancel its
    # plans for a data center in the Laveen area of Phoenix, Arizona."
    # Project was scrapped before any distinct operator was ever named.
    ("Vintage Partners", "Laveen, Phoenix", "AZ"): "Vintage Partners",
    # baxtel.com/data-center/aligned-phoenix: "Aligned Data Centers is an
    # infrastructure technology company..." — this is Aligned's PHX-01 campus.
    ("Aligned", "Phoenix", "AZ"): "Aligned Data Centers",
    # expedient.com/data-centers/phoenix: 2475 W Townley Ave, Phoenix, AZ
    # 85021 is Expedient's "PHX1" facility.
    ("PHX1", "Phoenix", "AZ"): "Expedient",
}


def fill_from_manual_research(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill ``operator_name`` from :data:`RESEARCHED_OPERATORS` lookups.

    Distinct from the heuristic tiers below: every entry here was confirmed
    against a citable source during a manual research pass, rather than
    inferred from the facility_name string itself.
    """
    df = df.copy()
    missing = _is_missing(df["operator_name"])
    # FracTracker facility_name values sometimes carry stray trailing
    # whitespace (e.g. "Vintage Partners "), so strip before matching.
    key = list(
        zip(
            df["facility_name"].str.strip(),
            df["city"].str.strip(),
            df["state"].str.strip(),
        )
    )
    candidate = pd.Series(
        [RESEARCHED_OPERATORS.get(k) for k in key], index=df.index
    )
    fillable = missing & candidate.notna()
    df.loc[fillable, "operator_name"] = candidate[fillable]
    return df
