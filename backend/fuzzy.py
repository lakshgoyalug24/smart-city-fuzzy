"""Pure-Python fuzzy engine: Mamdani, Sugeno and Tsukamoto on identical inputs."""
from itertools import product

TERMS = ["Low", "Medium", "High"]
OUT_MIN, OUT_MAX = 0.0, 100.0          # every module outputs a 0-100 score

# ---------- module definitions (pol: +1 raises output, -1 lowers it; w: importance)
MODULES = {
    "traffic": dict(name="Smart Traffic Management", output="Signal priority",
        desc="How urgently traffic signals must act.",
        inputs=[dict(id="density", name="Traffic density", unit="veh/km", min=0, max=100, default=60, pol=1, w=1),
                dict(id="speed", name="Average speed", unit="km/h", min=0, max=80, default=25, pol=-1, w=1),
                dict(id="queue", name="Queue length", unit="m", min=0, max=200, default=120, pol=1, w=1)]),
    "parking": dict(name="Smart Parking Management", output="Guidance priority",
        desc="How strongly to send drivers elsewhere.",
        inputs=[dict(id="occ", name="Occupancy", unit="%", min=0, max=100, default=80, pol=1, w=1.5),
                dict(id="demand", name="Parking demand", unit="%", min=0, max=100, default=70, pol=1, w=1),
                dict(id="free", name="Available spaces", unit="%", min=0, max=100, default=20, pol=-1, w=1)]),
    "lighting": dict(name="Smart Street Lighting", output="Lighting intensity",
        desc="How bright street lights should be.",
        inputs=[dict(id="ambient", name="Ambient light", unit="%", min=0, max=100, default=20, pol=-1, w=1.5),
                dict(id="activity", name="Pedestrian/vehicle activity", unit="%", min=0, max=100, default=60, pol=1, w=1),
                dict(id="night", name="Night factor", unit="%", min=0, max=100, default=85, pol=1, w=1)]),
    "waste": dict(name="Smart Waste Management", output="Collection priority",
        desc="Which bins to empty first.",
        inputs=[dict(id="fill", name="Bin fill level", unit="%", min=0, max=100, default=75, pol=1, w=1.5),
                dict(id="rate", name="Waste generation rate", unit="kg/h", min=0, max=20, default=12, pol=1, w=1),
                dict(id="delay", name="Collection delay", unit="h", min=0, max=72, default=36, pol=1, w=1)]),
    "water": dict(name="Smart Water Management", output="Irrigation requirement",
        desc="How much water crops need.",
        inputs=[dict(id="soil", name="Soil moisture", unit="%", min=0, max=100, default=25, pol=-1, w=1.5),
                dict(id="temp", name="Temperature", unit="°C", min=0, max=45, default=34, pol=1, w=1),
                dict(id="rain", name="Rainfall probability", unit="%", min=0, max=100, default=15, pol=-1, w=1)]),
    "environment": dict(name="Environment Monitoring", output="Environmental risk",
        desc="How risky the environment is.",
        inputs=[dict(id="aqi", name="Air Quality Index", unit="AQI", min=0, max=500, default=260, pol=1, w=1.5),
                dict(id="co2", name="CO2 concentration", unit="ppm", min=300, max=2000, default=900, pol=1, w=1),
                dict(id="noise", name="Noise level", unit="dB", min=30, max=120, default=75, pol=1, w=1)]),
}

# ---------- membership functions
def tri(x, a, b, c):
    if x < a or x > c: return 0.0
    if x == b: return 1.0
    return (x - a) / (b - a) if x < b else (c - x) / (c - b)

def in_params(var, term):
    lo, hi = var["min"], var["max"]; mid = (lo + hi) / 2
    return [(lo, lo, mid), (lo, mid, hi), (mid, hi, hi)][TERMS.index(term)]

def out_params(term):                  # Mamdani output triangles on 0-100
    return [(0, 0, 50), (25, 50, 75), (50, 100, 100)][TERMS.index(term)]

