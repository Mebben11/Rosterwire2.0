from flask import Flask, jsonify
from flask_cors import CORS
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import playercareerstats
import threading
import logging
import time
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# In-memory caches
player_data_cache = {}
player_team_cache = {}

all_teams = nba_teams.get_teams()
all_players = players.get_active_players()

# ... [normalize_stats, compute_player_value, fetch_player_data, fetch_player_data_with_one_retry, prefetch_all_players as before, just updated timing] ...

def normalize_stats(stats):
    gp = float(stats.get("GP", 0))
    keys_to_normalize = ["PTS", "AST", "REB", "STL", "BLK", "TOV", "MIN"]
    per_game_stats = {}

    for key in keys_to_normalize:
        raw_val = stats.get(key, 0)
        try:
            val = float(raw_val)
        except:
            val = 0
        per_game_stats[key] = round(val / gp, 1) if gp > 0 else 0.0

    per_game_stats["GP"] = gp
    per_game_stats["GS"] = float(stats.get("GS", 0))
    per_game_stats["FG_PCT"] = float(stats.get("FG_PCT", 0))
    per_game_stats["FG3_PCT"] = float(stats.get("FG3_PCT", 0))
    per_game_stats["FT_PCT"] = float(stats.get("FT_PCT", 0))

    return per_game_stats

def compute_player_value(per_game_stats, age=None, advanced_stats=None):
    base = (
        per_game_stats.get("PTS", 0) * 0.3 +
        per_game_stats.get("REB", 0) * 0.15 +
        per_game_stats.get("AST", 0) * 0.15 +
        per_game_stats.get("STL", 0) * 0.1 +
        per_game_stats.get("BLK", 0) * 0.1 -
        per_game_stats.get("TOV", 0) * 0.15
    )

    fg_pct = per_game_stats.get("FG_PCT", 0)
    fg3_pct = per_game_stats.get("FG3_PCT", 0)
    ft_pct = per_game_stats.get("FT_PCT", 0)

    shooting_score = (fg_pct * 0.4 + fg3_pct * 0.3 + ft_pct * 0.3) * 5
    combined_score = base * 0.7 + shooting_score * 0.3

    if age is not None:
        if age < 24:
            age_factor = 0.95
        elif 24 <= age <= 29:
            age_factor = 1.0
        elif 30 <= age <= 34:
            age_factor = 0.9
        else:
            age_factor = 0.7
        combined_score *= age_factor

    if advanced_stats:
        per = advanced_stats.get('PER', 15)
        ws_per_48 = advanced_stats.get('WS/48', 0.1)
        bpm = advanced_stats.get('BPM', 0)

        adv_score = (
            (per / 20) * 0.5 +
            (ws_per_48 / 0.2) * 0.3 +
            (max(bpm, 0) / 10) * 0.2
        ) * 5

        combined_score = combined_score * 0.7 + adv_score * 0.3

    if combined_score < 1.5:
        star = 1
    elif combined_score < 2.5:
        star = 2
    elif combined_score < 3.5:
        star = 3
    elif combined_score < 4.2:
        star = 4
    else:
        star = 5

    return star

def fetch_player_data(player_id):
    player_name = next((p["full_name"] for p in all_players if p["id"] == player_id), f"ID {player_id}")
    try:
        career_df = playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[0]
        if career_df.empty:
            return None

        last_season = career_df.iloc[-1].fillna(0).to_dict()
        gp = float(last_season.get("GP", 0))
        if gp == 0:
            return None

        team_abbr = last_season.get("TEAM_ABBREVIATION", "")
        if not team_abbr:
            return None

        per_game_stats = normalize_stats(last_season)
        star_value = compute_player_value(per_game_stats)

        return {
            "id": player_id,
            "name": player_name,
            "team": {
                "id": last_season.get("TEAM_ID", -1),
                "abbreviation": team_abbr.upper()
            },
            "last_season_stats": per_game_stats,
            "star_value": star_value
        }
    except Exception as e:
        logging.warning(f"Error fetching stats for {player_name}: {e}")
        return None

def fetch_player_data_with_one_retry(player_id):
    data = fetch_player_data(player_id)
    if data:
        logging.info(f"Successfully fetched data for player {player_id}")
        return data
    else:
        logging.warning(f"Initial fetch failed for player {player_id}, retrying once after 5s...")
        time.sleep(5)
        data = fetch_player_data(player_id)
        if data:
            logging.info(f"Successfully fetched data for player {player_id} on retry")
            return data
        else:
            logging.warning(f"Failed to fetch data for player {player_id} after retry")
            return None

def prefetch_all_players():
    logging.info("Starting background player prefetch...")
    consecutive_failures = 0

    for i, player in enumerate(all_players, start=1):
        pid = player["id"]
        if pid in player_data_cache:
            continue

        data = fetch_player_data_with_one_retry(pid)
        if data:
            player_data_cache[pid] = data
            abbrev = data["team"]["abbreviation"]
            if abbrev not in player_team_cache:
                player_team_cache[abbrev] = []
            player_team_cache[abbrev].append(data)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            logging.warning(f"Consecutive failures: {consecutive_failures}, sleeping 15 seconds before continuing.")
            time.sleep(15)

        if i % 25 == 0:
            logging.info(f"Prefetched {i} players, sleeping 30 seconds to avoid API rate limits...")
            time.sleep(30)

    logging.info("Finished background prefetch.")

@app.route('/api/players')
def get_all_players():
    if not player_data_cache:
        logging.info("Cache empty, fetching players live (slow)...")
        results = []
        for player in all_players:
            data = fetch_player_data_with_one_retry(player["id"])
            if data:
                results.append(data)
        return jsonify({"players": results})
    return jsonify({"players": list(player_data_cache.values())})

@app.route('/api/players/team/<team_abbr>')
def get_players_by_team(team_abbr):
    team_abbr = team_abbr.upper()
    if team_abbr in player_team_cache:
        return jsonify({"players": player_team_cache[team_abbr]})

    logging.info(f"Cache miss for team {team_abbr}, fetching live...")
    filtered_players = []

    for player in all_players:
        data = fetch_player_data_with_one_retry(player["id"])
        if not data:
            continue
        if data["team"]["abbreviation"] != team_abbr:
            continue
        filtered_players.append(data)

    return jsonify({"players": filtered_players})

@app.route('/api/teams')
def get_teams():
    try:
        teams_data = [{
            "id": t["id"],
            "abbreviation": t["abbreviation"],
            "full_name": t["full_name"]
        } for t in all_teams]
        return jsonify({"teams": teams_data})
    except Exception as e:
        logging.error(f"Error fetching teams: {e}")
        return jsonify({"detail": f"Error fetching teams: {str(e)}"}), 500

@app.route('/api/status')
def get_cache_status():
    return jsonify({
        "cached_players_count": len(player_data_cache),
        "cached_teams": list(player_team_cache.keys())
    })

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

from datetime import datetime

@app.route('/api/transactions/nba-movement')
def get_nba_player_movement():
    try:
        response = requests.get(NBA_MOVEMENT_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        rows = data.get('NBA_Player_Movement', {}).get('rows', [])

        # Filter for 2025 only
        filtered_rows = [
            row for row in rows
            if row.get('TRANSACTION_DATE') and datetime.fromisoformat(row['TRANSACTION_DATE']).year == 2025
        ]

        # Return filtered data under same structure, but only filtered rows
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
    threading.Thread(target=prefetch_all_players, daemon=True).start()
    app.run(debug=True)
