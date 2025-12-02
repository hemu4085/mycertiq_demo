# app/services/cme_query.py

from typing import List, Tuple, Dict, Any

import time
import logging

import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cme_event import CMEEvent
from app.schemas.ask_cme import CMERecommendation, AskCMERequest
from app.services.physician_profile import build_effective_physician_profile

# -----------------------------------------------------------------------------
# Logging & OpenAI client
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


async def run_cme_query(
    request: AskCMERequest,
    db: Session,
    *,
    vector_top_k: int = 24,
    max_events: int = 5,
) -> Tuple[str, List[CMERecommendation]]:
    """
    Full pipeline for the Human-like, Personalized CME Query:

    1. Vector search (/vector/search)
    2. Physician profile (DB + overrides)
    3. Score CME events based on chunk similarity
    4. Load CME metadata from DB
    5. Apply personalization filters
    6. Build LLM context
    7. Call LLM for natural-language answer
    8. Build structured recommendations for the UI
    """

    t_start = time.perf_counter()

    question = request.question.strip()
    if not question:
        return (
            "Please provide a non-empty question about what CME you are looking for.",
            [],
        )

    # -------------------------------------------------------------------------
    # 1. Call vector search
    # -------------------------------------------------------------------------
    async with httpx.AsyncClient(
        base_url=settings.BACKEND_BASE_URL,
        timeout=30.0,
    ) as http_client:
        resp = await http_client.post(
            "/vector/search",
            json={
                "query": question,
                "source_type": "cme_event",
                "top_k": vector_top_k,
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Vector search failed: {resp.status_code} — {resp.text}"
        )

    chunks: List[Dict[str, Any]] = resp.json()
    t_after_vector = time.perf_counter()
    logger.info(
        "[CME_QUERY] Vector search returned %d chunks in %.3fs",
        len(chunks),
        t_after_vector - t_start,
    )

    if not chunks:
        return (
            "I couldn’t find any CME activities that match your question in the current catalog.",
            [],
        )

    # -------------------------------------------------------------------------
    # 2. Build physician profile (DB + request overrides)
    # -------------------------------------------------------------------------
    profile: Dict[str, Any] = build_effective_physician_profile(db, request)

    completed_cme_ids = set(profile.get("completed_cme_ids") or [])
    min_credits = profile.get("min_credits")
    preferred_format = profile.get("preferred_format")
    credit_type_pref = profile.get("credit_type")

    # Normalize format preference
    if isinstance(preferred_format, str):
        preferred_format = preferred_format.strip().lower()

    t_after_profile = time.perf_counter()
    logger.info(
        "[CME_QUERY] Physician profile built in %.3fs",
        t_after_profile - t_after_vector,
    )

    # -------------------------------------------------------------------------
    # 3. Group chunks by CME event & score them
    # -------------------------------------------------------------------------
    cme_map: Dict[int, Dict[str, Any]] = {}
    total_chunks = len(chunks)

    for idx, ch in enumerate(chunks):
        cme_id = ch.get("source_id")
        if cme_id is None:
            continue

        # Simple rank-based score: earlier = higher
        score = float(total_chunks - idx)

        entry = cme_map.setdefault(
            int(cme_id),
            {"score": 0.0, "chunks": []},
        )
        entry["score"] += score
        entry["chunks"].append(ch)

    sorted_events = sorted(
        cme_map.items(),
        key=lambda tup: tup[1]["score"],
        reverse=True,
    )

    candidate_ids = [cid for cid, _ in sorted_events]

    # -------------------------------------------------------------------------
    # 4. Load CME metadata from DB
    # -------------------------------------------------------------------------
    events = (
        db.query(CMEEvent)
        .filter(CMEEvent.id.in_(candidate_ids))
        .all()
    )
    events_by_id: Dict[int, CMEEvent] = {int(e.id): e for e in events}

    t_after_db = time.perf_counter()
    logger.info(
        "[CME_QUERY] Loaded %d CME events from DB in %.3fs",
        len(events),
        t_after_db - t_after_profile,
    )

    # -------------------------------------------------------------------------
    # 5. Apply basic personalization filters
    # -------------------------------------------------------------------------
    filtered_events: List[Tuple[int, Dict[str, Any], CMEEvent]] = []

    def _eligible(ev: CMEEvent) -> bool:
        # Exclude CME already completed by this physician
        if ev.id in completed_cme_ids:
            return False

        # Minimum credits filter
        if min_credits is not None:
            try:
                ev_credits = float(ev.credits or 0)
            except Exception:
                ev_credits = 0.0
            if ev_credits < float(min_credits):
                return False

        # Preferred format filter
        if preferred_format:
            ev_fmt = (ev.format or "").strip().lower()
            if ev_fmt and ev_fmt != preferred_format:
                return False

        # Credit type preference (soft filter)
        if credit_type_pref:
            ev_ct = (ev.credit_type or "").strip().lower()
            if ev_ct and credit_type_pref.strip().lower() not in ev_ct:
                # Soft preference: we do NOT reject, but could downrank later.
                pass

        return True

    for cme_id, meta in sorted_events:
        ev = events_by_id.get(int(cme_id))
        if not ev:
            continue

        if not _eligible(ev):
            continue

        filtered_events.append((int(cme_id), meta, ev))
        if len(filtered_events) >= max_events:
            break

    # If filters were too strict, fall back to unfiltered top events
    if not filtered_events:
        filtered_events = []
        for cme_id, meta in sorted_events[:max_events]:
            ev = events_by_id.get(int(cme_id))
            if ev:
                filtered_events.append((int(cme_id), meta, ev))

    if not filtered_events:
        return (
            "I found CME content in the system, but none matched the filters/preferences provided.",
            [],
        )

    # -------------------------------------------------------------------------
    # 6. Build context blocks for LLM
    # -------------------------------------------------------------------------
    context_blocks: List[str] = []

    for rank_idx, (cme_id, meta, ev) in enumerate(filtered_events, start=1):
        chunks_text = "\n\n".join(
            ch.get("chunk_text", "")
            for ch in meta["chunks"]
            if ch.get("chunk_text")
        )

        title = getattr(ev, "title", "") or ""
        provider_name = getattr(ev, "provider_name", "") or ""

        credits = getattr(ev, "credits", None)
        credits_str = f"{credits} credits" if credits is not None else "Credits: N/A"

        credit_type = getattr(ev, "credit_type", "") or ""
        ev_format = getattr(ev, "format", "") or ""
        audience = getattr(ev, "audience", "") or ""

        raw_url = getattr(ev, "url", None)
        # 🔹 URL fallback so the LLM & UI always have something clickable
        url = raw_url or f"https://mycertiq-demo.local/cme/{cme_id}"

        context_blocks.append(
            f"CME ID: {cme_id}\n"
            f"Rank: {rank_idx}\n"
            f"Title: {title}\n"
            f"Provider: {provider_name}\n"
            f"{credits_str}\n"
            f"Credit Type: {credit_type}\n"
            f"Format: {ev_format}\n"
            f"Audience: {audience}\n"
            f"URL: {url}\n"
            f"Content Snippets:\n{chunks_text}"
        )

    context_str = "\n\n-----\n\n".join(context_blocks)

    t_after_context = time.perf_counter()
    logger.info(
        "[CME_QUERY] Built LLM context for %d CME events in %.3fs",
        len(filtered_events),
        t_after_context - t_after_db,
    )

    # -------------------------------------------------------------------------
    # 6b. Personalized physician context
    # -------------------------------------------------------------------------
    missing_reqs = profile.get("missing_requirements") or []
    completed_ids = profile.get("completed_cme_ids") or []

    physician_profile_block = (
        "Physician Profile (if available):\n"
        f"- Physician ID: {profile.get('physician_id')}\n"
        f"- Specialty: {profile.get('specialty')}\n"
        f"- State: {profile.get('state')}\n"
        f"- Preferred format: {profile.get('preferred_format')}\n"
        f"- Minimum credits per activity: {profile.get('min_credits')}\n"
        f"- Preferred credit type: {profile.get('credit_type')}\n"
        f"- Travel ok: {profile.get('travel_ok')}\n"
        f"- Missing requirements (if any): "
        f"{', '.join(missing_reqs) if missing_reqs else 'None listed'}\n"
        f"- Completed CME IDs (avoid recommending again): {completed_ids}\n"
    )

    system_msg = (
        "You are an assistant helping physicians choose CME activities.\n"
        "You will receive:\n"
        "1) The physician's question.\n"
        "2) A set of candidate CME activities (with IDs, titles, providers, credits, URLs, and content snippets).\n"
        "3) A physician profile with specialty, state, preferences, and any missing requirements.\n\n"
        "Your job is to:\n"
        "- Answer the physician's question in clear, practical clinical language.\n"
        "- Prefer CME activities that match the physician's specialty, state, format and credit preferences, "
        "and outstanding requirements.\n"
        "- Avoid recommending CME that is already listed as completed, unless there are no other good options.\n"
        "- ONLY use the CME activities provided in the context; do NOT invent new courses.\n"
        "- Then recommend the best 3–5 CME activities, based on the question AND the profile.\n"
        "- If information about credits or URLs is missing, just omit it."
    )

    user_msg = (
        f"Physician Question:\n{question}\n\n"
        f"{physician_profile_block}\n\n"
        f"CME Context:\n{context_str}\n\n"
        "Write your answer in this structure:\n"
        "1. A concise 1–3 paragraph answer to the question, explicitly tailoring it to the "
        "physician's specialty and state when relevant.\n"
        "2. A bulleted list titled 'Recommended CME Activities' with each bullet containing:\n"
        "   - CME ID\n"
        "   - Title\n"
        "   - Provider (if available)\n"
        "   - Credits (if available)\n"
        "   - Format (online/live, etc.)\n"
        "   - URL (if available)\n"
        "3. Briefly explain why each activity is a good match for this physician and how it relates "
        "to their missing requirements or preferences when applicable.\n"
    )

    # -------------------------------------------------------------------------
    # 7. Call OpenAI LLM for real answer
    # -------------------------------------------------------------------------
    t_llm_start = time.perf_counter()
    try:
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL or "gpt-4o-mini",
            temperature=0.4,
            max_tokens=600,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

        # openai==2.x message access pattern
        answer_text = completion.choices[0].message.content.strip()
        t_after_llm = time.perf_counter()
        logger.info(
            "[CME_QUERY] LLM call succeeded in %.3fs",
            t_after_llm - t_llm_start,
        )

    except Exception as e:
        t_after_llm = time.perf_counter()
        logger.warning(
            "[CME_QUERY] LLM call failed in %.3fs: %s",
            t_after_llm - t_llm_start,
            e,
        )
        # Fallback: never break API
        answer_text = (
            "I found CME activities matching your question, but could not "
            "generate a personalized explanation at this moment. "
            "Here are the recommended CME activities based on semantic relevance."
        )

    # -------------------------------------------------------------------------
    # 8. Build structured recommendations (for UI / API clients)
    # -------------------------------------------------------------------------
    recommendations: List[CMERecommendation] = []

    max_score = filtered_events[0][1]["score"] if filtered_events else 1.0

    for rank_idx, (cme_id, meta, ev) in enumerate(filtered_events, start=1):
        title = getattr(ev, "title", f"CME {cme_id}")
        provider_name = getattr(ev, "provider_name", None)
        credits = getattr(ev, "credits", None)

        raw_url = getattr(ev, "url", None)
        rec_url = raw_url or f"https://mycertiq-demo.local/cme/{cme_id}"

        raw_score = float(meta["score"])
        norm_score = raw_score / max_score if max_score else 0.0

        recommendations.append(
            CMERecommendation(
                cme_event_id=int(cme_id),
                title=title,
                provider=provider_name,
                credit_hours=float(credits) if credits is not None else None,
                url=rec_url,
                score=norm_score,
                rank=rank_idx,
                reason=(
                    "High semantic similarity to your question and alignment with your "
                    "profile/preferences."
                ),
            )
        )

    t_end = time.perf_counter()
    logger.info(
        "[CME_QUERY] Total run_cme_query time: %.3fs",
        t_end - t_start,
    )

    return answer_text, recommendations
