from flask import Flask, jsonify, request
from flask_cors import CORS
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import leaguedashplayerstats, commonplayerinfo, playercareerstats
import logging
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Static
all_teams = nba_teams.get_teams()
all_players = players.get_active_players()

# In-memory cache for team rosters
roster_cache = {}
CACHE_EXPIRY = timedelta(hours=6)

def normalize_stats(row):
    gp = row.get("GP", 1) or 1  # avoid division by zero; default to 1 if missing or zero
    
    return {
        "PLAYER_ID": row.get("PLAYER_ID"),
        "PLAYER_NAME": row.get("PLAYER_NAME"),
        "GP": gp,
        "PTS": round(row.get("PTS", 0) / gp, 1),
        "AST": round(row.get("AST", 0) / gp, 1),
        "REB": round(row.get("REB", 0) / gp, 1),
        "STL": round(row.get("STL", 0) / gp, 1),
        "BLK": round(row.get("BLK", 0) / gp, 1),
        "TOV": round(row.get("TOV", 0) / gp, 1),
        "MIN": round(row.get("MIN", 0) / gp, 1),
        "FG_PCT": round(row.get("FG_PCT", 0), 3),
        "FG3_PCT": round(row.get("FG3_PCT", 0), 3),
        "FT_PCT": round(row.get("FT_PCT", 0), 3),
        "AGE": row.get("AGE", 25),  # default to 25 if not provided
    }

def compute_player_value(per_game_stats, age=None):
    if age is None:
        age = per_game_stats.get("AGE", 25)  # default to 25 if missing

    base = (
        per_game_stats.get("PTS", 0) * 0.3 +
        per_game_stats.get("REB", 0) * 0.15 +
        per_game_stats.get("AST", 0) * 0.15 +
        per_game_stats.get("STL", 0) * 0.1 +
        per_game_stats.get("BLK", 0) * 0.1 -
        per_game_stats.get("TOV", 0) * 0.15
    )
    shooting_score = (
        (per_game_stats.get("FG_PCT", 0) * 0.4 +
         per_game_stats.get("FG3_PCT", 0) * 0.3 +
         per_game_stats.get("FT_PCT", 0) * 0.3) * 5
    )
    combined = base * 0.7 + shooting_score * 0.3

    # Age penalty: after 30 years old, subtract 0.05 points per year
    age_penalty = max(0, (age - 30)) * 0.05
    combined -= age_penalty

    # Adjust thresholds to be harder for top ratings
    if combined < 2.0:
        return 1
    elif combined < 3.5:
        return 2
    elif combined < 5.0:
        return 3
    elif combined < 6.2:
        return 4
    else:
        return 5


def get_team_id_by_abbr(team_abbr):
    team_abbr = team_abbr.upper()
    for team in all_teams:
        if team['abbreviation'].upper() == team_abbr:
            return team['id']
    return None

def fetch_team_roster(team_id, season="2024-25"):
    cache_key = f"{team_id}_{season}"
    now = datetime.utcnow()

    if cache_key in roster_cache:
        players, timestamp = roster_cache[cache_key]
        if now - timestamp < CACHE_EXPIRY:
            return players

    try:
        league_data = leaguedashplayerstats.LeagueDashPlayerStats(season=season)
        df = league_data.get_data_frames()[0]

        # Check and filter for Regular Season only
        if 'SEASON_TYPE' in df.columns:
            df = df[df['SEASON_TYPE'] == 'Regular Season']
        else:
            logging.warning("SEASON_TYPE column not found; unable to filter for Regular Season")

        # Filter by team
        team_players = df[df['TEAM_ID'] == team_id]

        team_players = team_players[team_players['GP'] > 5]

        results = []
        for _, row in team_players.iterrows():
            stats = normalize_stats(row)
            stats["VALUE"] = compute_player_value(stats)
            results.append(stats)

        roster_cache[cache_key] = (results, now)
        return results
    except Exception as e:
        logging.error(f"Failed to fetch team roster: {e}")
        return []

@app.route('/api/rosters/players')
def rosters_players():
    team_abbr = request.args.get('team_abbr')
    season = request.args.get('season', '2024-25')

    if not team_abbr:
        teams_list = [{"abbreviation": t["abbreviation"], "full_name": t["full_name"]} for t in all_teams]
        return jsonify({
            "error": "team_abbr query parameter is required",
            "available_teams": teams_list
        }), 400

    team_id = get_team_id_by_abbr(team_abbr)
    if not team_id:
        return jsonify({"error": f"Team abbreviation {team_abbr} not found"}), 404

    players = fetch_team_roster(team_id, season)
    if not players:
        return jsonify({"error": "No player data found"}), 500

    return jsonify(players)

@app.route('/api/teams', methods=['GET'])
def get_teams():
    try:
        teams_data = []
        for t in all_teams:
            teams_data.append({
                "ID": t.get('id'),
                "ABBREVIATION": t.get('abbreviation'),
                "FULL_NAME": t.get('full_name')
            })
        return jsonify(teams_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

NBA_MOVEMENT_URL = "https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

@app.route('/api/transactions/nba-movement')
def get_nba_player_movement():
    try:
        response = requests.get(NBA_MOVEMENT_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        rows = data.get('NBA_Player_Movement', {}).get('rows', [])
        filtered_rows = [
            row for row in rows
            if row.get('TRANSACTION_DATE') and datetime.fromisoformat(row['TRANSACTION_DATE']).year == 2025
        ]

        return jsonify({
            'NBA_Player_Movement': {
                'columns': data.get('NBA_Player_Movement', {}).get('columns', []),
                'rows': filtered_rows
            }
        })
    except Exception as e:
        logging.error(f"Error fetching NBA player movement data: {e}")
        return jsonify({"error": "Failed to fetch NBA player movement data"}), 500

if __name__ == '__main__':
    app.run(debug=True)
