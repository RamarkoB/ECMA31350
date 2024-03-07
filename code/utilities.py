import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

QUARTER_TO_INT = {
    '2015-03-31 00:00:00+00:00': 1,
    '2015-06-30 00:00:00+00:00': 2,
    '2015-09-30 00:00:00+00:00': 3,
    '2015-12-31 00:00:00+00:00': 4,
    '2016-03-31 00:00:00+00:00': 5,
    '2016-06-30 00:00:00+00:00': 6,
    '2016-09-30 00:00:00+00:00': 7,
    '2016-12-31 00:00:00+00:00': 8,
    '2017-03-31 00:00:00+00:00': 9,
    '2017-06-30 00:00:00+00:00': 10,
    '2017-09-30 00:00:00+00:00': 11,
    '2017-12-31 00:00:00+00:00': 12,
}

INT_TO_QUARTER = {
    1: '2015 Q1',
    2: '2015 Q2',
    3: '2015 Q3',
    4: '2015 Q4',
    5: '2016 Q1',
    6: '2016 Q2',
    7: '2016 Q3',
    8: '2016 Q4',
    9: '2017 Q1',
    10: '2017 Q2',
    11: '2017 Q3',
    12: '2017 Q4',
}


def convert_seconds(s, to='hours'):
    if to == 'days':
        return s / 86400
    elif to == 'hours':
        return s / 3600
    elif to == 'minutes':
        return s / 60
    else:
        raise ValueError("Invalid 'to' value")
    

def get_first_treat(repo, treatment):
    repo = repo.replace("/", "--")
    ts_str = treatment[repo]
    
    if ts_str is None:
        return 0

    dt = pd.to_datetime(ts_str)
    keys = list(QUARTER_TO_INT.keys())

    if dt <= pd.to_datetime('2016-03-31'):
        return 5

    for date in keys:
        if dt <= pd.to_datetime(date).tz_localize(None):
            return QUARTER_TO_INT[date]
        
    raise ValueError("Date out of range")


def load_data(treat_func=None, quarter_range=None, outliers=None, level=0.95):
    df = pd.read_csv("../githubData.csv").drop(columns='Unnamed: 0')

    with open('../data/repo-names.json') as f:
        repos = json.load(f)
        repos = [r.replace("--", "/") for r in repos]

    with open('../data/treatment.json') as f:
        treatment = json.load(f)

    df['opened'] = pd.to_datetime(df['opened'])
    df['closed'] = pd.to_datetime(df['closed'])
    df['timetoclose'] = pd.to_timedelta(df['timetoclose'])

    df['ttc_s'] = df['timetoclose'].dt.total_seconds()
    if outliers == "winsor":
        df['ttc_s'] = df['ttc_s'].clip(lower=0, upper=df['ttc_s'].quantile(level))
    elif outliers == "drop":
        df = df[df['ttc_s'] < df['ttc_s'].quantile(level)].copy()

    df['ttc_h'] = df['ttc_s'] / 3600
    df['ttc_d'] = df['ttc_s'] / 86400


    df['repo'] = df['repository_url'].str.replace("https://api.github.com/repos/", "", regex=True).str.lower()
    df['time'] = df['quarter'].map(QUARTER_TO_INT)
    df = df[df['repo'].isin(repos)]

    first_treat_dict = {}
    for repo in repos:
        first_treat_dict[repo] = get_first_treat(repo, treatment)

    df['first_treat'] = df['repo'].map(first_treat_dict)

    if treat_func is None:
        df['treat'] = np.where(df['first_treat'] == 5, 1, 0)
    else:
        df['treat'] = df.apply(treat_func, axis=1)

    if quarter_range is not None:
        df = df[df['time'].isin(quarter_range)]
    else:
        df = df[(df['time'] >= 1) & (df['time'] < 10)]

    return df


def get_y0(gb, repo_name, quarter, outcome):
    try:
        return gb[(gb['repo'] == repo_name) & (gb['time'] == quarter)][outcome].values[0]
    except:
        return np.nan


def create_covs_dict():
    with open("../data/covariates.json") as f:
        covs = json.load(f)

    rv = {}
    for repo_data in covs:
        rv[repo_data['name'].lower()] = repo_data
    
    return rv


