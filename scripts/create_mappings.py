import json
import os

def extract_chara_map():
    mappings = {}
    try:
        with open('data/en/chara.txt', 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) > 1:
                    # ID is index 0, Name is index 1
                    mappings[parts[0]] = parts[1]
        
        with open('data/en/map_chara.json', 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        print(f"Extracted {len(mappings)} character mappings.")
    except FileNotFoundError:
        print("data/en/chara.txt not found, skipping.")

def extract_support_map():
    mappings = {}
    try:
        with open('data/en/support_card.txt', 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) > 1:
                    # ID is index 0, Name is index 1
                    mappings[parts[0]] = parts[1]
        
        with open('data/en/map_support.json', 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        print(f"Extracted {len(mappings)} support card mappings.")
    except FileNotFoundError:
        print("data/en/support_card.txt not found, skipping.")

if __name__ == "__main__":
    os.makedirs('data/en', exist_ok=True)
    extract_chara_map()
    extract_support_map()
