#!/usr/bin/env python3
"""
Data Audit Script for UMA Team Planner

This script validates final_data.json against the raw datasets and identifies
any data discrepancies or parsing issues.
"""

import json
import re
import os
from collections import defaultdict

# Constants
VALID_DISTANCES = {"Sprint", "Mile", "Medium", "Long", "Dirt"}
VALID_STYLES = {"Front Runner", "Pace Chaser", "Late Surger", "End Closer"}
VALID_SCORE_PATTERN = re.compile(r'^[1-5]$')
UNCERTAIN_SCORE_PATTERN = re.compile(r'[\?~+]')

class AuditReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = {}
    
    def add_error(self, message):
        self.errors.append(message)
    
    def add_warning(self, message):
        self.warnings.append(message)
    
    def add_info(self, message):
        self.info.append(message)
    
    def print_report(self):
        print("\n" + "=" * 60)
        print("DATA AUDIT REPORT")
        print("=" * 60)
        
        # Summary Statistics
        print("\n--- SUMMARY STATISTICS ---")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
        
        # Errors
        print(f"\n--- ERRORS ({len(self.errors)}) ---")
        if self.errors:
            for error in self.errors:
                print(f"  [ERROR] {error}")
        else:
            print("  None")
        
        # Warnings
        print(f"\n--- WARNINGS ({len(self.warnings)}) ---")
        if self.warnings:
            for warning in self.warnings:
                print(f"  [WARN] {warning}")
        else:
            print("  None")
        
        # Info
        print(f"\n--- INFO ({len(self.info)}) ---")
        if self.info:
            for info in self.info:
                print(f"  [INFO] {info}")
        else:
            print("  None")
        
        print("\n" + "=" * 60)
        print(f"Total: {len(self.errors)} errors, {len(self.warnings)} warnings, {len(self.info)} info")
        print("=" * 60 + "\n")


def load_json(file_path):
    """Load JSON file and return data."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_text_file(file_path):
    """Load text file and return lines."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_names_from_ratings_raw(content):
    """Extract character names from uma_ratings_raw.txt."""
    names = []
    lines = content.strip().split('\n')
    
    # Pattern to match character header lines: Name (Distance | Style)
    # Must have both parentheses and pipe to be a valid header
    header_pattern = re.compile(r'^([^(\n]+)\s*\([^|]+\|[^)]+\)')
    
    for line in lines:
        line = line.strip()
        if not line or line in ["Uma", "Lv 2", "Lv 3", "Lv 4", "Lv 5"]:
            continue
        
        # Skip lines that are just numbers (scores)
        if re.match(r'^[\d?+~\-\s()a-zA-Z.]+$', line) and '|' not in line and '(' not in line:
            continue
        
        match = header_pattern.match(line)
        if match:
            name = match.group(1).strip()
            # Additional validation: name should not be just a number
            if not re.match(r'^\d+$', name):
                names.append(name)
    
    return names


def extract_names_from_reviews_raw(content):
    """Extract character names from uma_reviews_raw.txt."""
    names = []
    lines = content.strip().split('\n')
    
    # Pattern to match character header lines (Name (Variant) or Name [Variant])
    header_pattern = re.compile(r'^([^()\[\]]+)\s*(\(([^)]+)\)|\[([^\]]+)\])$')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Ratings:'):
            continue
        
        match = header_pattern.match(line)
        if match:
            name = match.group(1).strip()
            variant = (match.group(3) or match.group(4) or "").strip()
            
            # Skip category headers
            if name in ["1*", "2*", "3*", "This Month's"] or "Umas" in name or "Reviews" in name:
                continue
            
            full_name = name
            if variant and variant not in ["Original", "1*", "2*", "3*"]:
                full_name = f"{name} [{variant}]"
            
            names.append({"name": name, "variant": variant, "full_name": full_name})
    
    return names


