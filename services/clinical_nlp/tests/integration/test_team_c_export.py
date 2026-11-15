"""Team 2B output must be accepted by Team 2C's `TeamBPayload` schema."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _team_c_schema():
    candidates = [
        ROOT.parents[1] / "backend/dashboard/app/schemas/team_b.py",
        ROOT / "backend/app/schemas/team_b.py",
        ROOT.parents[1] / "shared/contracts/clinical_analysis.py",
    ]
    target_path = next((p for p in candidates if p.exists()), None)
    if not target_path:
        raise FileNotFoundError(f"Could not locate Team C schema in candidates: {candidates}")
    spec = importlib.util.spec_from_file_location("team_c_schema", target_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "TeamBPayload", getattr(mod, "ClinicalAnalysisContract", None))


def test_real_team_a_sample_maps_to_team_c(pipeline):
    from app.export.team_c import to_team_c_payload
    from app.models.contracts import TeamATranscriptIn

    sample = json.loads((ROOT / "data/samples/team_a_20261031_143022.json").read_text())
    analysis = pipeline.analyze(TeamATranscriptIn(**sample))
    payload = to_team_c_payload(analysis, {"name": "Mr. Davis", "age": 54})
    parsed = _team_c_schema().model_validate(payload)

    assert parsed.patient.age == 54 and "penicillin" in [a.lower() for a in parsed.patient.allergies]
    seg_ids = {s.id for s in parsed.transcript.segments}
    assert all(c in seg_ids for claim in parsed.claims for c in claim.citations)  # citations resolvable
    assert {s.speaker for s in parsed.transcript.segments} == {"physician", "patient"}


def test_unknown_age_is_allowed(pipeline):
    from app.export.team_c import to_team_c_payload
    from app.models.contracts import TeamATranscriptIn

    sample = json.loads((ROOT / "data/samples/team_a_20261031_143022.json").read_text())
    payload = to_team_c_payload(pipeline.analyze(TeamATranscriptIn(**sample)))
    assert _team_c_schema().model_validate(payload).patient.age is None
