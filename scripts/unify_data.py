#!/usr/bin/env python3
"""
Unified data parser for UMA Team Planner.

This script parses both ratings and reviews raw data files and produces
a single unified final_data.json for the viewer.
"""

import json
import re
import os
import logging

# Import shared utilities
from utils import (
    standardize,
    parse_score,
    split_ignoring_brackets,
    is_category_header,
    VALID_DISTANCES,
    VALID_STYLES,
    DISTANCE_MAPPINGS,
    EMPTY_RATING,
    EMPTY_TRIALS,
    EMPTY_PARENT,
    EMPTY_DEBUFFER,
    logger
)

# =============================================================================
# RATINGS PARSER
# =============================================================================

def parse_rating_line(line, char_name=None, level=None):
    """
    Parse a single rating line (e.g., "4", "2 (Late)", "3 (5 Pace Chaser)").
    
    Args:
        line: Raw rating line
        char_name: Character name for edge case handling
        level: Level name (e.g., "lv3") for edge case handling
        
    Returns:
        Dict with score, style, track_type, special_score, special_style
    """
    result = {
        "score": None,
        "style": None,
        "track_type": None,
        "special_score": None,
        "special_style": None
    }
    
    line = line.strip()
    if not line:
        return result
    
    # Pattern: "2 (5 Pace Chaser)" - special score with style
    special_match = re.search(r'^([\d?+/~\-\s]+)\s*\(([\d?+/~-]+)\s*(.+?)\)$', line)
    if special_match:
        raw_score = special_match.group(1).strip()
        score, _ = parse_score(raw_score, char_name, level)
        result["score"] = score
        
        special_raw = special_match.group(2).strip()
        special_score, _ = parse_score(special_raw)
        result["special_score"] = special_score
        result["special_style"] = standardize(special_match.group(3))
        return result
    
    # Pattern: "2 (Late)" or "4 (Mile)" - score with note
    note_match = re.search(r'^([\d?+/~\-\s]+)\s*\((.+?)\)$', line)
    if note_match:
        raw_score = note_match.group(1).strip()
        score, _ = parse_score(raw_score, char_name, level)
        result["score"] = score
        
        note = note_match.group(2).strip()
        
        # Check if note is a track type or style
        found_track = False
        for tt in VALID_DISTANCES:
            if tt in note:
                result["track_type"] = tt
                found_track = True
                break
        
        if not found_track:
            result["style"] = standardize(note)
        
        return result
    
    # Simple score or complex like "1? 3?"
    raw_score = line
    score, _ = parse_score(raw_score, char_name, level)
    result["score"] = score
    
    return result