def validate_score(score, field_name, char_name, report):
    """Validate a score value and add issues to report."""
    if score is None:
        return  # Null scores are handled separately
    
    score_str = str(score).strip()
    
    # Check for uncertain scores
    if UNCERTAIN_SCORE_PATTERN.search(score_str):
        report.add_warning(f"{char_name}: Uncertain score '{score_str}' in {field_name}")
        return
    
    # Check for special annotations like "4 but bad"
    if "but" in score_str.lower():
        report.add_warning(f"{char_name}: Special annotation '{score_str}' in {field_name}")
        return
    
    # Check if it's a valid numeric score
    if not VALID_SCORE_PATTERN.match(score_str):
        # It might be a compound like "4 / 3"
        if "/" in score_str:
            report.add_info(f"{char_name}: Compound score '{score_str}' in {field_name}")
        else:
            report.add_warning(f"{char_name}: Non-standard score '{score_str}' in {field_name}")


def validate_distance(distance, char_name, report):
    """Validate a distance value."""
    if distance is None:
        return
    
    if isinstance(distance, list):
        for d in distance:
            validate_distance(d, char_name, report)
        return
    
    distance_str = str(distance).strip()
    
    # Check for non-standard values
    non_standard = {
        "Med.": "Medium",
        "Med": "Medium",
        "Mid": "Medium"
    }
    
    if distance_str in non_standard:
        report.add_warning(f"{char_name}: Non-standard distance '{distance_str}' should be '{non_standard[distance_str]}'")
    elif distance_str not in VALID_DISTANCES:
        # Could be compound like "Medium/Long"
        if "/" in distance_str:
            for part in distance_str.split("/"):
                part = part.strip()
                if part and part not in VALID_DISTANCES:
                    report.add_warning(f"{char_name}: Unknown distance component '{part}'")
        else:
            report.add_warning(f"{char_name}: Unknown distance '{distance_str}'")


def validate_style(style, char_name, report):
    """Validate a style value."""
    if style is None:
        return
    
    if isinstance(style, list):
        for s in style:
            validate_style(s, char_name, report)
        return
    
    style_str = str(style).strip()
    
    # Check for non-standard values
    non_standard = {
        "Front": "Front Runner",
        "Fronts": "Front Runner",
        "Pace": "Pace Chaser",
        "Late": "Late Surger",
        "End": "End Closer",
        "Runaway": "Front Runner"
    }
    
    if style_str in non_standard:
        report.add_warning(f"{char_name}: Non-standard style '{style_str}' should be '{non_standard[style_str]}'")
    elif style_str not in VALID_STYLES:
        # Could be compound like "Late Surger/End Closer" or special like "Not-Front"
        if "/" in style_str:
            for part in style_str.split("/"):
                part = part.strip()
                if part and part not in VALID_STYLES and part not in non_standard:
                    report.add_info(f"{char_name}: Non-standard style component '{part}'")
        elif style_str not in ["Not-Front", "Anything", "Front/Pace", "Late/End", "Late/Pace"]:
            report.add_info(f"{char_name}: Non-standard style '{style_str}'")


