"""Streamlit front-end for the MAHSUDo-guide conversational assistant.

Run with:
    streamlit run streamlit_app.py

Reuses the same FastAPI backend services (retrieval, agent, timezone) so the
answers, citations and follow-up behaviour match the web app exactly.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Chunk, Document  # noqa: E402
from app.services.agent import answer_question  # noqa: E402
from app.utils.time import format_pakistan, pakistan_now  # noqa: E402

st.set_page_config(
    page_title="MAHSUDo-guide Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROGRAMS = [
    "",
    "MBBS",
    "BDS",
    "Pharm-D",
    "Allied Health Sciences",
    "Nursing",
    "Physiotherapy",
]

SCHOOLS = [
    "MBBS",
    "BDS",
    "Pharm-D",
    "Nursing",
]


@st.cache_resource(show_spinner=False)
def bootstrap() -> dict:
    init_db()
    db = SessionLocal()
    try:
        docs = db.scalar(select(func.count(Document.id))) or 0
        chunks = db.scalar(select(func.count(Chunk.id))) or 0
        if docs == 0:
            from app.cli import (
                create_admin,
                ingest_pages,
                seed_admissions,
                seed_institutions_and_programs,
                seed_sources,
            )
            from app.config import settings

            try:
                sources = seed_sources(db)
                seed_admissions(db, sources)
                ingest_pages(db, sources, sources)
                seed_institutions_and_programs(db, sources, offline=True)
                if settings.admin_seed_password != "change-me-in-production":
                    create_admin(db, settings.admin_seed_email, settings.admin_seed_password)
                db.commit()
            except Exception:
                db.rollback()
            docs = db.scalar(select(func.count(Document.id))) or 0
            chunks = db.scalar(select(func.count(Chunk.id))) or 0
        return {"documents": docs, "chunks": chunks}
    finally:
        db.close()


def ask(message: str, history: list[dict], program: str | None) -> dict:
    db = SessionLocal()
    try:
        answer = answer_question(
            db,
            message,
            program=program or None,
            history=history,
        )
        return answer.as_dict()
    finally:
        db.close()


def render_citations(citations: list[dict]) -> None:
    if not citations:
        st.caption("No official sources matched this question.")
        return
    with st.expander(f"Sources ({len(citations)}) — official documents cited"):
        for c in citations:
            badge = {
                "verified": "✅ verified",
                "unverified": "⚠️ unverified",
                "historical": "🗄 historical",
                "conflicting": "⚠️ conflicting sources",
            }.get(c.get("verification_status", ""), c.get("verification_status", ""))
            demo = " (demo record)" if c.get("is_demo") else ""
            st.markdown(
                f"- [{c['title']}]({c['url']})  \n"
                f"  `{badge}`{demo} — published: {c.get('publication_date') or 'n/a'} — "
                f"retrieved: {c.get('retrieved_at') or 'n/a'}"
            )


def main() -> None:
    state = bootstrap()

    if "st_messages" not in st.session_state:
        st.session_state.st_messages = []
    if "st_program" not in st.session_state:
        st.session_state.st_program = ""

    with st.sidebar:
        st.title("🎓 MAHSUDo-guide")
        st.caption("Source-aware KMU admissions guidance")
        now = pakistan_now()
        st.markdown(
            f"**🕒 Peshawar time**  \n{now:%A, %d %B %Y}  \n{now:%I:%M:%S %p} (Asia/Karachi)"
        )
        st.divider()
        st.session_state.st_program = st.selectbox(
            "Focus program (optional)",
            PROGRAMS,
            index=PROGRAMS.index(st.session_state.st_program) if st.session_state.st_program else 0,
        )
        if st.button("🆕 New chat", use_container_width=True):
            st.session_state.st_messages = []
            st.rerun()
        st.divider()
        st.caption(
            f"Knowledge base: {state['documents']} documents, {state['chunks']} chunks.\n\n"
            "Independent project. Not an official KMU service."
        )

    st.header("Admissions Assistant")

    for msg in st.session_state.st_messages:
        with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "🧑‍🎓"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                for d in msg.get("disclaimers", []):
                    st.warning(d)
                if msg.get("missing_information"):
                    st.info("Missing / needs official confirmation: " + "; ".join(msg["missing_information"]))
                if msg.get("blocked_prompt_injection"):
                    st.error("Blocked unsafe instruction embedded in the source text.")
                render_citations(msg.get("citations", []))
                meta = f"{msg['meta']} • {msg['time']}"
                st.caption(meta)

    user_input = st.chat_input(
        "Ask about KMU admissions: aggregate, eligibility, deadlines, programs…"
    )

    if user_input:
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.st_messages
        ]
        st.session_state.st_messages.append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("Searching official documents…"):
                started = time.perf_counter()
                result = ask(user_input, history, st.session_state.st_program)
                elapsed_ms = int((time.perf_counter() - started) * 1000)

            st.markdown(result["answer"])
            for d in result["disclaimers"]:
                st.warning(d)
            if result["missing_information"]:
                st.info(
                    "Missing / needs official confirmation: "
                    + "; ".join(result["missing_information"])
                )
            if result["blocked_prompt_injection"]:
                st.error("Blocked unsafe instruction embedded in the source text.")
            render_citations(result["citations"])

            provider = (
                f"AI model ({result['generated_by']})"
                if result["provider_configured"]
                else "extractive mode — no AI provider configured"
            )
            meta = f"{provider} • {elapsed_ms} ms • intent: {result['intent']}"
            st.caption(meta)
            msg_time = format_pakistan(pakistan_now())
            result_meta = meta

        st.session_state.st_messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "citations": result["citations"],
                "disclaimers": result["disclaimers"],
                "missing_information": result["missing_information"],
                "blocked_prompt_injection": result["blocked_prompt_injection"],
                "meta": result_meta,
                "time": msg_time,
            }
        )
        st.rerun()


if __name__ == "__main__":
    main()
