import json
from flextool_lp.optimization import calculation
from pathlib import Path
from flextool_lp.validation import reformat_payload

def test_calculation_runs():
    sample = json.loads(Path("examples/sample_payload.json").read_text())
    payload = reformat_payload(payload)   
    sample = reformat_payload(sample)
    out, status = calculation(sample)
    assert status in {"Optimal", "Feasible"}
    assert "totalSavings" in out
    assert "activated_measuers_times_list" in out
