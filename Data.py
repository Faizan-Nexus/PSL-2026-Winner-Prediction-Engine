import json
import os
import pandas as pd
import re

# --- HELPER 1: Clean Season String ---
def clean_season(season_raw):
    s = str(season_raw).strip()
    if '/' in s:
        year_part = s.split('/')[-1]
        return "20" + year_part if len(year_part) == 2 else year_part
    return s

# --- 2. LOAD THE MASTER DRAFT LOOKUP TABLE ---
print("Loading Master Draft History...")
try:
    draft_df = pd.read_csv('psl_draft_history.csv')
    draft_dict = {}
    
    for _, row in draft_df.iterrows():
        s = str(row['Season']).strip()
        if s not in draft_dict:
            draft_dict[s] = {}
        draft_dict[s][str(row['Player_Name']).strip()] = str(row['Category']).strip()
        
    print("Draft History loaded successfully.")
except FileNotFoundError:
    print("Error: 'psl_draft_history.csv' not found!")
    exit()

# --- HELPER 3: Count Player Categories ---
def get_category_counts(roster_set, season, draft_data):
    counts = {'Platinum': 0, 'Diamond': 0, 'Gold': 0, 'Silver': 0, 'Emerging': 0, 'Supplementary': 0}
    season_draft = draft_data.get(str(season), {})
    
    for player in roster_set:
        if not player: continue
        player_name = str(player).strip() if isinstance(player, list) else str(player).strip()
            
        cat = season_draft.get(player_name, 'Supplementary') 
        if cat == 'Icon': cat = 'Platinum'
        
        if cat in counts: counts[cat] += 1
        else: counts['Supplementary'] += 1
            
    return counts

# --- HELPER 4: SINGLE BALL PROCESSOR ---
def process_ball(delivery, team_stats):
    """Safely increments runs, legal balls, and wickets for a single delivery."""
    runs_data = delivery.get("runs", {})
    extras_data = delivery.get("extras", {})
    
    team_stats["runs"] += runs_data.get("total", 0)
    
    is_wide = "wides" in extras_data
    is_noball = "noballs" in extras_data
    
    # Only count legal deliveries for the Over count
    if not (is_wide or is_noball):
        team_stats["balls"] += 1
        
    # Count Wickets
    w = delivery.get("wickets", [])
    if isinstance(w, list):
        team_stats["wickets"] += len(w)
    elif w:
        team_stats["wickets"] += 1

# --- HELPER 5: Target Runs Extractor ---
def get_target_runs(innings_list):
    for inn in innings_list:
        if not isinstance(inn, dict): continue
        if 'target' in inn:
            return inn['target'].get('runs', 0)
        for key, val in inn.items():
            if isinstance(val, dict) and 'target' in val:
                return val['target'].get('runs', 0)
    return 0 


# --- MAIN JSON EXTRACTION ---
folder_path = 'psl_json'
all_matches = []

print(f"Starting JSON extraction from '{folder_path}'...")

if not os.path.exists(folder_path):
    print(f"Error: Folder '{folder_path}' not found!")
