from flask import Flask, jsonify, request
from flextool_lp.optimization import calculation
from flextool_lp.validation import reformat_payload
from flextool_lp.version import __version__
import traceback

app = Flask(__name__)

@app.get("/healthz")
def health():
    return jsonify({"status": "ok", "service": "flextool-lp-service", "version": __version__})

@app.post("/optimize")
def optimize():
    try:
        payload = request.get_json(force=True, silent=False)
        payload = reformat_payload(payload)
        outputs, status = calculation(payload)
        return jsonify({"status": status, "result": outputs})
    except Exception as e:
        #to log full tracebacks in real deployments.
        traceback.print_exc()
        return jsonify({"error": "internal_error", "detail": str(e)}), 500

if __name__ == "__main__":
    # Simple built-in server for local development
    app.run(host="0.0.0.0", port=5050, debug=True)