def parse_ratings(file_path):
    """
    Parse uma_ratings.txt (or uma_ratings_raw.txt) and return a dict of ratings.
    
    Returns:
        Dict mapping display_name -> {scores, base_name, title, innate_distance, innate_style}
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ratings_map = {}
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    i = 0
    
    while i < len(lines):
        # Skip header lines
        if lines[i] in ["Uma", "Lv 2", "Lv 3", "Lv 4", "Lv 5"]:
            i += 1
            continue
        
        header = lines[i]
        
        # Extract name and optional title
        # Examples: "Agnes Tachyon (Med. | Pace)", "Mayano Top Gun [Wedding] (Med. | Not-Front)"
        name_match = re.match(r'^([^(\n]+)', header)
        if not name_match:
            i += 1
            continue
            
        name_part = name_match.group(1).strip()
        
        # Check for title in brackets: "Name [Title]"
        title = None
        title_match = re.search(r'\[(.*?)\]', name_part)
        if title_match:
            title = title_match.group(1)
            base_name = name_part.replace(f'[{title}]', '').strip()
        else:
            base_name = name_part
        
        # Extract innate info from parentheses: "(Distance | Style)"
        innate_distances = []
        innate_styles = []
        innate_match = re.search(r'\(([^)]*\|[^)]*)\)', header)
        if innate_match:
            innate_content = innate_match.group(1)
            parts = [p.strip() for p in innate_content.split('|')]
            
            if len(parts) >= 1:
                for d in parts[0].split('/'):
                    std_d = standardize(d.strip())
                    if std_d:
                        innate_distances.append(std_d)
            
            if len(parts) >= 2:
                for s in parts[1].split('/'):
                    std_s = standardize(s.strip())
                    if std_s:
                        innate_styles.append(std_s)
        
        # Parse next 4 lines as awakening scores
        scores = {}
        if i + 1 < len(lines) and (lines[i+1][0].isdigit() or '?' in lines[i+1]):
            for j, level in enumerate(["lv2", "lv3", "lv4", "lv5"]):
                if i + 1 + j < len(lines):
                    scores[level] = parse_rating_line(lines[i + 1 + j], base_name, level)
            
            ratings_map[name_part] = {
                "scores": scores,
                "base_name": base_name,
                "title": title,
                "innate_distance": innate_distances,
                "innate_style": innate_styles
            }
            i += 5
        else:
            i += 1
    
    logger.info(f"Parsed {len(ratings_map)} entries from ratings")
    return ratings_map


# =============================================================================
# REVIEWS PARSER
# =============================================================================

def parse_reviews(file_path):
    """
    Parse uma_reviews.txt (or uma_reviews_raw.txt) and return a list of reviews.
    
    Returns:
        List of review dicts with name, base_name, variant, description, ratings
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    review_data = []
    current_ura = None
    description_lines = []
    lines = content.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        
        # Handle empty lines - save description
        if not line_stripped:
            if current_ura and description_lines:
                current_ura["description"] = '\n\n'.join(description_lines)
                description_lines = []
            continue
        
        # Skip ratings lines for header matching
        if line_stripped.startswith('Ratings:'):
            name_match = None
        else:
            # Match character headers: "Name (Variant)" or "Name [Variant]"
            name_match = re.match(r'^([^()\[\]]+)\s*(\(([^)]+)\)|\[([^\]]+)\])$', line_stripped)
        
        if name_match:
            name = name_match.group(1).strip()
            variant = (name_match.group(3) or name_match.group(4)).strip()
            
            # Skip category headers
            if name in ["1*", "2*", "3*", "This Month's"] or is_category_header(name):
                continue
            
            # Save previous character's description before creating new one
            if current_ura and description_lines:
                current_ura["description"] = '\n\n'.join(description_lines)
                description_lines = []
            
            # Determine display name and variant
            if variant in ["1*", "2*", "3*"]:
                display_name = name
                variant_label = "Original"
            elif variant == "Original":
                display_name = name
                variant_label = "Original"
            else:
                display_name = f"{name} [{variant}]"
                variant_label = variant
            
            current_ura = {
                "name": display_name,
                "base_name": name,
                "variant": variant_label,
                "description": None,
                "ratings": {
                    "style": [],
                    "team_trials": {"score": None, "distance": None, "style": None},
                    "parent": None,
                    "debuffer": {"type": None, "effect": None, "note": None}
                }
            }
            review_data.append(current_ura)
            continue
        
        # Parse ratings line
        if line_stripped.startswith('Ratings:') and current_ura:
            ratings_content = line_stripped.replace('Ratings:', '').strip()
            
            for part in split_ignoring_brackets(ratings_content):
                # Extract scores from the part
                scores_found = re.findall(r'(\d[\d?+~-]*\??)', part)
                score = scores_found[-1] if scores_found else None
                
                # Normalize score using parse_score
                if score:
                    normalized_score, _ = parse_score(score, current_ura["base_name"])
                    score = normalized_score
                
                # Extract note in parentheses
                note_match = re.search(r'\((.+?)\)', part)
                note = note_match.group(1) if note_match else None
                
                # Categorize the rating
                if "Debuffer" in part:
                    type_match = re.search(r'(\w+)\s+Debuffer', part)
                    current_ura["ratings"]["debuffer"]["type"] = type_match.group(1) if type_match else None
                    if note and ',' in note:
                        parts = note.split(',', 1)
                        current_ura["ratings"]["debuffer"]["effect"] = parts[0].strip()
                        current_ura["ratings"]["debuffer"]["note"] = parts[1].strip()
                    else:
                        current_ura["ratings"]["debuffer"]["effect"] = note
                        current_ura["ratings"]["debuffer"]["note"] = None
                
                elif "Parent" in part:
                    # Normalize parent score
                    if score and "~" in score:
                        score = score.split("~")[0]
                    current_ura["ratings"]["parent"] = {"score": score, "note": note}
                
                elif "Stadium" in part:
                    # Extract distance/style hints from Stadium notes (e.g., "Stadium 5 (Dirt Late Surger)")
                    # We don't store Stadium score but use it to infer innate distance
                    if note:
                        for d in VALID_DISTANCES:
                            if d in note:
                                if "stadium_hints" not in current_ura["ratings"]:
                                    current_ura["ratings"]["stadium_hints"] = {"distances": [], "styles": []}
                                if d not in current_ura["ratings"]["stadium_hints"]["distances"]:
                                    current_ura["ratings"]["stadium_hints"]["distances"].append(d)
                        # Also capture style hints
                        for s in VALID_STYLES:
                            if s in note:
                                if "stadium_hints" not in current_ura["ratings"]:
                                    current_ura["ratings"]["stadium_hints"] = {"distances": [], "styles": []}
                                if s not in current_ura["ratings"]["stadium_hints"]["styles"]:
                                    current_ura["ratings"]["stadium_hints"]["styles"].append(s)
                    continue
                
                elif "Team Trials" in part:
                    # Parse Team Trials ratings
                    matches = re.finditer(r'(\d[\d?+~-]*)\s*(?:\(([^)]+)\))?', part.replace("Team Trials", ""))
                    
                    found_scores = []
                    found_styles = []
                    found_distances = []
                    
                    for m in matches:
                        s_val = m.group(1).strip()
                        n_val = m.group(2).strip() if m.group(2) else ""
                        
                        # Normalize score
                        s_val, _ = parse_score(s_val, current_ura["base_name"], "trials")
                        
                        dist = None
                        sty = None
                        
                        if n_val:
                            # Find ALL distances in the note (check both canonical and abbreviations)
                            note_distances = []
                            remaining = n_val
                            
                            # First check canonical distances
                            for d in VALID_DISTANCES:
                                if d in remaining:
                                    note_distances.append(d)
                                    remaining = re.sub(rf'\b{d}\b', '', remaining)
                            
                            # Then check distance abbreviations (Mid, Med, Med.)
                            for abbrev, canonical in DISTANCE_MAPPINGS.items():
                                if abbrev in remaining:
                                    note_distances.append(canonical)
                                    remaining = re.sub(rf'\b{re.escape(abbrev)}\b', '', remaining)
                            
                            # Clean up remaining text
                            remaining = remaining.strip().strip('/')
                            
                            # Set dist as compound if multiple distances
                            if note_distances:
                                dist = '/'.join(note_distances)
                            
                            # Check remaining text for style
                            if '/' in remaining:
                                potential_styles = []
                                for p in remaining.split('/'):
                                    std_p = standardize(p.strip())
                                    if std_p:
                                        potential_styles.append(std_p)
                                if potential_styles:
                                    sty = '/'.join(potential_styles)
                            else:
                                for s in VALID_STYLES:
                                    if s in remaining:
                                        sty = s
                                        break
                                if not sty and remaining:
                                    sty = standardize(remaining)
                        
                        found_scores.append(s_val)
                        if dist:
                            found_distances.append(standardize(dist))
                        if sty:
                            found_styles.append(sty)
                    
                    # Join multiple values
                    final_score = " / ".join(found_scores) if found_scores else score
                    final_distance = " / ".join(list(set(found_distances))) if found_distances else None
                    final_style = " / ".join(list(set(found_styles))) if found_styles else None
                    
                    current_ura["ratings"]["team_trials"] = {
                        "score": final_score,
                        "distance": final_distance,
                        "style": final_style
                    }
                
                else:
                    # Style rating (e.g., "Pace Chaser 4 (Sprint)")
                    for subpart in [s.strip() for s in part.split('/')]:
                        if not subpart:
                            continue
                        clean_subpart = re.sub(r'\(.+?\)', '', subpart).strip()
                        style_type_match = re.search(r'^([^\d(]+)', clean_subpart)
                        if style_type_match:
                            style_type = standardize(style_type_match.group(1).strip())
                            current_ura["ratings"]["style"].append({
                                "type": style_type,
                                "score": score,
                                "distance": standardize(note)
                            })
                        else:
                            current_ura["ratings"]["style"].append({
                                "type": standardize(subpart),
                                "score": score,
                                "distance": standardize(note)
                            })
            
            # Set default team_trials style from highest-scored style rating
            # Priority for ties: End Closer > Late Surger = Pace Chaser > Front Runner
            if current_ura["ratings"]["team_trials"]["style"] is None and current_ura["ratings"]["style"]:
                style_priority = {
                    "End Closer": 4,
                    "Late Surger": 3,
                    "Pace Chaser": 3,
                    "Front Runner": 2
                }
                
                # Get all styles with their numeric scores
                style_scores = []
                for sr in current_ura["ratings"]["style"]:
                    try:
                        numeric_score = int(str(sr["score"]).strip().replace("?", "").replace("+", "")[0])
                    except (ValueError, IndexError):
                        numeric_score = 0
                    style_scores.append((sr["type"], numeric_score))
                
                if style_scores:
                    # Find max score
                    max_score = max(s[1] for s in style_scores)
                    
                    # Filter to styles with max score
                    top_styles = [s[0] for s in style_scores if s[1] == max_score]
                    
                    if len(top_styles) == 1:
                        current_ura["ratings"]["team_trials"]["style"] = top_styles[0]
                    else:
                        # Apply priority to break ties
                        top_styles_with_priority = [(s, style_priority.get(s, 0)) for s in top_styles]
                        max_priority = max(p[1] for p in top_styles_with_priority)
                        
                        # Get all styles with max priority (could still be ties like Late/Pace)
                        final_styles = [s[0] for s in top_styles_with_priority if s[1] == max_priority]
                        
                        # Join with "/" if still tied, otherwise use the single winner
                        current_ura["ratings"]["team_trials"]["style"] = "/".join(final_styles)
            continue
        
        # Description lines
        if current_ura:
            # Skip category headers from descriptions
            if is_category_header(line_stripped):
                continue
            description_lines.append(line_stripped)
    
    # Save last character's description
    if current_ura and description_lines:
        current_ura["description"] = '\n\n'.join(description_lines)
    
    logger.info(f"Parsed {len(review_data)} entries from reviews")
    return review_data


