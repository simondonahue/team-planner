#!/usr/bin/env python3
"""
Shared utilities for UMA Team Planner data parsing.

This module provides a single source of truth for:
- Valid distances and styles
- Standardization/normalization functions
- Score parsing with edge case handling
- Common helper functions
"""

import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

VALID_DISTANCES = {"Sprint", "Mile", "Medium", "Long", "Dirt"}

VALID_STYLES = {"Front Runner", "Pace Chaser", "Late Surger", "End Closer"}

# Mapping for standardizing distance abbreviations
DISTANCE_MAPPINGS = {
    "Med.": "Medium",
    "Med": "Medium",
    "Mid": "Medium",
}

# Mapping for standardizing style abbreviations
STYLE_MAPPINGS = {
    "Front": "Front Runner",
    "Fronts": "Front Runner",
    "Pace": "Pace Chaser",
    "Late": "Late Surger",
    "End": "End Closer",
    "Runaway": "Front Runner",
    # Full names map to themselves (for consistency)
    "End Closer": "End Closer",
    "Front Runner": "Front Runner",
    "Pace Chaser": "Pace Chaser",
    "Late Surger": "Late Surger",
}

# Category headers that should be skipped
CATEGORY_HEADERS = {
    "1* Umas", "2* Umas", "3* Umas",
    "This Month's Reviews", "This Month's",
}

# Known edge cases for score normalization
# Format: {character_name: {field: (pattern, normalized_value)}}
SCORE_EDGE_CASES = {
    "Haru Urara": {
        "lv3": ("1? 3?", "1"),
    },
    "Mayano Top Gun": {
        "trials": ("2?4?", "4"),
    },
    "Curren Chan": {
        "trials": ("5?", "5"),
    },
}

# =============================================================================
# STANDARDIZATION FUNCTIONS
# =============================================================================

def standardize(text):
    """
    Standardize a distance or style value to its canonical form.
    
    Args:
        text: Raw text to standardize (can be single value or slash-separated)
        
    Returns:
        Standardized string with canonical values, or None if input is empty
    """
    if not text:
        return None
    
    text = str(text).strip()
    if not text:
        return None
    
    # Handle slash-separated values (e.g., "Late/End")
    words = text.split('/')
    standardized_words = []
    
    for word in words:
        word = word.strip()
        if not word:
            continue
            
        # Try title case for matching
        word_title = word.title()
        
        # Check distance mappings first
        if word in DISTANCE_MAPPINGS:
            standardized_words.append(DISTANCE_MAPPINGS[word])
        elif word_title in DISTANCE_MAPPINGS:
            standardized_words.append(DISTANCE_MAPPINGS[word_title])
        # Check style mappings
        elif word in STYLE_MAPPINGS:
            standardized_words.append(STYLE_MAPPINGS[word])
        elif word_title in STYLE_MAPPINGS:
            standardized_words.append(STYLE_MAPPINGS[word_title])
        # Keep as-is if valid
        elif word in VALID_DISTANCES or word in VALID_STYLES:
            standardized_words.append(word)
        elif word_title in VALID_DISTANCES or word_title in VALID_STYLES:
            standardized_words.append(word_title)
        else:
            # Keep original if no mapping found
            standardized_words.append(word)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for w in standardized_words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)
    
    return '/'.join(unique_words) if unique_words else None


def standardize_distance(text):
    """Standardize a distance value specifically."""
    result = standardize(text)
    if result and result not in VALID_DISTANCES:
        # Check if it's a compound
        if '/' in result:
            return result
        # Log unknown distance
        logger.debug(f"Unknown distance value: {result}")
    return result


def standardize_style(text):
    """Standardize a style value specifically."""
    result = standardize(text)
    if result and result not in VALID_STYLES:
        # Check if it's a compound or known exception
        if '/' in result or result in ["Not-Front", "Anything"]:
            return result
        # Log unknown style
        logger.debug(f"Unknown style value: {result}")
    return result


# =============================================================================
# SCORE PARSING
# =============================================================================

def parse_score(raw_score, char_name=None, field_name=None):
    """
    Parse and normalize a score value, handling edge cases.
    
    Args:
        raw_score: Raw score string (e.g., "4", "5?", "1? 3?", "2~3")
        char_name: Character name for edge case lookup (optional)
        field_name: Field name for edge case lookup (optional)
        
    Returns:
        Tuple of (normalized_score, was_modified)
    """
    if raw_score is None:
        return (None, False)
    
    score_str = str(raw_score).strip()
    if not score_str:
        return (None, False)
    
    # Check for known edge cases first
    if char_name and field_name:
        edge_cases = SCORE_EDGE_CASES.get(char_name, {})
        if field_name in edge_cases:
            pattern, normalized = edge_cases[field_name]
            if pattern in score_str:
                logger.info(f"Normalized {char_name} {field_name}: '{score_str}' -> '{normalized}'")
                return (normalized, True)
    
    # Handle common patterns
    
    # Pattern: "1? 3?" -> take first number
    space_pattern = re.match(r'^(\d)\?\s+\d\?', score_str)
    if space_pattern:
        normalized = space_pattern.group(1)
        logger.info(f"Normalized ambiguous score: '{score_str}' -> '{normalized}'")
        return (normalized, True)
    
    # Pattern: "2~3" range -> take first number
    range_pattern = re.match(r'^(\d)~\d', score_str)
    if range_pattern:
        normalized = range_pattern.group(1)
        logger.info(f"Normalized range score: '{score_str}' -> '{normalized}'")
        return (normalized, True)
    
    # Pattern: "5?" with single uncertain -> keep the number
    single_uncertain = re.match(r'^(\d)\?$', score_str)
    if single_uncertain:
        normalized = single_uncertain.group(1)
        logger.debug(f"Kept uncertain score: '{score_str}' -> '{normalized}'")
        return (normalized, True)
    
    # Return as-is if no normalization needed
    return (score_str, False)


