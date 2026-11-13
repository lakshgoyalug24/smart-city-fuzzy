# Smart City Fuzzy Platform

Six smart-city applications solved with three fuzzy inference models (Mamdani, Sugeno, Tsukamoto) on identical inputs.
Backend: Python + Flask (all fuzzy maths). Frontend: HTML, CSS, JavaScript (Canvas charts).

## Run
```
cd backend
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Structure
- backend/fuzzy.py - membership functions, rule base, 3 inference models
- backend/app.py - Flask REST API (/api/modules, /api/evaluate, /api/sweep)
- frontend/ - index.html, style.css, script.js
