# app/services/physician_profile.py

from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.ask_cme import AskCMERequest


def build_effective_physician_profile(
    db: Session,
    request: AskCMERequest,
) -> Dict[str, Any]:
    """
    Build an 'effective' physician profile for CME personalization.

    Priority:
      1. Use database values if physician_id is provided.
      2. Override/augment with any explicit fields from the request.
    """

    profile: Dict[str, Any] = {
        "physician_id": request.physician_id,
        "specialty": request.specialty,
        "state": request.state,
        "preferred_format": request.preferred_format,
        "min_credits": request.min_credits,
        "credit_type": getattr(request, "credit_type", None),
        "travel_ok": None,
        "missing_requirements": [],   # reserved for future use
        "completed_cme_ids": [],      # filled below if physician_id is present
    }

    pid = request.physician_id

    if pid:
        # --------------------------------------------------------------
        # 1) Core physician row + primary specialty
        # --------------------------------------------------------------
        physician_row = db.execute(
            text(
                """
                SELECT
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.email,
                    s.name AS specialty_name
                FROM physician p
                LEFT JOIN specialty s
                    ON s.id = p.primary_specialty_id
                WHERE p.id = :pid
                """
            ),
            {"pid": pid},
        ).fetchone()

        if physician_row:
            # Only fill specialty if not explicitly provided in request
            if not profile["specialty"] and physician_row.specialty_name:
                profile["specialty"] = physician_row.specialty_name

        # --------------------------------------------------------------
        # 2) Physician preferences (travel, modality, etc.)
        # --------------------------------------------------------------
        pref_row = db.execute(
            text(
                """
                SELECT
                    travel_pref,
                    modality_pref,
                    date_window_pref,
                    specialty_focus
                FROM physician_preference
                WHERE physician_id = :pid
                """
            ),
            {"pid": pid},
        ).fetchone()

        if pref_row:
            # Map modality_pref to preferred_format if not overridden
            if not profile["preferred_format"] and pref_row.modality_pref:
                profile["preferred_format"] = pref_row.modality_pref

            # Simple travel_ok derivation based on travel_pref
            travel_pref = pref_row.travel_pref or ""
            if travel_pref.lower() in ("no_travel", "local_only"):
                profile["travel_ok"] = False
            else:
                profile["travel_ok"] = True

        # --------------------------------------------------------------
        # 3) Completed CME list
        # --------------------------------------------------------------
        completed_rows = db.execute(
            text(
                """
                SELECT cme_event_id
                FROM physician_completed_cme
                WHERE physician_id = :pid
                """
            ),
            {"pid": pid},
        ).fetchall()

        profile["completed_cme_ids"] = [
            int(r.cme_event_id) for r in completed_rows if r.cme_event_id is not None
        ]

        # --------------------------------------------------------------
        # 4) (Optional) Missing requirements — placeholder for future
        # --------------------------------------------------------------
        # At the moment, requirement_master is empty in your demo DB,
        # so we leave missing_requirements as an empty list.
        profile["missing_requirements"] = []

    # --------------------------------------------------------------
    # 5) Ensure some sane defaults if fields are still None
    # --------------------------------------------------------------
    if profile["preferred_format"]:
        profile["preferred_format"] = str(profile["preferred_format"]).strip().lower()

    # If travel_ok is still None, assume True (physician is flexible)
    if profile["travel_ok"] is None:
        profile["travel_ok"] = True

    return profile