# =============================================================================
# UNIFICATION
# =============================================================================

def match_review_to_rating(review, base_name, title):
    """
    Check if a review matches a rating entry.
    
    Args:
        review: Review dict
        base_name: Base name from ratings
        title: Title/variant from ratings (may be None)
        
    Returns:
        True if match, False otherwise
    """
    if review["base_name"] != base_name:
        return False
    
    if title:
        # Match title to variant
        if review["variant"] == title:
            return True
        # Handle anime variant synonyms
        if title == "End of Sky" and review["variant"] == "Anime":
            return True
        if title == "Beyond the Horizon" and review["variant"] == "Anime":
            return True
        return False
    else:
        # No title means Original
        return review["variant"] in ["Original", "1*", "2*", "3*"]


def unify():
    """Main unification function."""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    VIEWER_DIR = os.path.join(BASE_DIR, 'viewer')
    
    ratings_file = os.path.join(DATA_DIR, 'uma_ratings.txt')
    reviews_file = os.path.join(DATA_DIR, 'uma_reviews.txt')
    output_file = os.path.join(VIEWER_DIR, 'final_data.json')
    
    # Parse both sources
    ratings_map = parse_ratings(ratings_file)
    reviews_list = parse_reviews(reviews_file)
    
    final_data_map = {}
    
    # Process ratings first (they have awakening scores)
    for display_name, data in ratings_map.items():
        base_name = data["base_name"]
        title = data["title"]
        levels = data["scores"]
        
        # Find matching review
        matched_review = None
        for review in reviews_list:
            if match_review_to_rating(review, base_name, title):
                matched_review = review
                break
        
        # Determine variant
        variant = title if title else (matched_review["variant"] if matched_review else "Original")
        if variant in ["3*", "1*", "2*"]:
            variant = "Original"
        
        final_data_map[display_name] = {
            "name": display_name,
            "base_name": base_name,
            "variant": variant,
            "description": matched_review["description"] if matched_review else None,
            "innate_distance": data["innate_distance"],
            "innate_style": data["innate_style"],
            "lv2": levels.get("lv2", EMPTY_RATING.copy()),
            "lv3": levels.get("lv3", EMPTY_RATING.copy()),
            "lv4": levels.get("lv4", EMPTY_RATING.copy()),
            "lv5": levels.get("lv5", EMPTY_RATING.copy()),
            "trials": matched_review["ratings"]["team_trials"] if matched_review else EMPTY_TRIALS.copy(),
            "parent": matched_review["ratings"]["parent"] if matched_review else EMPTY_PARENT.copy(),
            "debuffer": matched_review["ratings"]["debuffer"] if matched_review else EMPTY_DEBUFFER.copy(),
            "style_reviews": matched_review["ratings"]["style"] if matched_review else []
        }
    
    # Add reviews that weren't matched to ratings
    for review in reviews_list:
        d_name = review["name"]
        found = False
        
        for existing in final_data_map.values():
            if existing["name"] == d_name:
                found = True
                break
            
            # Check for variant equivalence
            if existing["base_name"] == review["base_name"]:
                e_var = existing["variant"]
                r_var = review["variant"]
                
                # Original/Star equivalents
                if r_var in ["1*", "2*", "3*", "Original"] and e_var in ["1*", "2*", "3*", "Original"]:
                    found = True
                elif r_var == e_var:
                    found = True
                # Anime synonyms
                elif e_var == "End of Sky" and r_var == "Anime":
                    found = True
                elif e_var == "Beyond the Horizon" and r_var == "Anime":
                    found = True
                
                if found:
                    break
        
        if not found:
            v_label = review["variant"]
            if v_label in ["1*", "2*", "3*"]:
                v_label = "Original"
            
            # Extract stadium hints for distance/style backfill
            stadium_hints = review["ratings"].get("stadium_hints", {"distances": [], "styles": []})
            
            final_data_map[d_name] = {
                "name": d_name,
                "base_name": review["base_name"],
                "variant": v_label,
                "description": review["description"],
                "innate_distance": stadium_hints.get("distances", []).copy(),
                "innate_style": stadium_hints.get("styles", []).copy(),
                "lv2": EMPTY_RATING.copy(),
                "lv3": EMPTY_RATING.copy(),
                "lv4": EMPTY_RATING.copy(),
                "lv5": EMPTY_RATING.copy(),
                "trials": review["ratings"]["team_trials"],
                "parent": review["ratings"]["parent"],
                "debuffer": review["ratings"]["debuffer"],
                "style_reviews": review["ratings"]["style"]
            }
    
    # Backfill innate distance/styles from review context
    for item in final_data_map.values():
        # ALWAYS backfill from style_reviews if innate_style is empty
        # (this is critical for characters only in reviews source)
        if not item["innate_style"]:
            # First, add from trials style
            if item["trials"]["style"]:
                styles_to_add = item["trials"]["style"].split('/')
                for s in styles_to_add:
                    s = s.strip()
                    if s and s not in item["innate_style"]:
                        item["innate_style"].append(s)
            
            # Then add from style_reviews
            for sr in item["style_reviews"]:
                if sr["type"] and sr["type"] not in item["innate_style"]:
                    item["innate_style"].append(sr["type"])
                # Also check if distance is embedded in style_reviews
                if sr.get("distance") and not item["innate_distance"]:
                    for d in VALID_DISTANCES:
                        if d in str(sr["distance"]) and d not in item["innate_distance"]:
                            item["innate_distance"].append(d)
        
        # ALWAYS backfill from trials if innate_distance is empty
        if not item["innate_distance"]:
            if item["trials"]["distance"]:
                dists = item["trials"]["distance"].split('/')
                for d in dists:
                    d = d.strip()
                    if d and d not in item["innate_distance"]:
                        item["innate_distance"].append(d)
        
        # Additional backfill from description if available
        if item["description"]:
            # Search description for distances
            if not item["innate_distance"]:
                for d in VALID_DISTANCES:
                    if re.search(rf'\b{d}\b', item["description"], re.I) and d not in item["innate_distance"]:
                        item["innate_distance"].append(d)
            
            # Search description for styles
            if not item["innate_style"]:
                style_keywords = {
                    "Front Runner": "Front Runner",
                    "Runner": "Front Runner",
                    "Pace Chaser": "Pace Chaser",
                    "Chaser": "Pace Chaser",
                    "Late Surger": "Late Surger",
                    "Betweener": "Late Surger",
                    "End Closer": "End Closer",
                    "Closer": "End Closer"
                }
                for key, val in style_keywords.items():
                    if re.search(rf'\b{key}\b', item["description"], re.I) and val not in item["innate_style"]:
                        item["innate_style"].append(val)
    
    # Clean up descriptions
    for item in final_data_map.values():
        if item["description"]:
            item["description"] = re.sub(r"This Month's Reviews", '', item["description"], flags=re.I)
            item["description"] = re.sub(r"This Month\'s Reviews", '', item["description"], flags=re.I)
            item["description"] = item["description"].strip()
    
    # Special case fixes (these should now be handled during parsing, but keep as safety net)
    for item in final_data_map.values():
        display_name = item["name"]
        
        # Mejiro McQueen End of Sky - ensure Pace Chaser style
        if "End of Sky" in display_name:
            if "Pace Chaser" not in item["innate_style"]:
                item["innate_style"].append("Pace Chaser")
    
    # Sort alphabetically by name
    final_list = sorted(final_data_map.values(), key=lambda x: x["name"])
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=4, sort_keys=False)
    
    logger.info(f"Successfully generated {output_file} ({len(final_list)} characters)")
    print(f"Successfully generated {output_file} ({len(final_list)} characters)")


if __name__ == "__main__":
    unify()
