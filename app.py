"""AI Learning Roadmap Generator
Streamlit UI + Google Gemini Flash.

Run locally:  streamlit run app.py
"""

import json
import os
import re

import streamlit as st

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
DEFAULT_MODEL = "gemini-3.5-flash"  # override with GEMINI_MODEL in secrets/env
LEVELS = ["Beginner", "Intermediate", "Advanced"]
MAX_RETRIES = 2

st.set_page_config(page_title="AI Learning Roadmap Generator", page_icon="🧭", layout="wide")


# --------------------------------------------------------------------------- #
# Helpers (pure functions - no Streamlit calls, easy to test)
# --------------------------------------------------------------------------- #
def get_secret(name: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass  # no secrets.toml present
    return os.environ.get(name, default)


def to_weeks(amount: int, unit: str) -> int:
    return amount * 4 if unit == "Months" else amount


def build_prompt(field: str, level: str, total_weeks: int, hours_per_week: int) -> str:
    total_hours = total_weeks * hours_per_week
    return f"""You are an expert curriculum designer and career mentor.
Create a realistic, practical learning roadmap.

LEARNER PROFILE
- Field / domain: {field}
- Current skill level: {level}
- Total time available: {total_weeks} weeks
- Study time per week: {hours_per_week} hours (about {total_hours} hours total)

RULES
1. Tailor content to the {level} level. Do not repeat basics for Intermediate/Advanced learners.
2. Split the roadmap into 3 to 6 sequential phases. The phase duration_weeks values must add up to {total_weeks}.
3. Each phase must have concrete topics (4-8), 2-4 learning resources, one hands-on project and a measurable milestone.
4. For resources give the NAME and TYPE only (course, book, docs, video, tool, practice site). Do NOT include URLs.
5. Be specific (name real tools, libraries, concepts) rather than generic.

Return ONLY valid JSON, no markdown fences, using exactly this schema:
{{
  "title": "string",
  "overview": "2-3 sentence summary of the journey",
  "prerequisites": ["string"],
  "phases": [
    {{
      "title": "string",
      "duration_weeks": 1,
      "goal": "string",
      "topics": ["string"],
      "resources": [{{"name": "string", "type": "string"}}],
      "project": "string",
      "milestone": "string"
    }}
  ],
  "capstone_project": "string",
  "next_steps": ["string"]
}}"""


def extract_json(text: str) -> dict:
    """Parse JSON from a model response, tolerating code fences / extra text."""
    if not text:
        raise ValueError("Empty response from model.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in model response.")
        return json.loads(cleaned[start : end + 1])


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def normalize_roadmap(data: dict) -> dict:
    """Validate and coerce the model output so the UI never crashes."""
    if not isinstance(data, dict):
        raise ValueError("Roadmap must be a JSON object.")
    phases = []
    for p in _as_list(data.get("phases")):
        if not isinstance(p, dict):
            continue
        resources = []
        for r in _as_list(p.get("resources")):
            if isinstance(r, dict):
                resources.append({"name": str(r.get("name", "")).strip(), "type": str(r.get("type", "")).strip()})
            elif isinstance(r, str):
                resources.append({"name": r.strip(), "type": ""})
        try:
            weeks = max(1, int(p.get("duration_weeks", 1)))
        except (TypeError, ValueError):
            weeks = 1
        phases.append(
            {
                "title": str(p.get("title", "Untitled phase")),
                "duration_weeks": weeks,
                "goal": str(p.get("goal", "")),
                "topics": [str(t) for t in _as_list(p.get("topics"))],
                "resources": [r for r in resources if r["name"]],
                "project": str(p.get("project", "")),
                "milestone": str(p.get("milestone", "")),
            }
        )
    if not phases:
        raise ValueError("Model returned no phases.")
    return {
        "title": str(data.get("title", "Your Learning Roadmap")),
        "overview": str(data.get("overview", "")),
        "prerequisites": [str(x) for x in _as_list(data.get("prerequisites"))],
        "phases": phases,
        "capstone_project": str(data.get("capstone_project", "")),
        "next_steps": [str(x) for x in _as_list(data.get("next_steps"))],
    }


def roadmap_to_markdown(rm: dict) -> str:
    lines = [f"# {rm['title']}", "", rm["overview"], ""]
    if rm["prerequisites"]:
        lines += ["## Prerequisites"] + [f"- {x}" for x in rm["prerequisites"]] + [""]
    week = 1
    for i, p in enumerate(rm["phases"], 1):
        end = week + p["duration_weeks"] - 1
        lines += [f"## Phase {i}: {p['title']} (Weeks {week}-{end})", "", f"**Goal:** {p['goal']}", ""]
        lines += ["**Topics**"] + [f"- {t}" for t in p["topics"]] + [""]
        if p["resources"]:
            lines += ["**Resources**"]
            lines += [f"- {r['name']}" + (f" ({r['type']})" if r["type"] else "") for r in p["resources"]] + [""]
        lines += [f"**Project:** {p['project']}", "", f"**Milestone:** {p['milestone']}", ""]
        week = end + 1
    if rm["capstone_project"]:
        lines += ["## Capstone Project", rm["capstone_project"], ""]
    if rm["next_steps"]:
        lines += ["## Next Steps"] + [f"- {x}" for x in rm["next_steps"]] + [""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Gemini call
# --------------------------------------------------------------------------- #
def generate_roadmap(api_key: str, model: str, prompt: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.7,
    )
    last_error = None
    for _ in range(MAX_RETRIES + 1):
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        try:
            return normalize_roadmap(extract_json(response.text))
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc  # retry on malformed output
    raise ValueError(f"Could not parse a valid roadmap after {MAX_RETRIES + 1} attempts: {last_error}")


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
def render_roadmap(rm: dict, total_weeks: int) -> None:
    st.header(rm["title"])
    if rm["overview"]:
        st.write(rm["overview"])

    planned = sum(p["duration_weeks"] for p in rm["phases"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Phases", len(rm["phases"]))
    c2.metric("Planned duration", f"{planned} weeks")
    c3.metric("Requested", f"{total_weeks} weeks")

    if rm["prerequisites"]:
        with st.expander("✅ Prerequisites", expanded=False):
            for item in rm["prerequisites"]:
                st.markdown(f"- {item}")

    week = 1
    for i, p in enumerate(rm["phases"], 1):
        end = week + p["duration_weeks"] - 1
        with st.expander(f"Phase {i}: {p['title']}  •  Weeks {week}-{end}", expanded=(i == 1)):
            st.markdown(f"**🎯 Goal:** {p['goal']}")
            left, right = st.columns(2)
            with left:
                st.markdown("**📚 Topics**")
                for t in p["topics"]:
                    st.markdown(f"- {t}")
            with right:
                st.markdown("**🔗 Resources**")
                for r in p["resources"]:
                    st.markdown(f"- {r['name']}" + (f" *({r['type']})*" if r["type"] else ""))
            st.info(f"🛠️ **Project:** {p['project']}")
            st.success(f"🏁 **Milestone:** {p['milestone']}")
        week = end + 1

    if rm["capstone_project"]:
        st.subheader("🚀 Capstone Project")
        st.write(rm["capstone_project"])
    if rm["next_steps"]:
        st.subheader("➡️ Next Steps")
        for item in rm["next_steps"]:
            st.markdown(f"- {item}")

    st.download_button(
        "⬇️ Download roadmap (Markdown)",
        data=roadmap_to_markdown(rm),
        file_name="learning_roadmap.md",
        mime="text/markdown",
    )


def main() -> None:
    st.title("🧭 AI Learning Roadmap Generator")
    st.caption("Tell me what you want to learn and how much time you have. I'll build your plan.")

    # ---- Sidebar: API key ----
    api_key = get_secret("GEMINI_API_KEY")
    model = get_secret("GEMINI_MODEL", DEFAULT_MODEL)
    with st.sidebar:
        st.header("⚙️ Settings")
        if not api_key:
            api_key = st.text_input("Gemini API key", type="password", help="Get one free at aistudio.google.com")
        else:
            st.success("API key loaded from secrets/environment.")
        model = st.text_input("Model", value=model)

    # ---- Input form ----
    with st.form("roadmap_form"):
        field = st.text_input("Field / domain", placeholder="e.g. Data Science, Web Development, Cybersecurity")
        c1, c2, c3 = st.columns(3)
        level = c1.selectbox("Skill level", LEVELS)
        amount = c2.number_input("Time to learn", min_value=1, max_value=60, value=12, step=1)
        unit = c3.selectbox("Unit", ["Weeks", "Months"])
        hours = st.slider("Hours you can study per week", min_value=1, max_value=60, value=8)
        submitted = st.form_submit_button("Generate roadmap ✨", use_container_width=True)

    if submitted:
        field = field.strip()
        total_weeks = to_weeks(int(amount), unit)
        if not field:
            st.warning("Please enter a field or domain.")
        elif len(field) > 100:
            st.warning("Please keep the field under 100 characters.")
        elif not api_key:
            st.error("Please provide a Gemini API key in the sidebar.")
        else:
            try:
                with st.spinner("Designing your roadmap..."):
                    prompt = build_prompt(field, level, total_weeks, int(hours))
                    rm = generate_roadmap(api_key, model.strip() or DEFAULT_MODEL, prompt)
                st.session_state["roadmap"] = rm
                st.session_state["total_weeks"] = total_weeks
            except Exception as exc:  # network, quota, auth, parse errors
                st.session_state.pop("roadmap", None)
                st.error(f"Something went wrong: {exc}")

    if "roadmap" in st.session_state:
        render_roadmap(st.session_state["roadmap"], st.session_state.get("total_weeks", 0))


if __name__ == "__main__":
    main()
