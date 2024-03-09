import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

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
    

def get_first_treat(repo_id, treatment):
    # repo = repo.replace("/", "--")
    ts_str = treatment[repo_id]
    
    if ts_str is None:
        return 0

    dt = pd.to_datetime(ts_str)
    treat_time = dt.quarter + (dt.year - 2015) * 4

    if treat_time <= 5:
        return 5
    elif treat_time > 12:
        return 0
    return treat_time


def load_data(quarter_range=None, outliers=None, level=0.95,
              filename='../data/issue-history/issue-history-all.csv'):
    if filename == "../githubData.csv":
        df = pd.read_csv(filename).drop(columns=['Unnamed: 0', 'quarter'])
    else:
        df = pd.read_csv(filename)

    repo_ids = []

    with open("../covariates/all-covariates.json") as f:
        repo_ids.extend([repo['id'] for repo in json.load(f)])

    with open('../data/treatment-all.json') as f:
        treatment = {int(k): v for k, v in json.load(f).items()}

    repo_ids = set(repo_ids).intersection(set(treatment.keys()))
    df = df[df['repo_id'].isin(repo_ids)]
    df['opened'] = pd.to_datetime(df['opened']).dt.tz_localize(None)
    df['closed'] = pd.to_datetime(df['closed']).dt.tz_localize(None)
    df['time'] = df['opened'].dt.quarter + (df['opened'].dt.year - 2015) * 4

    if 'timetoclose' in df.columns:
        df['timetoclose'] = pd.to_timedelta(df['timetoclose'])
    else:
        df['timetoclose'] = df['closed'] - df['opened']

    df['ttc_s'] = df['timetoclose'].dt.total_seconds()

    if quarter_range is not None:
        df = df[df['time'].isin(quarter_range)]
    else:
        df = df[(df['time'] >= 1) & (df['time'] < 10)]

    if outliers == "winsor":
        print(f"droppping at level: {convert_seconds(df['ttc_s'].quantile(level), to='days')}")
        df['ttc_s'] = df['ttc_s'].clip(lower=0, upper=df['ttc_s'].quantile(level))
    elif outliers == "drop":
        print(f"droppping at level: {convert_seconds(df['ttc_s'].quantile(level), to='days')}")
        df = df[df['ttc_s'] < df['ttc_s'].quantile(level)].copy()

    df['ttc_h'] = df['ttc_s'] / 3600
    df['ttc_d'] = df['ttc_s'] / 86400

    if filename == "../githubData.csv":
        df['repo_name'] = df['repository_url'].str.replace("https://api.github.com/repos/", "", regex=True).str.lower()
    else:
        df['repo_name'] = df['name'].str.lower()

    first_treat_dict = {}
    for repo_id in repo_ids:
        first_treat_dict[repo_id] = get_first_treat(repo_id, treatment)

    df['first_treat'] = df['repo_id'].map(first_treat_dict)
    df['treat'] = np.where(df['first_treat'] == 5, 1, 0)

    ## clean out repos with low sample size
    gb_repo_time = (df[df['time'].isin([3, 4, 5, 6, 7])]
                    .groupby(['repo_id', 'time'])['ttc_d']
                    .count()
                    .reset_index())
    low_sample_ids = gb_repo_time[gb_repo_time['ttc_d'] < 10]['repo_id'].unique()

    gb_repo = df.groupby(['repo_id']).agg({"time": set})
    repo_times_dict = gb_repo.to_dict()['time']
    no_time_ids = [k for k, v in repo_times_dict.items() if not set([4, 5, 6]) <= (v)]
    drop_ids = list(low_sample_ids) + no_time_ids
    print(f"dropping {len(drop_ids)} repos due to low sample size during treatment timeframe")

    return df[~df['repo_id'].isin(drop_ids)]


def get_y0(gb, repo_name, quarter, outcome):
    try:
        return gb[(gb['repo_id'] == repo_name) & (gb['time'] == quarter)][outcome].values[0]
    except:
        return np.nan


def create_covs_dict():
    cov_dict = {}
    with open("../covariates/all-covariates.json") as f:
        for data in json.load(f):
            cov_dict[data['id']] = data
    
    return cov_dict


def get_repo_stats(covariates, name, stat):
    # if name in covariates:
    covs = covariates[name]
    if stat == 'age':
        return (pd.to_datetime("2016-02-17") - pd.to_datetime(covs['created_at']).tz_localize(None)).total_seconds() / 86400
    if stat == 'has_wiki':
        try:
            return covs['has_wiki']
        except:
            return covs['hasWiki']
        
    return covs[stat]


def get_grouped_df(df, outcome, time_range=None, first_tperiod=5, stats=None, 
                   agg_func='mean'):
    agg_dict = {
        'first_treat': 'first', 
        'treat': 'first',
        outcome: [agg_func, 'count'],
    }

    gb = pd.DataFrame(df.groupby(['repo_id', 'time']).agg(agg_dict)).reset_index()
    gb.columns = [x[0] for x in list(gb.columns)[:-1]] + ['count']

    repo_to_id = {repo: i + 1 for i, repo in enumerate(gb['repo_id'].unique())}
    gb['id'] = gb['repo_id'].map(repo_to_id)
    gb['post'] = np.where(gb['time'] >= first_tperiod, 1, 0)

    if time_range is not None:
        gb = gb[gb['time'].isin(time_range)]
    else:
        time_range = gb['time'].unique()

    for quarter in range(min(time_range), first_tperiod):
        gb[f'y0_{quarter}'] = gb.apply(lambda x: get_y0(gb, x['repo_id'], quarter, outcome), axis=1)

    # get repo-level statistics
    covs = create_covs_dict()

    if stats is None:
        stats = ['age', 'size', 'watchers', 'forks', 'has_wiki']

    for stat in stats:
        gb[stat] = gb['repo_id'].map(lambda x: get_repo_stats(covs, x, stat))

    return gb


def mean_gb(gb, outcome, wide=True):
    covs = [col for col in gb.columns if col not in 
            ['repo_id', 'time', 'post', outcome, 'count']]
    agg_dict = {col: 'first' for col in covs}
    agg_dict[outcome] = 'mean'

    agged_gb = pd.DataFrame(gb.groupby(['repo_id', 'post']).agg(agg_dict)).reset_index()
    
    if not wide:
        return agged_gb
    
    wide_df = agged_gb.pivot(index=['repo_id'] + covs, columns='post', values=outcome)
    
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
        np.array(handles)[[-1, -2, -3]], ["Treatment", "Treated", "Controls"], 
        frameon=False,
        loc="upper left"
    )
    plt.show()
