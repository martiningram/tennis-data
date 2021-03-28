import pandas as pd
import csv
import numpy as np
from os.path import join
from typing import NamedTuple, Optional
from functools import reduce


class Shot(NamedTuple):

    shot_type: Optional[str] = None
    direction: Optional[str] = None
    depth: Optional[str] = None
    outcome: Optional[str] = None
    error_type: Optional[str] = None
    additional: Optional[str] = None
    missed: Optional[str] = None
    penalty: Optional[str] = None
    challenge: Optional[str] = None


def combine_surfaces(df):

    # Surface fixes
    df = df[~df["Surface"].str.contains("Carpet")]
    df["Surface"] = df["Surface"].str.strip()

    df.loc[
        df["Surface"].isin(
            [
                "Hard Court",
                "Hard Indoor",
                "Hard Outdoor",
                "Indoor Hard",
                "Gard",
                "Hardcourt",
            ]
        ),
        "Surface",
    ] = "Hard"

    df.loc[
        df["Surface"].isin(["Indoor Clay", "Court des Princes", "Outdoor Clay"]),
        "Surface",
    ] = "Clay"

    return df


type_lookup = {
    "shot_type": "f,b,r,s,v,z,o,p,u,y,l,m,h,i,j,k,t,q",
    "direction": "1,2,3",
    "error_type": "n,w,d,x,!,e",
    "outcome": "@,#,*",
    "depth": "7,8,9",
    "additional": "+,-,=,;,^",
    "missed": "S,R",
    "penalty": "P,Q",
    "challenge": "C",
}

lookup_lists = {x: y.split(",") for x, y in type_lookup.items()}
char_lookup = [{z: x for z in y} for x, y in lookup_lists.items()]
merged_char_lookup = reduce(lambda x, y: dict(**x, **y), char_lookup, {})


def parse_single_shot(rally_str, shot_dict={}):

    if len(rally_str) == 0:
        try:
            return Shot(**shot_dict), rally_str
        except TypeError:
            import ipdb

            ipdb.set_trace()

    cur_char = rally_str[0]
    cur_type = merged_char_lookup[cur_char]

    if cur_type in shot_dict:
        # We already have this one
        try:
            return Shot(**shot_dict), rally_str
        except TypeError:
            import ipdb

            ipdb.set_trace()

    shot_dict[cur_type] = cur_char
    return parse_single_shot(rally_str[1:], shot_dict)


def parse_rally(rally_str):

    if len(rally_str) == 0:
        return []

    cur_parsed, new_rally_str = parse_single_shot(rally_str, {})

    return [cur_parsed] + parse_rally(new_rally_str)


def parse_outcome(shot):

    lookup = {"#": "forced", "@": "unforced", "*": "winner"}

    return "returned" if shot.outcome is None else lookup[shot.outcome]


def get_chart_df(base_dir, gender="m", drop_challengers=True):

    point_df = pd.read_csv(
        join(base_dir, f"charting-{gender}-points.csv"),
        encoding="ISO-8859-1",
    )

    match_df = pd.read_csv(
        join(base_dir, f"charting-{gender}-matches.csv"),
        encoding="ISO-8859-1",
        quoting=csv.QUOTE_NONE,
    )

    match_df["Date"] = pd.to_datetime(
        match_df["Date"].astype(str), format="%Y%m%d", errors="coerce"
    )

    match_df = match_df.sort_values("Date")

    # Fix surfaces
    match_df = match_df.dropna(subset=["Surface"])
    match_df = combine_surfaces(match_df)

    joined = match_df.merge(point_df, on="match_id")

    winners = joined.groupby("match_id").apply(
        lambda x: x.iloc[-1]["Player 1"]
        if x.iloc[-1]["PtWinner"] == 1
        else x.iloc[-1]["Player 2"]
    )

    losers = joined.groupby("match_id").apply(
        lambda x: x.iloc[-1]["Player 1"]
        if x.iloc[-1]["PtWinner"] == 2
        else x.iloc[-1]["Player 2"]
    )

    match_df = match_df.set_index("match_id")

    match_df.loc[winners.index, "winner"] = winners
    match_df.loc[losers.index, "loser"] = losers

    return match_df, point_df, joined


def create_basic_summary(rally_df):

    rally_df["Rally"] = rally_df["Rally"].fillna("")

    all_rallies = [
        [] if len(x) == 0 else parse_rally(x) for x in rally_df["Rally"].values
    ]

    shot_descriptions = [create_rally_types(x) for x in all_rallies]

    rally_df = rally_df.rename(
        columns={"1stIn": "firstIn", "Player 1": "player_1", "Player 2": "player_2"}
    )

    results = list()

    for i, (cur_row, cur_description) in enumerate(
        zip(rally_df.itertuples(), shot_descriptions)
    ):

        if cur_row.isDouble:
            # Ignore for now
            continue

        is_first = cur_row.firstIn == 1

        cur_description = (
            ["first"] + cur_description if is_first else ["second"] + cur_description
        )

        if cur_row.isRallyWinner or cur_row.isAce or cur_row.isUnret:
            cur_description = cur_description + ["unreturned"]

        n_shots = len(cur_description)

        shot_nums = np.arange(len(cur_description))

        server = cur_row.player_1 if cur_row.Svr == 1 else cur_row.player_2
        returner = cur_row.player_2 if cur_row.Svr == 1 else cur_row.player_1

        if n_shots > 1:
            cur_description[1] = (
                cur_description[1] + ("_first" if is_first else "_second") + "_return"
            )

        is_final_shot = np.repeat(False, n_shots - 1).tolist() + [True]

        cur_surface = cur_row.Surface

        results.append(
            {
                "shot_nums": shot_nums,
                "description": cur_description,
                "server": np.repeat(server, n_shots),
                "returner": np.repeat(returner, n_shots),
                "is_final_shot": is_final_shot,
                "hitter": [server if i % 2 == 0 else returner for i in range(n_shots)],
                "point_num": np.repeat(i, n_shots),
                "surface": np.repeat(cur_surface, n_shots),
                "match_id": np.repeat(cur_row.match_id, n_shots),
            }
        )

    all_together = {x: np.concatenate([y[x] for y in results]) for x in results[0]}

    return pd.DataFrame(all_together)


def create_rally_types(rally_shots):
    def combine_shots(shot_type, direction):

        if shot_type is None:
            shot_type = "?"

        if direction is None:
            direction = "?"

        return shot_type + direction

    return [combine_shots(x.shot_type, x.direction) for x in rally_shots]
