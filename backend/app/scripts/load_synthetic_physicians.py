"""
Load 1000 synthetic physicians + specialties + preferences + CME history
+ requirement cycles/status into the MyCertiQ_Demo database.

Run from backend/:

    source .venv/bin/activate
    python app/scripts/load_synthetic_physicians.py
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Any

from sqlalchemy import text

from app.database import SessionLocal


# ---------------------------------------------------------------------
# Static lookup data
# ---------------------------------------------------------------------
SPECIALTIES = [
    ("FM", "Family Medicine"),
    ("IM", "Internal Medicine"),
    ("CARD", "Cardiology"),
    ("ONC", "Oncology"),
    ("GI", "Gastroenterology"),
    ("ENDO", "Endocrinology"),
    ("NEURO", "Neurology"),
    ("ORTHO", "Orthopedics"),
    ("OBGYN", "Obstetrics & Gynecology"),
    ("EM", "Emergency Medicine"),
    ("PULM", "Pulmonology"),
    ("HEME", "Hematology"),
    ("NEPH", "Nephrology"),
    ("DERM", "Dermatology"),
    ("RHEUM", "Rheumatology"),
    ("PSYCH", "Psychiatry"),
    ("PED", "Pediatrics"),
    ("URO", "Urology"),
    ("RAD", "Radiology"),
    ("SURG", "Surgery"),
    ("ANES", "Anesthesiology"),
    ("PATH", "Pathology"),
    ("PMR", "Physical Med & Rehab"),
    ("OPHTH", "Ophthalmology"),
    ("PAIN", "Pain Medicine"),
    ("GERI", "Geriatrics"),
    ("ID", "Infectious Disease"),
    ("HOSP", "Hospital Medicine"),
    ("SPORTS", "Sports Medicine"),
    ("ADD", "Addiction Medicine"),
    ("CC", "Critical Care"),
    ("AI", "Allergy & Immunology"),
    ("SLEEP", "Sleep Medicine"),
    ("NUC", "Nuclear Medicine"),
    ("PLAST", "Plastic Surgery"),
    ("VASC", "Vascular Surgery"),
    ("NSURG", "Neurosurgery"),
    ("PALL", "Palliative Care"),
    ("PREV", "Preventive Medicine"),
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Casey", "Riley", "Morgan", "Sam",
    "Jamie", "Avery", "Cameron", "Drew", "Kendall", "Reese", "Logan",
    "Priya", "Neha", "Arjun", "Rahul", "Anita", "Sanjay",
]

LAST_NAMES = [
    "Smith", "Johnson", "Lee", "Patel", "Verma", "Gupta",
    "Brown", "Garcia", "Rodriguez", "Khan", "Singh", "Desai",
    "Kim", "Chen", "Lopez", "Martinez", "Davis", "Miller",
]

TRAVEL_PREFS = ["no_travel", "regional", "national", "international"]
MODALITY_PREFS = ["online_only", "live_only", "mixed"]
DATE_WINDOW_PREFS = ["anytime", "weekends_only", "weeknights_only", "next_3_months"]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def ensure_specialties(db) -> List[Dict[str, Any]]:
    """Ensure the specialty table has entries from SPECIALTIES.
    Returns a list of specialty rows (id, code, name).
    """
    print("→ Ensuring specialties exist...")

    for code, name in SPECIALTIES:
        db.execute(
            text(
                """
                INSERT INTO specialty (code, name)
                VALUES (:code, :name)
                ON CONFLICT (code) DO NOTHING;
                """
            ),
            {"code": code, "name": name},
        )
    db.commit()

    rows = db.execute(
        text("SELECT id, code, name FROM specialty ORDER BY id")
    ).fetchall()

    specialties = [{"id": r.id, "code": r.code, "name": r.name} for r in rows]
    print(f"   Found {len(specialties)} specialties.")
    return specialties


def get_all_cme_events(db) -> List[Dict[str, Any]]:
    rows = db.execute(
        text("SELECT id, credits FROM cme_event WHERE is_active = TRUE")
    ).fetchall()
    events = [{"id": r.id, "credits": r.credits} for r in rows]
    print(f"→ Found {len(events)} active CME events.")
    return events


def get_requirement_ids(db) -> List[int]:
    rows = db.execute(
        text("SELECT id FROM requirement_master")
    ).fetchall()
    ids = [r.id for r in rows]
    print(f"→ Found {len(ids)} requirement_master rows.")
    return ids


# ---------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------
def load_physicians_and_specialties(db, specialties: List[Dict[str, Any]], n: int = 1000):
    print(f"→ Loading {n} physicians...")

    count_row = db.execute(text("SELECT COUNT(*) AS c FROM physician")).fetchone()
    if count_row and count_row.c > 0:
        print(f"   Physician table already has {count_row.c} rows. Skipping physician creation.")
        return

    physician_ids: List[int] = []

    for i in range(n):
        spec = random.choice(specialties)
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}.{i+1}@demo.mycertiq"

        row = db.execute(
            text(
                """
                INSERT INTO physician (
                    user_account_id,
                    npi,
                    first_name,
                    last_name,
                    email,
                    primary_specialty_id,
                    status
                )
                VALUES (
                    NULL,
                    :npi,
                    :first_name,
                    :last_name,
                    :email,
                    :primary_specialty_id,
                    'active'
                )
                RETURNING id;
                """
            ),
            {
                "npi": f"999{i:06d}",
                "first_name": first,
                "last_name": last,
                "email": email,
                "primary_specialty_id": spec["id"],
            },
        ).fetchone()

        pid = row.id
        physician_ids.append(pid)

        # Also insert into physician_specialty as primary
        db.execute(
            text(
                """
                INSERT INTO physician_specialty (
                    physician_id,
                    specialty_id,
                    is_primary
                )
                VALUES (:pid, :sid, TRUE)
                """
            ),
            {"pid": pid, "sid": spec["id"]},
        )

    db.commit()
    print(f"   Inserted {len(physician_ids)} physicians.")
    return physician_ids


def load_physician_preferences(db, physician_ids: List[int]):
    print("→ Loading physician preferences...")

    # Check if preferences already exist
    row = db.execute(
        text("SELECT COUNT(*) AS c FROM physician_preference")
    ).fetchone()
    if row and row.c > 0:
        print(f"   physician_preference already has {row.c} rows. Skipping.")
        return

    for pid in physician_ids:
        travel_pref = random.choice(TRAVEL_PREFS)
        modality_pref = random.choice(MODALITY_PREFS)
        date_window_pref = random.choice(DATE_WINDOW_PREFS)
        family_constraints = random.choice([
            None,
            "Prefers CME near school holidays",
            "Avoids overnight travel due to family",
            "Needs activities limited to weekends",
        ])
       
       
        db.execute(
            text(
                """
                INSERT INTO physician_preference (
                    physician_id,
                    travel_pref,
                    modality_pref,
                    date_window_pref,
                    family_constraints,
                    specialty_focus
                )
                VALUES (
                    :pid,
                    :travel_pref,
                    :modality_pref,
                    :date_window_pref,
                    :family_constraints,
                    CAST(:specialty_focus AS jsonb)
                )
                """
            ),
            {
                "pid": pid,
                "travel_pref": travel_pref,
                "modality_pref": modality_pref,
                "date_window_pref": date_window_pref,
                "family_constraints": family_constraints,
                "specialty_focus": "{}",
            },
        )

  

    db.commit()
    print("   Preferences inserted.")


def load_completed_cme(db, physician_ids: List[int], cme_events: List[Dict[str, Any]]):
    print("→ Loading physician_completed_cme...")

    if not cme_events:
        print("   No cme_event rows found. Skipping completed CME load.")
        return

    row = db.execute(
        text("SELECT COUNT(*) AS c FROM physician_completed_cme")
    ).fetchone()
    if row and row.c > 0:
        print(f"   physician_completed_cme already has {row.c} rows. Skipping.")
        return

    today = date.today()

    for pid in physician_ids:
        k = random.randint(3, 15)
        chosen = random.sample(cme_events, k=min(k, len(cme_events)))

        for ev in chosen:
            credits_total = float(ev["credits"]) if ev["credits"] is not None else random.choice([1.0, 1.5, 2.0, 3.0])
            credits_earned = round(random.uniform(0.5, min(credits_total, 8.0)), 1)

            days_ago = random.randint(30, 3 * 365)
            completion_date = today - timedelta(days=days_ago)

            db.execute(
                text(
                    """
                    INSERT INTO physician_completed_cme (
                        physician_id,
                        cme_event_id,
                        credits_earned,
                        completion_date,
                        certificate_url,
                        file_store_id
                    )
                    VALUES (
                        :pid,
                        :cme_id,
                        :credits_earned,
                        :completion_date,
                        NULL,
                        NULL
                    )
                    """
                ),
                {
                    "pid": pid,
                    "cme_id": ev["id"],
                    "credits_earned": credits_earned,
                    "completion_date": completion_date,
                },
            )

    db.commit()
    print("   Completed CME records inserted.")


def load_requirement_cycles_and_status(
    db,
    physician_ids: List[int],
    requirement_ids: List[int],
):
    print("→ Loading physician_requirement_cycle + physician_requirement_status...")

    if not requirement_ids:
        print("   No requirement_master rows found. Skipping requirement cycles.")
        return

    row = db.execute(
        text("SELECT COUNT(*) AS c FROM physician_requirement_cycle")
    ).fetchone()
    if row and row.c > 0:
        print(f"   physician_requirement_cycle already has {row.c} rows. Skipping.")
        return

    today = date.today()

    for pid in physician_ids:
        # each physician gets 1–4 requirement cycles
        num_cycles = random.randint(1, 4)
        cycle_reqs = random.sample(requirement_ids, k=min(num_cycles, len(requirement_ids)))

        for req_id in cycle_reqs:
            # 2–3 year cycles
            start_offset_days = random.randint(0, 365)
            start_date = today - timedelta(days=start_offset_days)
            end_date = start_date + timedelta(days=365 * random.randint(2, 3))

            cycle_status = random.choice(["in_progress", "in_progress", "in_progress", "not_started"])

            cycle_row = db.execute(
                text(
                    """
                    INSERT INTO physician_requirement_cycle (
                        physician_id,
                        requirement_id,
                        start_date,
                        end_date,
                        status
                    )
                    VALUES (
                        :pid,
                        :req_id,
                        :start_date,
                        :end_date,
                        :status
                    )
                    RETURNING id;
                    """
                ),
                {
                    "pid": pid,
                    "req_id": req_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": cycle_status,
                },
            ).fetchone()

            cycle_id = cycle_row.id

            # Create 1 status row per cycle
            required_credits = random.choice([10.0, 20.0, 30.0, 50.0])
            completed_credits = round(random.uniform(0.0, required_credits), 1)
            remaining_credits = max(required_credits - completed_credits, 0.0)

            if remaining_credits <= 0.1:
                status = "complete"
            else:
                status = random.choice(["in_progress", "missing"])

            db.execute(
                text(
                    """
                    INSERT INTO physician_requirement_status (
                        physician_requirement_cycle_id,
                        requirement_id,
                        required_credits,
                        completed_credits,
                        remaining_credits,
                        status
                    )
                    VALUES (
                        :cycle_id,
                        :req_id,
                        :required,
                        :completed,
                        :remaining,
                        :status
                    )
                    """
                ),
                {
                    "cycle_id": cycle_id,
                    "req_id": req_id,
                    "required": required_credits,
                    "completed": completed_credits,
                    "remaining": remaining_credits,
                    "status": status,
                },
            )

    db.commit()
    print("   Requirement cycles & statuses inserted.")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    db = SessionLocal()

    try:
        specialties = ensure_specialties(db)

        physician_ids = load_physicians_and_specialties(db, specialties, n=1000)
        # If physicians already existed, reload their IDs:
        if not physician_ids:
            rows = db.execute(text("SELECT id FROM physician ORDER BY id")).fetchall()
            physician_ids = [r.id for r in rows]
            print(f"   Using existing {len(physician_ids)} physician IDs.")

        load_physician_preferences(db, physician_ids)

        cme_events = get_all_cme_events(db)
        load_completed_cme(db, physician_ids, cme_events)

        requirement_ids = get_requirement_ids(db)
        load_requirement_cycles_and_status(db, physician_ids, requirement_ids)

        print("🎉 Synthetic physician data load complete.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