SUGENO_CONST = {"Low": 15, "Medium": 50, "High": 85}

def tsukamoto_z(term, w):              # monotonic output shapes, inverted at firing strength w
    return {"Low": 50 * (1 - w), "Medium": 25 + 50 * w, "High": 50 + 50 * w}[term]

# ---------- rule base: 3^3 = 27 rules from expert polarity/weights
def build_rules(m):
    ins, rules = m["inputs"], []
    total = sum(2 * v["w"] for v in ins)
    for combo in product(range(3), repeat=len(ins)):
        s = sum(v["w"] * (lvl if v["pol"] > 0 else 2 - lvl) for v, lvl in zip(ins, combo)) / total
        out = TERMS[0] if s < 0.34 else TERMS[1] if s < 0.67 else TERMS[2]
        rules.append(dict(ants=[TERMS[l] for l in combo], out=out))
    return rules

def evaluate(key, values):
    m = MODULES[key]; ins = m["inputs"]
    x = {v["id"]: min(max(float(values.get(v["id"], v["default"])), v["min"]), v["max"]) for v in ins}
    # 1. fuzzification
    mu = {v["id"]: {t: tri(x[v["id"]], *in_params(v, t)) for t in TERMS} for v in ins}
    # 2. rule firing (AND = min)
    fired = []
    for r in build_rules(m):
        w = min(mu[v["id"]][t] for v, t in zip(ins, r["ants"]))
        if w > 0: fired.append(dict(ants=r["ants"], out=r["out"], w=round(w, 4)))
    fired.sort(key=lambda r: -r["w"])
    sw = sum(r["w"] for r in fired) or 1e-9
    # 3. three inference models
    zs = [i * 0.5 for i in range(201)]
    agg = [max(min(r["w"], tri(z, *out_params(r["out"]))) for r in fired) for z in zs]
    mam = sum(z * a for z, a in zip(zs, agg)) / (sum(agg) or 1e-9)          # centroid
    sug = sum(r["w"] * SUGENO_CONST[r["out"]] for r in fired) / sw          # weighted avg
    tsu = sum(r["w"] * tsukamoto_z(r["out"], r["w"]) for r in fired) / sw   # weighted avg of crisp z
    res = {"Mamdani": round(mam, 2), "Sugeno": round(sug, 2), "Tsukamoto": round(tsu, 2)}
    mean = sum(res.values()) / 3
    best = min(res, key=lambda k: abs(res[k] - mean))
    why = {"Mamdani": "it is the most interpretable and sits closest to the consensus of all three models.",
           "Sugeno": "it is the cheapest to compute (no integration) and sits closest to the consensus of all three models.",
           "Tsukamoto": "its crisp per-rule outputs track the consensus of all three models most closely."}[best]
    return dict(inputs=x, memberships=mu, fired=fired[:8], fired_count=len(fired), total_rules=27,
                results=res, aggregated=dict(z=zs[::4], mu=agg[::4]),
                best=best, reason=f"{best} fits best here because {why}")

def curves(key):
    m = MODULES[key]; out = {}
    for v in m["inputs"]:
        xs = [v["min"] + (v["max"] - v["min"]) * i / 60 for i in range(61)]
        out[v["id"]] = dict(x=xs, **{t: [tri(x, *in_params(v, t)) for x in xs] for t in TERMS})
    return out

def sweep(key, var_id, base):
    v = next(i for i in MODULES[key]["inputs"] if i["id"] == var_id)
    xs = [v["min"] + (v["max"] - v["min"]) * i / 30 for i in range(31)]
    series = {"Mamdani": [], "Sugeno": [], "Tsukamoto": []}
    for x in xs:
        r = evaluate(key, {**base, var_id: x})["results"]
        for k in series: series[k].append(r[k])
    return dict(x=xs, series=series, label=f'{v["name"]} ({v["unit"]})')
