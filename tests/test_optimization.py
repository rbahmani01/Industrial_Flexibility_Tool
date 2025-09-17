import json
from pathlib import Path
from flextool_lp.optimization import calculation


def test_calculation_runs_with_sample_payload():
    # Load example payload
    sample_path = Path("examples/sample_payload.json")
    sample = json.loads(sample_path.read_text())

    # Reformat and run calculation
    payload = reformat_payload(sample)
    outputs, status = calculation(payload)

    # Basic checks
    assert "totalSavings" in outputs
    assert 'activated_measures' in outputs
