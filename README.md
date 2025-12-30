# UMA Ratings Viewer & Team Planner

A premium, standalone web application for viewing UMA Musume ratings, reviews, and planning your team compositions.

## Project Structure

```text
team-planner/
├── viewer/             # The Web Application
│   ├── index.html      # Main UI
│   ├── style.css       # Premium styles (Glassmorphism, Dark mode)
│   ├── script.js       # App logic (Filters, Sorting, Team Planner)
│   └── final_data.json # Unified data (Generated)
├── scripts/            # Data Processing Scripts
│   ├── unify_data.py   # Main script to merge ratings and reviews
│   └── ...             # Helper parsing scripts
├── data/               # Source Data
│   ├── uma_ratings.txt # Raw ratings data
│   └── uma_reviews.txt # Raw review descriptions
└── README.md
```

## Features

- **Advanced Filtering**: Filter by Distance, Style, Trials, Parent, Debuff, and Owned status.
- **Team Planner**: Save your team for Sprint, Mile, Medium, Long, and Dirt categories (persists in LocalStorage).
- **Interactive Tooltips**: Hover over UMA names to see detailed review descriptions. Pin tooltips with a click.
- **Premium Design**: Dark themed, glassmorphic UI with smooth animations and intuitive controls.
- **Dynamic Sorting**: Sort by any column, including special ratings and owned status.

## Getting Started

### 1. View the Application
To run the viewer locally, start a web server in the `viewer/` directory:

```bash
cd viewer
python -m http.server 8000
```
Then open `http://localhost:8000` in your browser.

### 2. Update Data
If you modify the source files in `data/`, run the unification script to update the viewer's data:

```bash
python scripts/unify_data.py
```

## Maintenance

The `scripts/` directory contains various utility scripts inherited from the legacy system to help with parsing and identifying missing character mappings.

---
*Created for Simon - 2025*
