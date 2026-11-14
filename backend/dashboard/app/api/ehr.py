from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import Principal, require_physician
from ..database import get_db
from ..integrations.ehr import handoff_to_mock_ehr
from ..models.orm import Encounter
from ..schemas.team_b import HandoffRequest
from ..services.encounter import write_audit

router = APIRouter(prefix="/api/ehr")


@router.post("/handoff")
def ehr_handoff(
    body: HandoffRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = db.query(Encounter).filter_by(encounter_id=body.encounter_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Unable to load encounter.")
    try:
        summary = handoff_to_mock_ehr(db, row)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    write_audit(
        db,
        row,
        "ehr_handoff_completed" if summary.get("status") == "SUCCESS" else "ehr_handoff_failed",
        "Mock EHR adapter processed a physician-finalized bundle.",
    )
    db.commit()
    if summary.get("status") != "SUCCESS":
        raise HTTPException(status_code=502, detail="EHR handoff failed.")
    return summary