else:
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(folder_path, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print(f"Skipped {filename}: File is empty/corrupted.")
                continue
            except Exception as e:
                print(f"Skipped {filename} due to file read error: {e}")
                continue
                    
            try:
                info = data.get('info', {})
                outcome = info.get('outcome', {})
                event = info.get('event', {})
                innings = data.get('innings', [])
                
                raw_dates_str = str(info.get('dates', ['']))
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', raw_dates_str)
                match_date = date_match.group(0) if date_match else None
                
                season = clean_season(info.get('season', 'Unknown'))
                
                # Setup Base Teams
                teams_list = info.get('teams', ['Team 1', 'Team 2'])
                team1 = str(teams_list).strip() if len(teams_list) > 0 else 'Team 1'
                team2 = str(teams_list).strip() if len(teams_list) > 1 else 'Team 2'

                # Win Logic
                by_dict = outcome.get('by', {})
                if isinstance(by_dict, dict) and len(by_dict) > 0:
                    win_by = str(list(by_dict.keys()))
                    win_margin = list(by_dict.values())
                else:
                    win_by = 'N/A'
                    win_margin = 0

                # Match Stage Logic
                stage = str(event.get('stage', '')).strip()
                match_type = stage.title() if stage else "League"
                
                target_runs = get_target_runs(innings)

                # ==========================================
                # NEW CHRONOLOGICAL INNINGS LOGIC
                # ==========================================
                toss_winner = str(info.get('toss', {}).get('winner', team1)).strip()
                toss_decision = str(info.get('toss', {}).get('decision', 'bat')).strip().lower()
                
                # Determine strictly who bats first and second based on Toss
                if toss_decision == 'bat':
                    inn1_team = toss_winner
                    inn2_team = team2 if toss_winner == team1 else team1
                else: # 'field'
                    inn1_team = team2 if toss_winner == team1 else team1
                    inn2_team = toss_winner

                stats_inn1 = {"runs": 0, "balls": 0, "wickets": 0}
                stats_inn2 = {"runs": 0, "balls": 0, "wickets": 0}

                valid_innings_count = 0
                for inn in innings:
                    if not isinstance(inn, dict): continue
                    
                    inn_data = inn
                    # Dig down if nested
                    if 'overs' not in inn_data and 'deliveries' not in inn_data:
                        for k, v in inn_data.items():
                            if isinstance(v, dict) and ('overs' in v or 'deliveries' in v):
                                inn_data = v
                                break
                    
                    # Ensure it has actionable data
                    if 'overs' not in inn_data and 'deliveries' not in inn_data:
                        continue
                        
                    valid_innings_count += 1
                    
                    # Direct data to the correct tracking variable chronologically
                    active_stats = stats_inn1 if valid_innings_count == 1 else stats_inn2
                    
                    if 'overs' in inn_data:
                        for over in inn_data['overs']:
                            for d in over.get('deliveries', []):
                                process_ball(d, active_stats)
                    elif 'deliveries' in inn_data:
                        for d_wrapper in inn_data['deliveries']:
                            for key, d in d_wrapper.items():
                                process_ball(d, active_stats)

                # Convert balls to Overs & Run Rate
                def finalize_stats(s):
                    b = s["balls"]
                    s["overs"] = (b // 6) + ((b % 6) / 10.0)
                    s["run_rate"] = round(s["runs"] / (b / 6.0), 2) if b > 0 else 0.0
                    return s

                stats_inn1 = finalize_stats(stats_inn1)
                stats_inn2 = finalize_stats(stats_inn2)

                # Map Innings 1 and Innings 2 strictly to Team 1 and Team 2
                if inn1_team == team1:
                    t1_stats = stats_inn1
                    t2_stats = stats_inn2
                else:
                    t1_stats = stats_inn2
                    t2_stats = stats_inn1

                # ==========================================
                # SECURE ROSTER EXTRACTION
                # ==========================================
                rosters = info.get('players', {})
                t1_playing_xi = set(rosters.get(team1, [])) if isinstance(rosters, dict) else set()
                t2_playing_xi = set(rosters.get(team2, [])) if isinstance(rosters, dict) else set()
                
                # Chronological Fallback if missing
                if not t1_playing_xi or not t2_playing_xi:
                    valid_innings_count = 0
                    for inn in innings:
                        if not isinstance(inn, dict): continue
                        inn_data = inn
                        if 'overs' not in inn_data and 'deliveries' not in inn_data:
                            for k, v in inn_data.items():
                                if isinstance(v, dict):
                                    inn_data = v
                                    break
                                    
                        if 'overs' not in inn_data and 'deliveries' not in inn_data:
                            continue
                            
                        valid_innings_count += 1
                        batting_team = inn1_team if valid_innings_count == 1 else inn2_team
                        
                        if batting_team == team1:
                            target_bat_set = t1_playing_xi
                            target_bowl_set = t2_playing_xi
                        else:
                            target_bat_set = t2_playing_xi
                            target_bowl_set = t1_playing_xi
                            
                        if 'overs' in inn_data:
                            for over in inn_data['overs']:
                                for d in over.get('deliveries', []):
                                    if d.get('batter'): target_bat_set.add(d.get('batter'))
                                    if d.get('non_striker'): target_bat_set.add(d.get('non_striker'))
                                    if 'bowler' in d: target_bowl_set.add(d.get('bowler'))
                        elif 'deliveries' in inn_data:
                            for d_wrapper in inn_data['deliveries']:
                                for key, d in d_wrapper.items():
                                    if d.get('batter'): target_bat_set.add(d.get('batter'))
                                    if d.get('non_striker'): target_bat_set.add(d.get('non_striker'))
                                    if 'bowler' in d: target_bowl_set.add(d.get('bowler'))

                t1_cats = get_category_counts(t1_playing_xi, season, draft_dict)
                t2_cats = get_category_counts(t2_playing_xi, season, draft_dict)

                match_details = {
                    'match_id': filename.replace('.json', ''),
                    'season': season,
                    'date': match_date,
                    'match_type': match_type,
                    'venue': str(info.get('venue', 'Unknown')),
                    'team1': team1,
                    'team2': team2,
                    'toss_winner': str(info.get('toss', {}).get('winner', 'Unknown')),
                    'toss_decision': str(info.get('toss', {}).get('decision', 'Unknown')),
                    'winner': str(outcome.get('winner', 'No Result')),
                    'win_by': win_by,
                    'win_margin': int(win_margin) if str(win_margin).isdigit() else win_margin,
                    
                    'target_runs': target_runs,

                    # TEAM 1 STATS
                    'team1_runs': t1_stats['runs'],
                    'team1_overs': t1_stats['overs'],
                    'team1_wickets': t1_stats['wickets'],
                    'team1_run_rate': t1_stats['run_rate'],
                    
                    # TEAM 2 STATS
                    'team2_runs': t2_stats['runs'],
                    'team2_overs': t2_stats['overs'],
                    'team2_wickets': t2_stats['wickets'],
                    'team2_run_rate': t2_stats['run_rate'],
                    
                    # CATEGORY STRENGTH
                    't1_platinum': t1_cats['Platinum'],
                    't1_diamond': t1_cats['Diamond'],
                    't1_gold': t1_cats['Gold'],
                    't1_silver': t1_cats['Silver'],
                    't1_emerging': t1_cats['Emerging'],
                    't1_supplementary': t1_cats['Supplementary'],
                    
                    't2_platinum': t2_cats['Platinum'],
                    't2_diamond': t2_cats['Diamond'],
                    't2_gold': t2_cats['Gold'],
                    't2_silver': t2_cats['Silver'],
                    't2_emerging': t2_cats['Emerging'],
                    't2_supplementary': t2_cats['Supplementary']
                }
                all_matches.append(match_details)
                
            except Exception as e:
                print(f"Skipped {filename} due to parsing error: {e}")

    df = pd.DataFrame(all_matches)
    
    if df.empty:
        print("\n[!] CRITICAL ERROR: The DataFrame is empty. No files were processed.")
        exit()

    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values(by=['season', 'date']).reset_index(drop=True)

    season_finals = df.loc[df.groupby('season')['date'].idxmax()]
    season_winners_dict = dict(zip(season_finals['season'], season_finals['winner']))
    df['season_winner'] = df['season'].map(season_winners_dict)

    output_filename = 'psl_match_summary_master.csv'
    df.to_csv(output_filename, index=False)

    print(f"\nSuccess! Processed {len(df)} matches.")
    print(f"Master dataset securely saved as '{output_filename}'.")