def audit_final_data(final_data, report):
    """Run all audits on final_data.json."""
    
    # Track names for duplicate detection
    seen_names = {}
    
    for item in final_data:
        name = item.get("name", "Unknown")
        
        # 1. Check for duplicates
        if name in seen_names:
            report.add_error(f"{name}: Duplicate entry detected")
        seen_names[name] = True
        
        # 2. Check for missing awakening scores
        all_awakening_null = True
        for lv in ["lv2", "lv3", "lv4", "lv5"]:
            lv_data = item.get(lv, {})
            if lv_data and lv_data.get("score") is not None:
                all_awakening_null = False
                validate_score(lv_data.get("score"), lv, name, report)
        
        if all_awakening_null:
            report.add_warning(f"{name}: All awakening scores (lv2-lv5) are null")
        
        # 3. Check for empty innate_distance/innate_style
        innate_distance = item.get("innate_distance", [])
        innate_style = item.get("innate_style", [])
        
        if not innate_distance:
            report.add_info(f"{name}: Empty innate_distance array")
        else:
            for d in innate_distance:
                validate_distance(d, name, report)
        
        if not innate_style:
            report.add_info(f"{name}: Empty innate_style array")
        else:
            for s in innate_style:
                validate_style(s, name, report)
        
        # 4. Check trials data
        trials = item.get("trials", {})
        if trials:
            trials_score = trials.get("score")
            if trials_score is None:
                report.add_info(f"{name}: Missing trials score")
            else:
                validate_score(trials_score, "trials", name, report)
            
            if trials.get("style"):
                validate_style(trials.get("style"), name, report)
            if trials.get("distance"):
                validate_distance(trials.get("distance"), name, report)
        
        # 5. Check parent data
        parent = item.get("parent", {})
        if parent:
            parent_score = parent.get("score")
            if parent_score is None:
                report.add_info(f"{name}: Missing parent score")
            else:
                validate_score(parent_score, "parent", name, report)
        
        # 6. Check description
        description = item.get("description")
        if not description:
            report.add_info(f"{name}: Missing description")
        
        # 7. Check style_reviews
        style_reviews = item.get("style_reviews", [])
        for sr in style_reviews:
            if sr.get("type"):
                validate_style(sr.get("type"), name, report)
            if sr.get("score"):
                validate_score(sr.get("score"), "style_review", name, report)
        
        # 8. Check for known edge cases
        if name == "Agnes Digital" and all_awakening_null:
            report.add_info(f"{name}: Expected - awakening data not in ratings source")
        
        # Check variant mapping
        variant = item.get("variant", "")
        if variant in ["End of Sky", "Beyond the Horizon"]:
            report.add_info(f"{name}: Anime variant mapped to '{variant}'")


def cross_reference_sources(final_data, ratings_raw_names, reviews_raw_names, report):
    """Cross-reference final data against raw sources."""
    
    final_names = {item["name"] for item in final_data}
    final_base_names = {item.get("base_name", item["name"]) for item in final_data}
    
    # Check ratings coverage
    ratings_base_names = set(ratings_raw_names)
    
    # Check reviews coverage
    reviews_base_names = {r["name"] for r in reviews_raw_names}
    
    # Find characters in ratings but not in final
    for name in ratings_base_names:
        # Extract base name (remove variant brackets)
        base = re.sub(r'\s*\[.*?\]', '', name).strip()
        if base not in final_base_names and name not in final_names:
            # Check for partial match
            found = False
            for fn in final_names:
                if base in fn:
                    found = True
                    break
            if not found:
                report.add_warning(f"Ratings source '{name}' not found in final_data.json")
    
    # Find characters in reviews but not in final
    for r in reviews_raw_names:
        name = r["name"]
        full_name = r["full_name"]
        if name not in final_base_names and full_name not in final_names:
            # Check for partial match
            found = False
            for fn in final_names:
                if name in fn:
                    found = True
                    break
            if not found:
                report.add_warning(f"Reviews source '{name}' ({r['variant']}) not found in final_data.json")