def is_valid_score(score):
    """Check if a score is a valid 1-5 integer."""
    if score is None:
        return False
    try:
        val = int(str(score).strip())
        return 1 <= val <= 5
    except ValueError:
        return False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def split_ignoring_brackets(text, delimiter=','):
    """
    Split text by delimiter, but ignore delimiters inside parentheses.
    
    Args:
        text: String to split
        delimiter: Character to split on (default: ',')
        
    Returns:
        List of stripped parts
    """
    parts = []
    start = 0
    nest_level = 0
    
    for i, char in enumerate(text):
        if char == '(':
            nest_level += 1
        elif char == ')':
            nest_level -= 1
        elif char == delimiter and nest_level == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    
    # Add the last part
    parts.append(text[start:].strip())
    
    # Filter out empty strings
    return [p for p in parts if p]


def is_category_header(line):
    """Check if a line is a category header that should be skipped."""
    line = line.strip()
    return line in CATEGORY_HEADERS or "Umas" in line or "Reviews" in line


def extract_name_variant(header_line):
    """
    Extract name and variant from a character header line.
    
    Handles formats like:
    - "Name (Variant)"
    - "Name [Variant]"
    - "Name (Distance | Style)"
    
    Args:
        header_line: The header line to parse
        
    Returns:
        Tuple of (base_name, variant, full_display_name) or (None, None, None) if not a header
    """
    line = header_line.strip()
    
    # Skip empty lines and ratings lines
    if not line or line.startswith('Ratings:'):
        return (None, None, None)
    
    # Pattern for "[Variant]" format (used in reviews for non-original)
    bracket_match = re.match(r'^([^()\[\]]+)\s*\[([^\]]+)\]$', line)
    if bracket_match:
        name = bracket_match.group(1).strip()
        variant = bracket_match.group(2).strip()
        
        # Skip category headers
        if name in ["1*", "2*", "3*", "This Month's"] or is_category_header(name):
            return (None, None, None)
        
        full_name = f"{name} [{variant}]" if variant not in ["Original"] else name
        return (name, variant, full_name)
    
    # Pattern for "(Variant)" format (used in reviews for stars)
    paren_match = re.match(r'^([^()\[\]]+)\s*\(([^|)]+)\)$', line)
    if paren_match:
        name = paren_match.group(1).strip()
        variant = paren_match.group(2).strip()
        
        # Check if this looks like a star rating
        if variant in ["1*", "2*", "3*", "Original"]:
            # Skip category headers
            if name in ["1*", "2*", "3*", "This Month's"] or is_category_header(name):
                return (None, None, None)
            return (name, "Original", name)
        
        # This might be a ratings header with (Distance | Style) - handle separately
        return (None, None, None)
    
    return (None, None, None)


# =============================================================================
# EMPTY DEFAULTS
# =============================================================================

EMPTY_RATING = {
    "score": None,
    "style": None,
    "track_type": None,
    "special_score": None,
    "special_style": None
}

EMPTY_TRIALS = {
    "score": None,
    "distance": None,
    "style": None
}

EMPTY_PARENT = {
    "score": None,
    "note": None
}

EMPTY_DEBUFFER = {
    "type": None,
    "effect": None
}


if __name__ == "__main__":
    # Quick self-test
    print("Testing standardize():")
    print(f"  'Med.' -> '{standardize('Med.')}'")
    print(f"  'Front' -> '{standardize('Front')}'")
    print(f"  'Late/End' -> '{standardize('Late/End')}'")
    print(f"  'Pace Chaser' -> '{standardize('Pace Chaser')}'")
    
    print("\nTesting parse_score():")
    print(f"  '4' -> {parse_score('4')}")
    print(f"  '5?' -> {parse_score('5?')}")
    print(f"  '1? 3?' -> {parse_score('1? 3?')}")
    print(f"  '2~3' -> {parse_score('2~3')}")
    print(f"  Haru Urara lv3 '1? 3?' -> {parse_score('1? 3?', 'Haru Urara', 'lv3')}")
    
    print("\nTesting split_ignoring_brackets():")
    print(f"  'a, b (c, d), e' -> {split_ignoring_brackets('a, b (c, d), e')}")


