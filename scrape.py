import requests

team_values = [
    "arizona-diamondbacks", "atlanta-braves", "baltimore-orioles", "boston-red-sox", 
    "chicago-cubs", "chicago-white-sox", "cincinnati-reds", "cleveland-guardians", 
    "colorado-rockies", "detroit-tigers", "houston-astros", "kansas-city-royals", 
    "los-angeles-angels", "los-angeles-dodgers", "miami-marlins", "milwaukee-brewers", 
    "minnesota-twins", "new-york-mets", "new-york-yankees", "oakland-athletics", 
    "philadelphia-phillies", "pittsburgh-pirates", "san-diego-padres", "san-francisco-giants", 
    "seattle-mariners", "st-louis-cardinals", "tampa-bay-rays", "texas-rangers", 
    "toronto-blue-jays", "washington-nationals"
]

for team in team_values:
    print(team)
    out = open(f'{team}.html', 'w')
    r = requests.get(f'https://www.spotrac.com/mlb/contracts/sort-value/{team}/all-time/limit-7000/')
    if (r.ok): out.write(r.text)
    else: out.write('ERROR')