from flask import Flask, jsonify
from flask_cors import CORS
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import playercareerstats
import threading
import logging
import time

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# In-memory caches
player_data_cache = {}
player_team_cache = {}

all_teams = nba_teams.get_teams()
all_players = players.get_active_players()

def normalize_stats(stats):
    """
    Extract key stats and convert to per-game values by dividing by GP.
    Returns floats, 0 if GP=0.
    """
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

    # Include GP and GS (games started) as is
    per_game_stats["GP"] = gp
    per_game_stats["GS"] = float(stats.get("GS", 0))

    # Include shooting percentages as-is (not per game)
    per_game_stats["FG_PCT"] = float(stats.get("FG_PCT", 0))
    per_game_stats["FG3_PCT"] = float(stats.get("FG3_PCT", 0))
    per_game_stats["FT_PCT"] = float(stats.get("FT_PCT", 0))

    return per_game_stats

def compute_player_value(per_game_stats, age=None, advanced_stats=None):
    """
    Compute a player's star rating (1 to 5 stars) using:
    - Per-game stats: PTS, REB, AST, STL, BLK, TOV
    - Shooting percentages: FG_PCT, FG3_PCT, FT_PCT
    - Age (optional): penalize older players slightly
    - Advanced stats (optional): e.g. PER, WS/48, BPM if available

    The formula weights these with normalization and scales down the final star rating
    to reduce inflated star counts for average players.

    Returns: int star rating between 1 and 5.
    """

    # Base weighted sum from per-game stats
    base = (
        per_game_stats.get("PTS", 0) * 0.3 +
        per_game_stats.get("REB", 0) * 0.15 +
        per_game_stats.get("AST", 0) * 0.15 +
        per_game_stats.get("STL", 0) * 0.1 +
        per_game_stats.get("BLK", 0) * 0.1 -
        per_game_stats.get("TOV", 0) * 0.15
    )

    # Add shooting percentages with modest weights (scale to 0-1)
    fg_pct = per_game_stats.get("FG_PCT", 0)
    fg3_pct = per_game_stats.get("FG3_PCT", 0)
    ft_pct = per_game_stats.get("FT_PCT", 0)

    shooting_score = (fg_pct * 0.4 + fg3_pct * 0.3 + ft_pct * 0.3) * 5  # Scale to ~0-5

    # Combine base and shooting, weighted
    combined_score = base * 0.7 + shooting_score * 0.3

    # Age adjustment: peak range ~24-29, penalize older players slightly
    if age is not None:
        if age < 24:
            age_factor = 0.95  # Slight penalty for youth/inexperience
        elif 24 <= age <= 29:
            age_factor = 1.0   # Peak
        elif 30 <= age <= 34:
            age_factor = 0.9   # Mild decline
        else:
            age_factor = 0.7   # Significant decline
        combined_score *= age_factor

    # Optional advanced stats adjustment (if advanced_stats dict given)
    # Example keys: 'PER', 'WS/48', 'BPM' - normalize roughly around league average
    if advanced_stats:
        per = advanced_stats.get('PER', 15)  # league avg PER ~15
        ws_per_48 = advanced_stats.get('WS/48', 0.1)  # typical range 0-0.2
        bpm = advanced_stats.get('BPM', 0)  # Box Plus/Minus average ~0

        # Normalize and weight
        adv_score = (
            (per / 20) * 0.5 +       # scale PER max ~20+
            (ws_per_48 / 0.2) * 0.3 +  # scale WS/48 max ~0.2
            (max(bpm, 0) / 10) * 0.2    # scale positive BPM max ~10
        ) * 5  # scale 0-5 roughly

        # Blend with combined_score
        combined_score = combined_score * 0.7 + adv_score * 0.3

    # Final star rating scaled down more strictly
    # Map combined_score to 1-5 stars, with higher thresholds for 4-5 stars
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

        player_name = next((p["full_name"] for p in all_players if p["id"] == player_id), "Unknown")

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
        logging.warning(f"Error fetching stats for player {player_id}: {e}")
        return None
def prefetch_all_players():
    logging.info("Starting background player prefetch...")
    for i, player in enumerate(all_players):
        pid = player["id"]
        if pid in player_data_cache:
            continue
        data = fetch_player_data(pid)
        if data:
            player_data_cache[pid] = data
            abbrev = data["team"]["abbreviation"]
            if abbrev not in player_team_cache:
                player_team_cache[abbrev] = []
            player_team_cache[abbrev].append(data)
        if i % 50 == 0:
            logging.info(f"Prefetched {i} players so far, sleeping 2 seconds to avoid timeout...")
            time.sleep(2)  # pause every 50 players to reduce load
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
    return jsonify({"players": list(player_data_cache.values())})

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

if __name__ == '__main__':
    threading.Thread(target=prefetch_all_players, daemon=True).start()
    app.run(debug=True)
