from flask import Flask, jsonify
from flask_cors import CORS
from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import playercareerstats
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# League average shooting percentages
league_avg_fg = 0.465
league_avg_3p = 0.355
league_avg_ft = 0.78

def compute_player_value(stats):
    if not stats:
        return 0
    try:
        gp = float(stats.get("GP", 0))
        if gp == 0:
            return 0

        # Per-game stats
        points = float(stats.get("PTS", 0)) / gp
        rebounds = float(stats.get("REB", 0)) / gp
        assists = float(stats.get("AST", 0)) / gp
        steals = float(stats.get("STL", 0)) / gp
        blocks = float(stats.get("BLK", 0)) / gp
        turnovers = float(stats.get("TOV", 0)) / gp
        fg_pct = float(stats.get("FG_PCT", 0))
        threep_pct = float(stats.get("FG3_PCT", 0))
        ft_pct = float(stats.get("FT_PCT", 0))

        # Advanced stats (if available)
        ts_pct = float(stats.get("TS_PCT", 0))
        ws_per_48 = float(stats.get("WS_PER_48", 0))
        bpm = float(stats.get("BPM", 0))
        vorp = float(stats.get("VORP", 0))
        age = float(stats.get("PLAYER_AGE", 28))  # Default to 28 if not available

        score = (
            points * 0.35 +
            rebounds * 0.15 +
            assists * 0.2 +
            steals * 0.25 +
            blocks * 0.2 -
            turnovers * 0.15 +
            (fg_pct - league_avg_fg) * 100 * 0.4 +
            (threep_pct - league_avg_3p) * 100 * 0.3 +
            (ft_pct - league_avg_ft) * 100 * 0.2 +
            ts_pct * 10 +
            ws_per_48 * 100 +
            bpm * 1.5 +
            vorp * 2
            +6 # Minimum = 1 Star (6/30)
        )

        # Nonlinear age adjustment
        if age < 24:
            score *= 1 + (24 - age) * 0.03
        elif age > 30:
            score *= 1 - (age - 30) * 0.025

        max_score = 30
        star_rating = max(0, min(5, (score / max_score) * 5))
        return round(star_rating, 1)
    except Exception as e:
        logging.error(f"Error computing player value: {e}")
        return 0

def normalize_stats(stats):
    if not stats:
        return {}
    normalized = {}
    gp = float(stats.get("GP", 0))
    for k, v in stats.items():
        if isinstance(v, (int, float)) and gp > 0 and k in ["PTS", "REB", "AST", "STL", "BLK", "TO"]:
            normalized[k] = round(v / gp, 1)
        elif isinstance(v, (int, float)):
            normalized[k] = round(v, 1)
        else:
            normalized[k] = v
    return normalized


@app.route('/api/players')
def get_all_players():
    try:
        active_players = nba_players.get_active_players()
        players_data = []

        for i, player in enumerate(active_players):
            if i >= 5:
                break

            player_id = player['id']
            player_name = player['full_name']
            team_id = player.get('team_id')
            team_abbreviation = player.get('team_abbreviation', 'N/A')

            try:
                career_df = playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[0]
                if not career_df.empty:
                    last_season_stats = career_df.iloc[-1].fillna(0).to_dict()
                    if float(last_season_stats.get("GP", 0)) == 0:
                        continue
                    last_season_stats["PLAYER_AGE"] = float(last_season_stats.get("PLAYER_AGE", 28))
                else:
                    continue
            except Exception as e:
                logging.warning(f"Failed to fetch stats for player {player_name} (ID: {player_id}): {e}")
                continue

            per_game_stats = normalize_stats(last_season_stats)
            star_value = compute_player_value(last_season_stats)

            players_data.append({
                "id": player_id,
                "name": player_name,
                "team": {
                    "id": team_id,
                    "abbreviation": team_abbreviation
                },
                "last_season_stats": per_game_stats,
                "star_value": star_value
            })

        logging.info(f"Returning {len(players_data)} active players with games played")
        return jsonify({"players": players_data})

    except Exception as e:
        logging.error(f"Error fetching all players: {e}")
        return jsonify({"detail": f"Error fetching players: {str(e)}"}), 500

@app.route('/api/player/<name>')
def get_player_by_name(name):
    try:
        all_players = nba_players.get_active_players()
        matched = next((p for p in all_players if p['full_name'].lower() == name.lower()), None)

        if not matched:
            return jsonify({"detail": f"No active player found with name '{name}'"}), 404

        player_id = matched['id']
        player_name = matched['full_name']
        team_id = matched.get('team_id')
        team_abbreviation = matched.get('team_abbreviation', 'N/A')

        career_df = playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[0]
        if not career_df.empty:
            last_season_stats = career_df.iloc[-1].fillna(0).to_dict()
            last_season_stats["PLAYER_AGE"] = float(last_season_stats.get("PLAYER_AGE", 28))
        else:
            last_season_stats = {}

        per_game_stats = normalize_stats(last_season_stats)
        star_value = compute_player_value(last_season_stats)

        return jsonify({
            "id": player_id,
            "name": player_name,
            "team": {
                "id": team_id,
                "abbreviation": team_abbreviation
            },
            "last_season_stats": per_game_stats,
            "star_value": star_value
        })

    except Exception as e:
        logging.error(f"Error fetching player '{name}': {e}")
        return jsonify({"detail": f"Error fetching player: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
