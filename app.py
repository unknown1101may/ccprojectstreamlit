"""
app.py — Person 1: Frontend + Upload System
Responsibility: UI, image upload, result display, history view.

Run with:  streamlit run app.py
"""

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
from PIL import Image
from backend import process_image, save_result, get_history, clear_history, upload_to_storage
from config import DETECTION_MODE, CONFIDENCE_THRESHOLD, FIREBASE_ENABLED, CLOUD_FUNCTION_URL

# ---------------------------------------------------------------------------
# Page configuration — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Image Authenticity Detector",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — white background, clean typography
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Force white background everywhere */
        .stApp, [data-testid="stAppViewContainer"],
        [data-testid="block-container"],
        [data-testid="stHeader"] {
            background-color: #ffffff !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #f7f7f7 !important;
            border-right: 1px solid #e5e5e5;
        }

        /* Typography */
        h1 { font-size: 1.8rem !important; font-weight: 700; color: #111111; }
        h2 { font-size: 1.3rem !important; font-weight: 600; color: #222222; }
        h3 { font-size: 1.1rem !important; font-weight: 600; color: #333333; }
        p, li, label { color: #444444; }

        /* Result cards */
        .result-card {
            padding: 1.2rem 1.5rem;
            border-radius: 8px;
            border: 1px solid #dddddd;
            margin-top: 0.8rem;
        }
        .card-ai   { background-color: #fff8e1; border-left: 4px solid #f59e0b; }
        .card-real { background-color: #f0fdf4; border-left: 4px solid #22c55e; }
        .card-error{ background-color: #fff1f2; border-left: 4px solid #ef4444; }

        /* Metric boxes */
        .metric-box {
            background: #f7f7f7;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 0.9rem 1rem;
            text-align: center;
        }
        .metric-box .value { font-size: 1.6rem; font-weight: 700; color: #111111; }
        .metric-box .label { font-size: 0.8rem; color: #777777; margin-top: 2px; }

        /* Confidence bar */
        .conf-bar-bg {
            background: #e5e7eb;
            border-radius: 6px;
            height: 10px;
            margin-top: 4px;
        }
        .conf-bar-fill {
            height: 10px;
            border-radius: 6px;
        }

        /* Demo badge */
        .badge-demo {
            display: inline-block;
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 8px;
        }
        .badge-live {
            display: inline-block;
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 8px;
        }

        /* Divider */
        hr { border: none; border-top: 1px solid #e5e5e5; margin: 1.5rem 0; }

        /* Hide Streamlit branding */
        #MainMenu, footer { visibility: hidden; }

        /* File uploader */
        [data-testid="stFileUploaderDropzone"] {
            background-color: #fafafa !important;
            border: 2px dashed #cccccc !important;
            border-radius: 8px !important;
        }

        /* Table */
        .stDataFrame { border: 1px solid #e5e5e5; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Settings")

    mode_label = (
        '<span class="badge-live">Live API</span>'
        if DETECTION_MODE == "sightengine"
        else '<span class="badge-demo">Demo Mode</span>'
    )
    st.markdown(f"**Detection Mode** {mode_label}", unsafe_allow_html=True)

    if DETECTION_MODE == "demo":
        st.info(
            "Running in demo mode. Set `SIGHTENGINE_API_USER` and "
            "`SIGHTENGINE_API_SECRET` environment variables to enable "
            "real AI detection.",
            icon=None,
        )

    st.markdown("---")

    # Firebase status — read live from env so it reflects .env correctly
    import os
    _sa  = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
    _bkt = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    _cfn = os.getenv("CLOUD_FUNCTION_URL", "")

    st.markdown("**Firebase**", unsafe_allow_html=True)
    for label, value, ok_text, miss_text in [
        ("Storage bucket",     _bkt, _bkt,                    "not set"),
        ("Service account",    _sa,  "configured",             "not set"),
        
    ]:
        dot   = "🟢" if value else "🔴"
        shown = ok_text if value else miss_text
        st.markdown(
            f"<div style='font-size:0.82rem;margin:2px 0;'>"
            f"{dot} <b>{label}:</b> {shown}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("**Confidence Threshold**")
    st.markdown(
        f"Images with AI probability **>= {CONFIDENCE_THRESHOLD}** are "
        "labelled *AI-Generated*."
    )

    st.markdown("---")
    st.markdown("## System Architecture")
    st.markdown(
        """
**Layer 1 — Frontend** *(this app)*
- Streamlit UI
- Image upload via browser
- Result rendering

**Layer 2 — Serverless Backend**
- `backend.py` → Lambda-style handler
- Decision logic + threshold
- Session-based result store

**Layer 3 — AI Detection**
- Sightengine `genai` model
- Returns AI probability 0 – 1
- Confidence threshold applied
        """
    )

    st.markdown("---")
    if st.button("Clear History", use_container_width=True):
        clear_history()
        st.rerun()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("# AI Image Authenticity Detector")
st.markdown(
    "Upload an image to determine whether it was **AI-generated** or captured as a **real photograph**."
)
st.markdown("<hr>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main layout: upload (left) + result (right)
# ---------------------------------------------------------------------------
col_upload, col_result = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### Upload Image")
    uploaded_file = st.file_uploader(
        "Drag and drop or click to browse",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True, caption=uploaded_file.name)
        st.markdown(
            f"<p style='font-size:0.8rem;color:#888;'>"
            f"Format: {image.format or uploaded_file.type.split('/')[-1].upper()} &nbsp;|&nbsp; "
            f"Size: {image.width} x {image.height} px &nbsp;|&nbsp; "
            f"File: {round(uploaded_file.size / 1024, 1)} KB"
            f"</p>",
            unsafe_allow_html=True,
        )

        analyze_btn = st.button("Analyze Image", type="primary", use_container_width=True)
    else:
        analyze_btn = False


with col_result:
    st.markdown("### Detection Result")

    if uploaded_file is None:
        st.markdown(
            "<div class='result-card' style='color:#aaaaaa;text-align:center;padding:2.5rem;'>"
            "No image uploaded yet."
            "</div>",
            unsafe_allow_html=True,
        )

    elif analyze_btn:
        with st.spinner("Running detection..."):
            try:
                image_bytes = uploaded_file.getvalue()

                # Step 1: upload to Firebase Storage (if enabled)
                storage_url = None
                if FIREBASE_ENABLED:
                    try:
                        storage_url, _ = upload_to_storage(image_bytes, uploaded_file.name)
                    except Exception as upload_err:
                        st.warning(f"Storage upload skipped: {upload_err}")

                # Step 2: run detection (Cloud Function or local)
                result = process_image(image_bytes, uploaded_file.name)

                # Step 3: attach storage URL if available
                if storage_url:
                    result["storage_url"] = storage_url

                # Step 4: persist to Firestore / session state
                save_result(result)
                st.session_state["last_result"] = result
            except Exception as e:
                st.session_state["last_result"] = {"error": str(e)}

    # Display the latest result
    last = st.session_state.get("last_result")

    if last:
        if "error" in last:
            st.markdown(
                f"<div class='result-card card-error'>"
                f"<strong>Detection failed</strong><br>"
                f"<span style='font-size:0.85rem;'>{last['error']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            is_ai = last["label"] == "AI-Generated"
            card_cls = "card-ai" if is_ai else "card-real"
            verdict_color = "#b45309" if is_ai else "#166534"
            verdict_icon = "AI-Generated" if is_ai else "Real Photograph"

            st.markdown(
                f"<div class='result-card {card_cls}'>"
                f"<div style='font-size:1.4rem;font-weight:700;color:{verdict_color};'>"
                f"{verdict_icon}"
                f"</div>"
                f"<div style='font-size:0.85rem;color:#555;margin-top:4px;'>"
                f"File: {last['filename']}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Metrics row
            m1, m2, m3 = st.columns(3)
            with m1:
                pct = round(last["confidence"] * 100, 1)
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='value'>{pct}%</div>"
                    f"<div class='label'>Confidence</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with m2:
                ai_pct = round(last["ai_probability"] * 100, 1)
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='value'>{ai_pct}%</div>"
                    f"<div class='label'>AI Probability</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with m3:
                st.markdown(
                    f"<div class='metric-box'>"
                    f"<div class='value'>{last['size_kb']} KB</div>"
                    f"<div class='label'>File Size</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Confidence bar
            bar_color = "#f59e0b" if is_ai else "#22c55e"
            bar_width = round(last["confidence"] * 100, 1)
            st.markdown(
                f"<div style='margin-top:1rem;'>"
                f"<div style='font-size:0.8rem;color:#666;margin-bottom:4px;'>"
                f"Confidence — {bar_width}%</div>"
                f"<div class='conf-bar-bg'>"
                f"<div class='conf-bar-fill' style='width:{bar_width}%;background:{bar_color};'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            # Detail table
            st.markdown("<div style='margin-top:1.2rem;'>", unsafe_allow_html=True)
            st.markdown("**Details**")
            detail_rows = {
                "Timestamp":        last["timestamp"],
                "Detection Source": last["source"],
                "Threshold Used":   f"{last['threshold']}",
            }
            if last.get("storage_url"):
                detail_rows["Firebase Storage"] = "Uploaded"

            for k, v in detail_rows.items():
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"font-size:0.85rem;padding:4px 0;border-bottom:1px solid #f0f0f0;'>"
                    f"<span style='color:#777;'>{k}</span>"
                    f"<span style='color:#222;font-weight:500;'>{v}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if last.get("storage_url"):
                st.markdown(
                    f"<div style='margin-top:6px;font-size:0.78rem;color:#888;'>"
                    f"Stored at: <a href='{last['storage_url']}' target='_blank' "
                    f"style='color:#3b82f6;'>{last['storage_url'][:60]}...</a>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Detection History
# ---------------------------------------------------------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("### Detection History")

history = get_history()

if not history:
    st.markdown(
        "<p style='color:#aaa;font-size:0.9rem;'>No detections yet. Upload an image above.</p>",
        unsafe_allow_html=True,
    )
else:
    import pandas as pd

    rows = [
        {
            "Timestamp":    r["timestamp"],
            "Filename":     r["filename"],
            "Result":       r["label"],
            "AI Prob (%)":  round(r["ai_probability"] * 100, 1),
            "Confidence (%)": round(r["confidence"] * 100, 1),
            "Size (KB)":    r["size_kb"],
            "Source":       r["source"],
        }
        for r in history
    ]
    df = pd.DataFrame(rows)

    # Color Result column
    def color_result(val):
        if val == "AI-Generated":
            return "background-color: #fff8e1; color: #b45309;"
        return "background-color: #f0fdf4; color: #166534;"

    styled = df.style.applymap(color_result, subset=["Result"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Summary stats
    total = len(history)
    ai_count   = sum(1 for r in history if r["label"] == "AI-Generated")
    real_count = total - ai_count

    s1, s2, s3 = st.columns(3)
    for col, label, val in [
        (s1, "Total Analyzed", total),
        (s2, "AI-Generated",   ai_count),
        (s3, "Real",           real_count),
    ]:
        with col:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='value'>{val}</div>"
                f"<div class='label'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Architecture section (for project report reference)
# ---------------------------------------------------------------------------
st.markdown("<hr>", unsafe_allow_html=True)

with st.expander("System Architecture", expanded=False):
    st.markdown(
        """
```
User Browser
     |
     |  HTTP (image upload)
     v
+-----------------------------+
|   Streamlit Frontend        |  <-- Person 1
|   app.py                   |
|   - File uploader           |
|   - Result renderer         |
|   - History table           |
+-----------------------------+
     |
     |  Function call
     v
+-----------------------------+
|   Serverless Handler        |  <-- Person 2
|   backend.py                |
|   - process_image()         |
|   - Decision logic          |
|   - Session store           |
+-----------------------------+
     |
     |  HTTP / SDK call
     v
+-----------------------------+
|   AI Detection Layer        |  <-- Person 3
|   detector.py               |
|   - Sightengine genai model |
|   - Returns AI probability  |
|   - Confidence threshold    |
+-----------------------------+
```

**Decision Logic (backend.py)**
```python
if ai_probability >= CONFIDENCE_THRESHOLD:   # default 0.7
    result = "AI-Generated"
else:
    result = "Real"
```

**Data Flow**
1. User uploads image via browser
2. Streamlit passes raw bytes to `process_image()`
3. `process_image()` calls `detector.detect()`
4. Detector calls Sightengine API (or demo mode)
5. Result returned → stored in session state → rendered in UI

**Cloud Services Used**
- Sightengine AI detection API (free tier: 500 ops/month)
- Deployable on: Streamlit Cloud (free), AWS, GCP, Azure
        """
    )
