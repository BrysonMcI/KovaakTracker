######
# Reads kovaaks challenge stats and graphs progression and improvement
# Author: Bryson M.
######

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

import pandas as pd
import plotly.graph_objs as go
import numpy as np

import os
import time


############# STATS PARSING CODE #############

STATS_DIRECTORY = "D:\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\stats"

def parse_stats_file(file_path):
    # Returns a row containing:
    # score (from bottom of file)
    # kills (from bottom of file)
    # damage done (from weapon line)
    # shots
    # hits
    # accuracy (calculated)
    # avg ttk per kill
    # avg ttk between kills (calculated from top)
    # efficiency (from top)
    df = pd.DataFrame(columns = ["score", "kills", "damage", "shots", "hits", "accuracy", "ttk_per", "ttk_between", "efficiency"])
    df.loc[len(df)] = [0] * len(df.columns)
    weapon_stats_next = False
    in_kill_list = False
    kill_list_frame = pd.DataFrame(columns = ["timestamp", "TTK", "shots" , "hits", "accuracy", "damage_done", "damage_possible", "efficiency"])
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if in_kill_list:
                line = line.split(",")
                if len(line) < 11:
                    if not kill_list_frame.empty:
                        df.at[0, "ttk_per"] = kill_list_frame["TTK"].mean()
                        df.at[0, "efficiency"] = kill_list_frame["efficiency"].mean()
                        try:
                            kill_times = pd.to_datetime(kill_list_frame["timestamp"], format="%H:%M:%S:%f")
                        except ValueError:
                            kill_times = pd.to_datetime(kill_list_frame["timestamp"], format="%H:%M:%S.%f")
                        df.at[0, "ttk_between"] = kill_times.diff().mean()
                    in_kill_list = False
                else:
                    kill_list_frame.at[line[0]] = line[1], float(line[4][:-1]), float(line[5]), float(line[6]), float(line[7]), float(line[8]), float(line[9]), float(line[10])
            elif weapon_stats_next:
                weapon_stats_next = False
                line = line.split(",")
                df.at[0, "shots"] = float(line[1])
                df.at[0, "hits"] = float(line[2])
                df.at[0, "accuracy"] = float(line[2])/float(line[1])
            elif line == "Kill #,Timestamp,Bot,Weapon,TTK,Shots,Hits,Accuracy,Damage Done,Damage Possible,Efficiency,Cheated":
                in_kill_list = True
            elif line == "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale":
                weapon_stats_next = True
            elif line.startswith("Score:,"):
                df.at[0, "score"] = float(line[len("Score:,"):])
            elif line.startswith("Kills:,"):
                df.at[0, "kills"] = float(line[len("Kills:,"):])
            elif line.startswith("Damage Done:,"):
                df.at[0, "damage"] = float(line[len("Damage Done:,"):])

    return df

def parse_filename(filename):
    # Returns the values from the below filename format
    # name_of_challenge - mode - date Stats
    filename = filename[:-len("Stats.csv")] # Drop the end
    filename = filename.split("-")
    return filename[0].strip(), filename[-2].strip(), filename[-1].strip()

def parse_stats_folder():
    # Returns a DF name,date,stats
    directory = os.fsencode(STATS_DIRECTORY)
    stats = pd.DataFrame(columns = ["challenge", "timestamp", "score", "kills", "damage", "shots", "hits", "accuracy", "ttk_per", "ttk_between", "efficiency"])
    i = 0
    for f in os.listdir(directory):
        filename = os.fsdecode(f)
        if filename.endswith(".csv"):
            chal, date, time = parse_filename(filename)
            chal_stats = parse_stats_file(os.path.join(directory, filename.encode("UTF-8")).decode("UTF-8"))
            stats = stats.append(pd.DataFrame([[chal, date + "-" + time] + chal_stats.to_numpy().tolist()[0]], columns = ["challenge", "timestamp", "score", "kills", "damage", "shots", "hits", "accuracy", "ttk_per", "ttk_between", "efficiency"]))
            i += 1
        #if i > 60:
        #    break

    stats["timestamp"] = pd.to_datetime(stats["timestamp"], format="%Y.%m.%d-%H.%M.%S")
    stats = stats.set_index(["challenge", "timestamp"])
    stats = stats.sort_index()
    return stats

############# DASH CODE #############

def normalize_by_group(df, by):
    groups = df.groupby(by)
    # computes group-wise min max normal,
    # then auto broadcasts to size of group chunk
    minimum = groups.min()
    maximum = groups.max()
    return (df)/(maximum)

def setup_dashboard(app, stats):
    # Setup stats
    stats = normalize_by_group(stats, "challenge")
    stats = stats.multiply(100)
    stats = stats.groupby(["challenge", pd.Grouper(level="timestamp", freq="1d")]).mean()

    traces = []
    for name, chal in stats.groupby("challenge"):
        array = chal["score"].droplevel(0).reset_index().to_numpy().transpose()
        traces.append(
            go.Scatter(
                x=array[0],
                y=array[1],
                mode="lines+markers",
                name=name
            )
        )
        

    # Create layout
    app.layout = html.Div(children=[
        html.H1(children="Kovaak's Stats Visualization"),
        dcc.Graph(
            id="example-graph",
            figure={
                "data": traces,
                "layout": go.Layout(title=go.layout.Title(text="Avg Diff from Highscore per Day"))
            }
        )
    ])

def main():
    print("Parsing stats folder...")
    start = time.time()
    stats = parse_stats_folder()
    end = time.time()
    print("Parsed in {}s".format(round(end-start, 2)))
    print("Creating Dashboard...")
    app = dash.Dash(__name__)
    server = app.server
    setup_dashboard(app, stats)
    print("Running Server...")
    app.run_server()


if __name__ == "__main__":
    main()