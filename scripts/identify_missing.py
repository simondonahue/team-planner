import json
import re

def get_names_from_ratings(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(item['name'] for item in data)

def get_names_from_reviews(file_path):
    names = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Matches headers like "Sakura Bakushin O (1*)" or "Mejiro McQueen (Anime)"
            # Character names are usually at the start of the line and followed by ( )
            match = re.match(r'^([^:(#\n]+)\s*(\(.*\))', line)
            if match:
                name = line.strip()
                if "Ratings:" not in name and "Written after" not in name:
                    names.append(name)
    return names

def normalize(name):
    base = re.sub(r'\(.*?\)|\[.*?\]', '', name).strip()
    return base.lower()

ratings_names = get_names_from_ratings('ratings_viewer/ratings.json')
reviews_names = get_names_from_reviews('uma_reviews.txt')

missing = []

# Map review variants to rating variants
variant_map = {
    "1*": "",
    "2*": "",
    "3*": "",
    "original": "",
    "anime mcqueen": "end of sky",
    "anime teio": "beyond the horizon",
    "wedding": "wedding",
    "fantasy": "fantasy",
    "summer": "summer"
}

for rev_name in reviews_names:
    norm_rev = normalize(rev_name)
    rev_var = re.search(r'\((.*?)\)', rev_name)
    rev_var_text = rev_var.group(1).lower() if rev_var else ""
    
    found = False
    for rat_name in ratings_names:
        norm_rat = normalize(rat_name)
        if norm_rev == norm_rat:
            rat_var = re.search(r'\[(.*?)\]', rat_name)
            rat_var_text = rat_var.group(1).lower() if rat_var else ""
            
            # Simple base version check
            if rev_var_text in ["1*", "2*", "3*", "original"] and not rat_var_text:
                found = True
                break
            # Variant check
            if rev_var_text == rat_var_text and rev_var_text != "":
                found = True
                break
            # Anime check
            if rev_var_text == "anime" and (rat_var_text == "end of sky" or rat_var_text == "beyond the horizon"):
                found = True
                break
                
    if not found:
        missing.append(rev_name)

print("Missing from table:")
for name in missing:
    print(name)
