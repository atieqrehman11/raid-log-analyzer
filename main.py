"""
Streamlit MVP UI - Project Predictive Analyzer (Demo-Optimized + Explainability)

Enhancements:
- Risk-to-Issue prediction badge
- "Why these risks?" drill-down (explainability layer)
- Each factor now has reasoning from LLM

Setup:
pip install streamlit pandas openpyxl openai
export OPENAI_API_KEY=your_key
streamlit run app.py
"""

import json
import pandas as pd

try:
    import streamlit as st
    from openai import OpenAI
    STREAMLIT_AVAILABLE = True
except ModuleNotFoundError:
    STREAMLIT_AVAILABLE = False

# -----------------------------
# LLM
# -----------------------------

def get_llm_client():
    return OpenAI()


def analyze_with_llm(raid_text):
    client = get_llm_client()

    prompt = f"""
You are a project risk analysis engine.

Return ONLY valid JSON in this exact format:
{{
  "score": number,
  "status": "On Track | At Risk | Critical",
  "confidence": number,
  "risk_to_issue_count": number,
  "factors": [
    {{"title": string, "reason": string}},
    {{"title": string, "reason": string}},
    {{"title": string, "reason": string}},
    {{"title": string, "reason": string}},
    {{"title": string, "reason": string}}
  ],
  "summary": string,
  "recommendations": [string, string, string]
}}

Rules:
- Exactly 5 factors
- Each factor must include a short title and a clear reason
- Reasons should explain WHY the risk matters

RAID DATA:
{raid_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        return {
            "score": 0,
            "status": "Error",
            "confidence": 0,
            "risk_to_issue_count": 0,
            "factors": [
                {"title": "Parsing Error", "reason": content}
            ] * 5,
            "summary": content,
            "recommendations": ["Check LLM output format"]
        }

# -----------------------------
# UI Helpers
# -----------------------------

def get_status_color(score):
    if score >= 75:
        return "#16a34a"
    elif score >= 50:
        return "#f59e0b"
    else:
        return "#dc2626"


def render_score_card(score, status, confidence):
    color = get_status_color(score)

    st.markdown(f"""
    <div style="padding:20px;border-radius:12px;background-color:{color}20;border:2px solid {color};text-align:center;">
        <h2 style="color:{color}; margin:0;">Health Score</h2>
        <h1 style="color:{color}; font-size:48px; margin:0;">{score}</h1>
        <p style="font-size:18px; margin:0;"><b>{status}</b></p>
        <p style="margin:0;">Confidence: {confidence}%</p>
    </div>
    """, unsafe_allow_html=True)


def render_prediction_badge(count):
    if count == 0:
        st.success("✅ No immediate risk-to-issue escalation detected")
    elif count <= 2:
        st.warning(f"⚠️ {count} risk(s) likely to convert into issues")
    else:
        st.error(f"🚨 {count} risks likely to convert into issues soon")

# -----------------------------
# App
# -----------------------------

def run_app():
    st.set_page_config(page_title="Project Predictive Analyzer", layout="wide")

    st.title("📊 Project Predictive Analyzer")
    st.markdown("### 🚀 From RAID Logs → Predictive Insights in Seconds")

    uploaded_file = st.file_uploader("Upload RAID Excel", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file, sheet_name=None)
        st.success("File uploaded successfully")

        with st.expander("📂 Preview RAID Data"):
            for sheet, data in df.items():
                st.subheader(sheet)
                st.dataframe(data.head())

        if st.button("⚡ Analyze Project Health"):
            with st.spinner("AI analyzing hidden risk signals..."):
                raid_text = ""
                for sheet, data in df.items():
                    raid_text += f"\n--- {sheet} ---\n"
                    raid_text += data.head(10).to_string()

                result = analyze_with_llm(raid_text)

            st.markdown("---")

            # HERO SCORE
            render_score_card(result["score"], result["status"], result["confidence"])

            # PREDICTION BADGE
            render_prediction_badge(result.get("risk_to_issue_count", 0))

            st.markdown("---")

            # FACTORS WITH DRILL-DOWN
            st.subheader("🔍 Top Risk Drivers (Click to expand)")

            for f in result["factors"]:
                with st.expander(f["title"]):
                    st.write(f["reason"])

            st.markdown("---")

            # SUMMARY
            st.subheader("🧠 Executive Summary")
            st.info(result["summary"])

            st.markdown("---")

            # RECOMMENDATIONS
            st.subheader("✅ Recommended Actions")
            for r in result["recommendations"]:
                st.success(r)

            st.markdown("---")
            st.subheader("📈 Health Trend (Early Warning Signals)")

            trend_data = pd.DataFrame({
                "Day": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "Score": [82, 78, 74, 70, result["score"]]
            })

            st.line_chart(trend_data.set_index("Day"))

    else:
        st.info("👈 Upload a RAID Excel file to begin analysis")

# -----------------------------
# Entry
# -----------------------------

if __name__ == "__main__":
    if STREAMLIT_AVAILABLE:
        run_app()
    else:
        print("Install streamlit to run the UI")
