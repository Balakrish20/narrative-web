from flask import Flask, request, render_template, jsonify
import pandas as pd
from narrative_utils import build_narrative

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json.get("data", [])
        df = pd.DataFrame(data)
        grouped = df.groupby("regulatory_ID")
        result = []
        for reg_id, group in grouped:
            narrative = build_narrative(group)
            result.append({"regulatory_ID": reg_id, "narrative": narrative})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

