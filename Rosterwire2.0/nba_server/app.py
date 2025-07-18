from flask import Flask, jsonify
from flask_cors import CORS
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import playercareerstats
import threading
import logging
import time
import requests

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# In-memory caches
player_data_cache = {}
player_team_cache = {}

all_teams = nba_teams.get_teams()
all_players = players.get_active_players()

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

def fetch_player_data(player_id, max_retries=3):
    if player_id in player_data_cache:
        logging.info(f"Cache hit for player ID {player_id}")
        return player_data_cache[player_id]

    player_name = next((p["full_name"] for p in all_players if p["id"] == player_id), f"ID {player_id}")

    retries = 0
    backoff = 1  # start 1 sec
    while retries < max_retries:
        try:
            career_df = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=5).get_data_frames()[0]
            if career_df.empty:
                logging.info(f"No career data for {player_name} (ID {player_id}), caching None")
                player_data_cache[player_id] = None
                return None

            last_season = career_df.iloc[-1].fillna(0).to_dict()
            gp = float(last_season.get("GP", 0))
            if gp == 0:
                logging.info(f"{player_name} (ID {player_id}) has zero games played last season, caching None")
                player_data_cache[player_id] = None
                return None

            team_abbr = last_season.get("TEAM_ABBREVIATION", "")
            if not team_abbr:
                logging.info(f"{player_name} (ID {player_id}) has no team abbreviation, caching None")
                player_data_cache[player_id] = None
                return None

            per_game_stats = normalize_stats(last_season)
            star_value = compute_player_value(per_game_stats)

            data = {
                "id": player_id,
                "name": player_name,
                "team": {
                    "id": last_season.get("TEAM_ID", -1),
                    "abbreviation": team_abbr.upper()
                },
                "last_season_stats": per_game_stats,
                "star_value": star_value
            }

            player_data_cache[player_id] = data
            logging.info(f"Cached data for player {player_name} (ID {player_id}) successfully")
            return data

        except requests.exceptions.ReadTimeout:
            retries += 1
            logging.warning(f"Read timeout for {player_name} (ID {player_id}), retry {retries}/{max_retries} after {backoff}s...")
            time.sleep(backoff)
            backoff *= 2
        except Exception as e:
            logging.warning(f"Error fetching stats for {player_name} (ID {player_id}): {e}, caching None")
            player_data_cache[player_id] = None
            return None

    logging.warning(f"Failed to fetch data for {player_name} (ID {player_id}) after {max_retries} retries, caching None")
    player_data_cache[player_id] = None
    return None

def prefetch_all_players():
    logging.info("Starting background player prefetch...")
    consecutive_failures = 0
    for i, player in enumerate(all_players):
        pid = player["id"]
        if pid in player_data_cache:
            continue

        data = fetch_player_data(pid)
        if data:
            consecutive_failures = 0
            abbrev = data["team"]["abbreviation"]
            if abbrev not in player_team_cache:
                player_team_cache[abbrev] = []
            if all(p['id'] != data['id'] for p in player_team_cache[abbrev]):
                player_team_cache[abbrev].append(data)
        else:
            consecutive_failures += 1
            logging.warning(f"Consecutive failures: {consecutive_failures}")
            if consecutive_failures >= 3:
                logging.warning("Too many failures, sleeping 30 seconds to cool down...")
                time.sleep(30)  # this sleep fully blocks here
                consecutive_failures = 0

        if i > 0 and i % 25 == 0:
            logging.info(f"Prefetched {i} players so far, sleeping 12 seconds to avoid timeout...")
            time.sleep(12)
    logging.info("Finished background prefetch.")

@app.route('/api/players')
def get_all_players():
    if not player_data_cache:
        logging.info("Cache empty, fetching players live (slow)...")
        results = []
        for player in all_players:
            data = fetch_player_data(player["id"])
            if data:
                results.append(data)
        return jsonify({"players": results})
    return jsonify({"players": [p for p in player_data_cache.values() if p is not None]})

@app.route('/api/players/team/<team_abbr>')
def get_players_by_team(team_abbr):
    team_abbr = team_abbr.upper()
    if team_abbr in player_team_cache:
        return jsonify({"players": player_team_cache[team_abbr]})

    logging.info(f"Cache miss for team {team_abbr}, fetching live...")
    filtered_players = []

    for player in all_players:
        data = fetch_player_data(player["id"])
        if not data:
            continue
        if data["team"]["abbreviation"] != team_abbr:
            continue
        if all(p['id'] != data['id'] for p in filtered_players):
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
        "cached_players_count": len([p for p in player_data_cache.values() if p is not None]),
        "cached_teams": list(player_team_cache.keys())
    })

if __name__ == '__main__':
    threading.Thread(target=prefetch_all_players, daemon=True).start()
    app.run(debug=True)
