
import json
import re
import os


def parse_rating_item(item_str):
    item_str = item_str.strip()
    if not item_str:
        return None
        
    # Patterns to try
    # 1. "Name Score (Context)" e.g. "Pace Chaser 4 (Sprint)"
    #    Also handles "Name Score" e.g. "Parent 2"
    #    Regex: Name comes first, then a number/score, then optional parens
    
    # "Team Trials 4 (Late Surger) 3 (Pace Chaser)" is weird.
    # Let's try to capture the score as the digit(s) immediately following name?
    
    # Pattern A: Name (Score) -> "Speed Debuffer (-0.25)"
    match_a = re.match(r"^(.+)\s+\(([-\d\.\?]+%?)\)$", item_str)
    if match_a:
        return {"name": match_a.group(1).strip(), "score": match_a.group(2).strip(), "context": ""}
        
    # Pattern B: Name Score (Context) OR Name Score
    # We look for the FIRST occurrence of a digit-like token that looks like a score
    # But names can have digits? "Team Trials" doesn't.
    # "3* Umas" is not a rating.
    
    # Heuristic: split by space, find the part that looks like a score.
    # Scores: "4", "2?4?", "-0.25", "4+"
    parts = item_str.split(' ')
    score_idx = -1
    for i, p in enumerate(parts):
        # Check if p is a score
        # Allow numbers, ?, +, -, %
        if re.match(r"^[-+]?[\d\.\?]+%?\+?$", p):
            score_idx = i
            break
            
    if score_idx != -1:
        name = " ".join(parts[:score_idx])
        score = parts[score_idx]
        context = " ".join(parts[score_idx+1:])
        # Strip parens from context if it's essentially just (Context)
        if context.startswith("(") and context.endswith(")"):
            context = context[1:-1]
        return {"name": name, "score": score, "context": context}
        
    # Fallback: Just put everything in name
    return {"name": item_str, "score": "", "context": ""}

def parse_uma_ratings(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    umas = []
    current_uma = None
    section_category = ""
    
    header_pattern = re.compile(r"^(.+) \((.+)\)$")
    category_pattern = re.compile(r"^(\d+\* Umas|This Month’s Reviews)$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if category_pattern.match(line):
            section_category = line
            continue
            
        if not line.startswith("Ratings:"):
            header_match = header_pattern.match(line)
            if header_match:
                name, stars = header_match.groups()
                
                if current_uma:
                    umas.append(current_uma)
                
                current_uma = {
                    "name": name,
                    "stars": stars,
                    "ratings_raw": "",
                    "ratings": [],
                    "description": "",
                    "category": section_category
                }
                continue

        if current_uma:
            if line.startswith("Ratings:"):
                raw = line[8:].strip()
                current_uma["ratings_raw"] = raw
                
                # Parse the raw string
                # Split by comma, but be careful of commas inside parens? 
                # The file seems consistent with "Item, Item, Item"
                # "Team Trials 4 (Late Surger) 3 (Pace Chaser)" -> no comma inside
                if raw:
                    items = [x.strip() for x in raw.split(',')]
                    for it in items:
                        parsed = parse_rating_item(it)
                        if parsed:
                            current_uma["ratings"].append(parsed)
            else:
                if current_uma["description"]:
                    current_uma["description"] += "\n\n" + line
                else:
                    current_uma["description"] = line

    if current_uma:
        umas.append(current_uma)

    return umas


def generate_markdown(umas):
    md_content = "# Uma Musume Ratings\n\n"
    
    md_content += "| Name | Stars | Ratings | Description |\n"
    md_content += "| --- | --- | --- | --- |\n"
    
    for uma in umas:
        name = uma['name'].replace("|", "\|")
        stars = uma['stars'].replace("|", "\|")
        
        # Format ratings for table: "Name: Score"
        # Combine them into a single string with line breaks or commas
        r_list = []
        for r in uma['ratings']:
            s = f"{r['name']}"
            if r['score']:
                s += f" **{r['score']}**"
            if r['context']:
                s += f" ({r['context']})"
            r_list.append(s)
        ratings_str = ", ".join(r_list).replace("|", "\|")
            
        # Preview description
        desc_preview = (uma['description'][:100] + '...') if len(uma['description']) > 100 else uma['description']
        desc_preview = desc_preview.replace("\n", " ")
        
        anchor = name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('.', '')
        md_content += f"| [{name}](#{anchor}) | {stars} | {ratings_str} | {desc_preview} |\n"
        
    md_content += "\n---\n\n"

    current_cat = ""
    for uma in umas:
        if uma['category'] != current_cat:
            if uma['category']:
                current_cat = uma['category']
                md_content += f"## {current_cat}\n\n"
            
        md_content += f"### {uma['name']} ({uma['stars']})\n"
        
        if uma['ratings']:
            md_content += "**Ratings:**\n"
            for r in uma['ratings']:
                md_content += f"- **{r['name']}**: {r['score']}"
                if r['context']:
                    md_content += f" *({r['context']})*"
                md_content += "\n"
            md_content += "\n"
        elif uma['ratings_raw']:
            md_content += f"**Ratings:** {uma['ratings_raw']}\n\n"
            
        md_content += f"{uma['description']}\n\n"
        
    return md_content

def main():
    source_file = r"c:\Users\Simon\Documents\GitHub\umasim\uma_ratings.txt"
    umas = parse_uma_ratings(source_file)
    
    # Write JSON
    json_output_path = r"c:\Users\Simon\Documents\GitHub\umasim\uma_ratings.json"
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(umas, f, indent=2, ensure_ascii=False)
        
    # Write Markdown
    md_output_path = r"c:\Users\Simon\Documents\GitHub\umasim\uma_ratings.md"
    md_content = generate_markdown(umas)
    with open(md_output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"Successfully converted {len(umas)} entries.")

if __name__ == "__main__":
    main()
