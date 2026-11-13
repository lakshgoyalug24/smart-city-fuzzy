from flask import Flask, jsonify, request, send_from_directory
import fuzzy

app = Flask(__name__, static_folder="../frontend", static_url_path="")

@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/api/health")
def health():
    return jsonify(status="online")

@app.get("/api/modules")
def modules():
    return jsonify({k: dict(id=k, name=m["name"], output=m["output"], desc=m["desc"],
                            inputs=m["inputs"], rules=27, curves=fuzzy.curves(k))
                    for k, m in fuzzy.MODULES.items()})

@app.post("/api/evaluate")
def evaluate():
    d = request.get_json(force=True)
    if d.get("module") not in fuzzy.MODULES:
        return jsonify(error="Unknown module"), 400
    return jsonify(fuzzy.evaluate(d["module"], d.get("inputs", {})))

@app.post("/api/sweep")
def sweep():
    d = request.get_json(force=True)
    if d.get("module") not in fuzzy.MODULES:
        return jsonify(error="Unknown module"), 400
    return jsonify(fuzzy.sweep(d["module"], d["variable"], d.get("inputs", {})))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
