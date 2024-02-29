import re
from bs4 import BeautifulSoup
import csv

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

def parse_team(team: str):
    with open(f'html_data/{team}.html', 'r') as f: content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Find all the repeating rows with the relevant data
    tbody = soup.find('tbody')
    player_rows = tbody.find_all('tr')

    out = open(f'parsed_data/{team}.csv', 'w')
    writer = csv.writer(out)

    header = ['name', 'team', 'position', 'contract_start', 'contract_end',
              'free_agent', 'signed_age', 'years', 'value', 'signing_bonus']
    writer.writerow(header)

    for row in player_rows:
        data_cells = row.find_all('td')

        # Extract the data from each cell
        name = data_cells[1].find('a', class_="team-name").text.strip()
        position = data_cells[1].find('div', class_="rank-position").text.split("|")[0].strip()
        contract_years = data_cells[1].find_all('div', class_='rank-position')[1].text.strip()
        signed_age = row['data-age-signed']
        years = data_cells[3].text.strip()
        value = data_cells[4].text.strip()[1:].replace(",", "")
        # avg_annual_value = data_cells[5].text.strip()
        signing_bonus = "".join(data_cells[6].text.strip()[1:].split(","))

        # Create a dictionary to consolidate the player information
        player_info = [
            name,
            team,
            position, 
            re.split('-| ', contract_years)[0],
            re.split('-| |\)', contract_years)[1],
            re.split('-| |\)', contract_years)[3],
            signed_age,
            years,
            value,
            signing_bonus
        ]

        # Print or store the extracted data 
        writer.writerow(player_info)

    out.close()

if __name__ == '__main__':
    for team in team_values:
        print(f"Processing {team}")
        parse_team(team)