def get_repo_stats(covariates, name, stat):
    if name in covariates:
        covs = covariates[name]
        if stat == 'age':
            return (pd.to_datetime("2016-02-17") - pd.to_datetime(covs['created_at']).tz_localize(None)).total_seconds() / 86400
        return covs[stat]
    
    owner, name = name.split("/")
    with (open(f"../data/repos/{owner}--{name}")) as f:
        data = json.load(f)
        if stat == 'age':
            return (pd.to_datetime("2016-02-17") - pd.to_datetime(data['created_at']).tz_localize(None)).total_seconds() / 86400
        elif stat == 'lang':
            return data['language']
        elif stat == 'license':
            return data['license']['name']
        return data[stat]


def get_grouped_df(df, outcome, time_range=None, first_tperiod=5, stats=None):
    agg_dict = {
        'first_treat': 'first', 
        'treat': 'first',
        outcome: 'mean',
    }

    gb = pd.DataFrame(df.groupby(['repo', 'time']).agg(agg_dict)).reset_index()

    repo_to_id = {repo: i + 1 for i, repo in enumerate(gb['repo'].unique())}
    gb['id'] = gb['repo'].map(repo_to_id)
    gb['post'] = np.where(gb['time'] >= first_tperiod, 1, 0)

    if time_range is not None:
        gb = gb[gb['time'].isin(time_range)]
    else:
        time_range = gb['time'].unique()

    for quarter in range(min(time_range), first_tperiod):
        gb[f'y0_{quarter}'] = gb.apply(lambda x: get_y0(gb, x['repo'], quarter, outcome), axis=1)

    # get repo-level statistics
    covs = create_covs_dict()

    if stats is None:
        stats = ['age', 'size', 'watchers', 'lang', 'forks', 'license', 'has_wiki']

    for stat in stats:
        gb[stat] = gb['repo'].map(lambda x: get_repo_stats(covs, x, stat))

    return gb


def mean_gb(gb, outcome, wide=True):
    covs = [col for col in gb.columns if col not in ['repo', 'time', 'post', outcome]]
    agg_dict = {col: 'first' for col in covs}
    agg_dict[outcome] = 'mean'

    agged_gb = pd.DataFrame(gb.groupby(['repo', 'post']).agg(agg_dict)).reset_index()
    
    if not wide:
        return agged_gb
    
    wide_df = agged_gb.pivot(index=['repo'] + covs, columns='post', values=outcome)
    
    pivot_cols = [f"{outcome}{col}" for col in wide_df.columns]
    wide_df.columns = pivot_cols
    wide_df = wide_df.reset_index()

    for col in pivot_cols:
        wide_df = wide_df[~pd.isna(wide_df[col])]
    return wide_df.copy()

# helper function to plot_trends
def plot_with_error_bars(df, color=["b", "orange", "green"]):
    se = df["std"] / df["count"] ** 0.5
    ax = (df["mean"] + 1.96 * se).plot(
        ls="--", color=color, lw=0.5, legend=False
    )

    (df["mean"] - 1.96 * se).plot(
        ax=ax, ls="--", color=color, lw=0.5, legend=False
    )

    df["mean"].plot(ax=ax, color=color, legend=True, marker=".")

    return ax


def plot_trends(df, outcome, ranges=None):
    if ranges:
        df = df[df["time"].isin(ranges)]
    else:
        ranges = df["time"].unique()

    annual_change = (
        df[["time", "treat", outcome]]
        .groupby(["treat", "time"])[outcome]
        .agg(["mean", "std", "count"])
        .unstack(0)
    )

    ax = plot_with_error_bars(annual_change)
    xticks = range(min(ranges), max(ranges) + 1, 2)
    plt.xticks(xticks, [INT_TO_QUARTER[i] for i in xticks])
    sns.despine()
    plt.ylabel(f"Average {outcome}")
    plt.xlabel("Quarter")
    plt.axvline(4.75, color="k", linestyle="--", label="Treatment")
    handles, _ = ax.get_legend_handles_labels()
    plt.legend(
        np.array(handles)[[-1, -2, -3]], ["Treatment", "Treated", "Controls"], frameon=False
    )
    plt.show()