def check_known_edge_cases(final_data, report):
    """Check for known edge cases that should have been handled."""
    
    edge_cases = {
        "Haru Urara": {"field": "lv3", "issue": "1? 3?", "expected": "1"},
        "Mayano Top Gun": {"field": "trials", "issue": "2?4?", "expected": "4"},
        "Curren Chan": {"field": "trials", "issue": "5?", "expected": "5"},
    }
    
    for item in final_data:
        name = item.get("name", "")
        
        # Check Haru Urara lv3
        if "Haru Urara" in name:
            lv3_score = item.get("lv3", {}).get("score")
            if lv3_score and "?" in str(lv3_score):
                report.add_error(f"Haru Urara: lv3 score '{lv3_score}' should have been normalized")
            elif lv3_score == "1":
                report.add_info(f"Haru Urara: lv3 score correctly normalized to '1'")
        
        # Check Mayano Top Gun trials
        if name == "Mayano Top Gun":
            trials_score = item.get("trials", {}).get("score")
            if trials_score and "?" in str(trials_score):
                report.add_error(f"Mayano Top Gun: trials score '{trials_score}' should have been normalized")
            elif trials_score == "4":
                report.add_info(f"Mayano Top Gun: trials score correctly normalized to '4'")
        
        # Check Curren Chan trials
        if name == "Curren Chan":
            trials_score = item.get("trials", {}).get("score")
            if trials_score and "?" in str(trials_score):
                report.add_error(f"Curren Chan: trials score '{trials_score}' should have been normalized")
            elif trials_score == "5":
                report.add_info(f"Curren Chan: trials score correctly normalized to '5'")
        
        # Check Smart Falcon for "4 but bad"
        if "Smart Falcon" in name:
            for lv in ["lv2", "lv3", "lv4", "lv5"]:
                score = item.get(lv, {}).get("score")
                if score and "but bad" in str(score):
                    report.add_warning(f"Smart Falcon: {lv} contains 'but bad' annotation")


def main():
    # Determine paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    VIEWER_DIR = os.path.join(BASE_DIR, 'viewer')
    
    final_data_path = os.path.join(VIEWER_DIR, 'final_data.json')
    ratings_raw_path = os.path.join(DATA_DIR, 'uma_ratings_raw.txt')
    reviews_raw_path = os.path.join(DATA_DIR, 'uma_reviews_raw.txt')
    
    # Initialize report
    report = AuditReport()
    
    # Load data
    print("Loading data files...")
    
    try:
        final_data = load_json(final_data_path)
        print(f"  Loaded final_data.json: {len(final_data)} characters")
    except FileNotFoundError:
        print(f"  ERROR: Could not find {final_data_path}")
        return
    
    try:
        ratings_raw = load_text_file(ratings_raw_path)
        ratings_raw_names = extract_names_from_ratings_raw(ratings_raw)
        print(f"  Loaded uma_ratings_raw.txt: {len(ratings_raw_names)} entries")
    except FileNotFoundError:
        print(f"  WARNING: Could not find {ratings_raw_path}")
        ratings_raw_names = []
    
    try:
        reviews_raw = load_text_file(reviews_raw_path)
        reviews_raw_names = extract_names_from_reviews_raw(reviews_raw)
        print(f"  Loaded uma_reviews_raw.txt: {len(reviews_raw_names)} entries")
    except FileNotFoundError:
        print(f"  WARNING: Could not find {reviews_raw_path}")
        reviews_raw_names = []
    
    # Add statistics
    report.stats["Total characters in final_data.json"] = len(final_data)
    report.stats["Total entries in ratings source"] = len(ratings_raw_names)
    report.stats["Total entries in reviews source"] = len(reviews_raw_names)
    
    # Count characters with complete data
    complete_count = 0
    for item in final_data:
        has_awakening = any(item.get(lv, {}).get("score") for lv in ["lv2", "lv3", "lv4", "lv5"])
        has_trials = item.get("trials", {}).get("score") is not None
        has_description = bool(item.get("description"))
        if has_awakening and has_trials and has_description:
            complete_count += 1
    
    report.stats["Characters with complete data"] = complete_count
    report.stats["Coverage percentage"] = f"{(complete_count / len(final_data) * 100):.1f}%"
    
    # Run audits
    print("\nRunning audits...")
    
    print("  1. Auditing final_data.json structure and values...")
    audit_final_data(final_data, report)
    
    print("  2. Cross-referencing against raw sources...")
    cross_reference_sources(final_data, ratings_raw_names, reviews_raw_names, report)
    
    print("  3. Checking known edge cases...")
    check_known_edge_cases(final_data, report)
    
    # Print report
    report.print_report()
    
    # Return exit code based on errors
    if report.errors:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())

