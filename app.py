"""
app.py — Single Page Unified Dashboard for FaceRecAtd
"""

import streamlit as st
import sys, os
from datetime import date, timedelta
import io
import gc
import pandas as pd
import plotly.express as px
from PIL import Image
import base64

sys.path.insert(0, os.path.dirname(__file__))

from core.database import (
    init_db, get_all_users, get_all_face_encodings, get_meal_logs,
    log_meal, add_user, deactivate_user, get_departments, toggle_food_program,
    get_today_meal_summary, get_daily_meal_counts, clear_meal_logs
)
from core.face_engine import encode_face, identify_faces, annotate_image
from utils.helpers import inject_css, records_to_df, df_to_csv_bytes

st.set_page_config(
    page_title="Face Tracking Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
inject_css()

# Clear RAM periodically
gc.collect()

@st.cache_data(ttl=600)
def get_cached_encodings():
    return get_all_face_encodings()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px;">
        <div style="font-size:2.5rem;"></div>
        <div style="font-weight:800; font-size:1.1rem; color:#e8eaf6;">FaceRecAtd</div>
        <div style="font-size:0.75rem; color:#4b5563;">Attendance System</div>
    </div>
    <div class="gradient-divider"></div>
    """, unsafe_allow_html=True)

    summary = get_today_meal_summary()
    st.markdown(f"""
    <div class="glass-card" style="padding:16px;">
        <div style="font-size:0.75rem; color:#6b7280; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px;">Today's Meal Logs</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="color:#9ca3af; font-size:0.85rem;">Breakfast</span>
            <span style="color:#00e676; font-weight:700;">{summary['meals']['Breakfast']}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="color:#9ca3af; font-size:0.85rem;">Lunch</span>
            <span style="color:#00e676; font-weight:700;">{summary['meals']['Lunch']}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="color:#9ca3af; font-size:0.85rem;">Dinner</span>
            <span style="color:#00e676; font-weight:700;">{summary['meals']['Dinner']}</span>
        </div>
        <div style="display:flex; justify-content:space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px;">
            <span style="color:#9ca3af; font-size:0.85rem;">Total Enrolled</span>
            <span style="color:#a9a4ff; font-weight:700;">{summary['total_enrolled']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='gradient-divider'></div>", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 20px 0 10px;">
    <h1 style="
        font-size:2rem; font-weight:800;
        background: linear-gradient(135deg, #6c63ff, #3ecfcf);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip:text;
        margin-bottom:4px;
    ">Dashboard</h1>
    <p style="color:#4b5563; font-size:0.9rem;">Mark attendance, register users, and view analytics</p>
</div>
""", unsafe_allow_html=True)

# ── Top Metric Row ─────────────────────────────────────────────────────────────
users = get_all_users()
active_users = [u for u in users if u["is_active"]]
today_records = get_meal_logs(date_from=date.today(), date_to=date.today())

m1, m2, m3, m4 = st.columns(4)
for col, val, label, icon in zip(
    [m1, m2, m3, m4],
    [summary['total_enrolled'], summary['meals']['Breakfast'], summary['meals']['Lunch'], summary['meals']['Dinner']],
    ["Users Enrolled", "Breakfasts Logged", "Lunches Logged", "Dinners Logged"],
    ["", "", "", ""]
):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_mark, tab_reg, tab_records, tab_reports, tab_users = st.tabs([
    "Mark Attendance",
    "Register User",
    "Records",
    "Reports",
    "Manage Users",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — MARK ATTENDANCE
# ════════════════════════════════════════════════════════════════════════════════
with tab_mark:
    st.markdown('<div class="section-title">Food Mess Scanner</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Use webcam snapshot or upload a photo to log current meal.</div>', unsafe_allow_html=True)

    from datetime import datetime
    now_hour = datetime.now().hour
    if 5 <= now_hour < 11:
        default_meal = "Breakfast"
    elif 11 <= now_hour < 16:
        default_meal = "Lunch"
    else:
        default_meal = "Dinner"
        
    current_meal = st.selectbox("Current Meal Phase", ["Breakfast", "Lunch", "Dinner"], index=["Breakfast", "Lunch", "Dinner"].index(default_meal))

    known = get_all_face_encodings()
    if not known:
        st.markdown('<div class="info-box">No registered faces yet. Go to the <b>Register User</b> tab first.</div>', unsafe_allow_html=True)
    else:
        method = st.radio("Input method:", ["Webcam Snapshot", "Upload Photo", "Live CCTV Scanner"], horizontal=True)

        img_pil = None
        if method == "Live CCTV Scanner":
            import cv2
            import time
            from datetime import datetime
            run_cctv = st.toggle("Turn on Live Scanner", key="live_cctv_toggle")
            if run_cctv:
                st.markdown('<div class="info-box">Streaming live camera feed...</div>', unsafe_allow_html=True)
                
                col_cam, col_log = st.columns([2.5, 1])
                with col_cam:
                    stframe = st.empty()
                    status_placeholder = st.empty()
                    
                with col_log:
                    st.markdown("<h4 style='color:#a9a4ff; margin-bottom:12px; font-weight:700;'>Recent Detections</h4>", unsafe_allow_html=True)
                    log_placeholder = st.empty()
                    
                if "scan_logs" not in st.session_state:
                    st.session_state.scan_logs = []
                    
                # render existing logs on load
                log_placeholder.markdown("".join(st.session_state.scan_logs), unsafe_allow_html=True)
                
                cap = cv2.VideoCapture(0)
                frame_count = 0
                latest_results = []
                
                # Cooldown dict to prevent log flooding (id: timestamp)
                last_seen_cooldown = {}
                
                try:
                    while run_cctv:
                        ret, frame = cap.read()
                        if not ret:
                            status_placeholder.error("Cannot read from webcam.")
                            break
                        
                        frame_count += 1
                        
                        # Convert to RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # We only run the heavy AI face recognition every 10 frames (approx 3 times a second)
                        if frame_count % 10 == 0:
                            # Downscale image to 1/4 size for much faster processing
                            small_frame = cv2.resize(frame_rgb, (0, 0), fx=0.25, fy=0.25)
                            pil_img = Image.fromarray(small_frame)
                            
                            # Try to identify faces
                            latest_results = identify_faces(pil_img, known)
                            
                            if latest_results:
                                for r in latest_results:
                                    if r["matched"]:
                                        user = r["user"]
                                        emp_id = user["employee_id"]
                                        now_time = time.time()
                                        
                                        # Only process logs for the side panel if it's been 5 seconds since we last saw them
                                        if emp_id not in last_seen_cooldown or (now_time - last_seen_cooldown[emp_id]) > 5:
                                            last_seen_cooldown[emp_id] = now_time
                                            
                                            status, ts = log_meal(user["user_id"], emp_id, current_meal)
                                            ts_str = ts.strftime("%H:%M:%S") if ts else datetime.now().strftime("%H:%M:%S")
                                            
                                            log_html = ""
                                            if status == "success":
                                                status_placeholder.markdown(f'<div class="success-box"><b>{user["name"]}</b> logged {current_meal} at {ts_str} (confidence: {r["confidence"]}%)</div>', unsafe_allow_html=True)
                                                log_html = f"<div style='border-left: 3px solid #00e676; padding-left: 10px; margin-bottom: 12px; background: rgba(0, 230, 118, 0.05); padding: 8px;'><span style='color:#9ca3af; font-size:0.75rem;'>{ts_str}</span><br><b style='font-size:0.95rem; color:#f8fafc;'>{user['name']}</b><br><span style='color:#00e676; font-size:0.8rem; font-weight:600;'>Logged {current_meal}</span></div>"
                                                
                                            elif status == "not_enrolled":
                                                status_placeholder.markdown(f'<div class="error-box"><b>{user["name"]}</b> is NOT enrolled in the food program!</div>', unsafe_allow_html=True)
                                                log_html = f"<div style='border-left: 3px solid #ff1744; padding-left: 10px; margin-bottom: 12px; background: rgba(255, 23, 68, 0.05); padding: 8px;'><span style='color:#9ca3af; font-size:0.75rem;'>{ts_str}</span><br><b style='font-size:0.95rem; color:#f8fafc;'>{user['name']}</b><br><span style='color:#ff1744; font-size:0.8rem; font-weight:600;'>Not Enrolled</span></div>"
                                                
                                            elif status == "already_logged":
                                                # Silently skip main status to avoid flickering, but add to side log
                                                log_html = f"<div style='border-left: 3px solid #a9a4ff; padding-left: 10px; margin-bottom: 12px; background: rgba(169, 164, 255, 0.05); padding: 8px;'><span style='color:#9ca3af; font-size:0.75rem;'>{ts_str}</span><br><b style='font-size:0.95rem; color:#f8fafc;'>{user['name']}</b><br><span style='color:#a9a4ff; font-size:0.8rem; font-weight:600;'>Already Logged</span></div>"
                                            
                                            if log_html:
                                                st.session_state.scan_logs.insert(0, log_html)
                                                st.session_state.scan_logs = st.session_state.scan_logs[:12] # Keep last 12
                                                log_placeholder.markdown("".join(st.session_state.scan_logs), unsafe_allow_html=True)
                        
                        # Draw the bounding boxes on the current frame using the cached latest_results
                        for r in latest_results:
                            top, right, bottom, left = r["location"]
                            # Scale back up since detection was on 1/4 size image
                            top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
                            
                            color = (0, 230, 118) if r["matched"] else (255, 23, 68)
                            cv2.rectangle(frame_rgb, (left, top), (right, bottom), color, 3)
                            
                            label = f'{r["user"]["name"]} ({r["user"]["employee_id"]})' if r["matched"] else "Unknown"
                            cv2.rectangle(frame_rgb, (left, bottom - 30), (right, bottom), color, cv2.FILLED)
                            cv2.putText(frame_rgb, label, (left + 6, bottom - 8), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 1)

                        # Display live feed smoothly with annotations
                        stframe.image(frame_rgb, width=600)
                        
                finally:
                    cap.release()
                    
        elif method == "Webcam Snapshot":
            enable_cam = st.checkbox("Turn on Camera", key="mark_cam_toggle")
            if enable_cam:
                cam = st.camera_input("Click to capture", key="mark_cam")
                if cam:
                    img_pil = Image.open(cam)
        else:
            up = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], key="mark_up")
            if up:
                img_pil = Image.open(up)

        if img_pil:
            with st.spinner("Recognizing faces…"):
                results = identify_faces(img_pil, known)

            if not results:
                st.markdown('<div class="error-box">No faces detected. Ensure good lighting.</div>', unsafe_allow_html=True)
            else:
                annotated = annotate_image(img_pil, results)
                st.image(annotated, caption="Recognition Result", use_container_width=True)

                st.markdown("---")
                marked_any = False
                for r in results:
                    if r["matched"]:
                        user = r["user"]
                        status, ts = log_meal(user["user_id"], user["employee_id"], current_meal)
                        ts_str = ts.strftime("%H:%M:%S") if ts else "—"
                        if status == "success":
                            st.markdown(f'<div class="success-box"><b>{user["name"]}</b> logged {current_meal} at {ts_str} (confidence: {r["confidence"]}%)</div>', unsafe_allow_html=True)
                        elif status == "not_enrolled":
                            st.markdown(f'<div class="error-box"><b>{user["name"]}</b> is NOT enrolled in the food program!</div>', unsafe_allow_html=True)
                        elif status == "already_logged":
                            st.markdown(f'<div class="info-box"><b>{user["name"]}</b> — already logged {current_meal} today.</div>', unsafe_allow_html=True)
                        marked_any = True
                    else:
                        st.markdown('<div class="error-box">Unknown face detected — not registered in the system.</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — REGISTER USER
# ════════════════════════════════════════════════════════════════════════════════
with tab_reg:
    if "reg_success_msg" in st.session_state:
        st.markdown(st.session_state.reg_success_msg, unsafe_allow_html=True)
        del st.session_state["reg_success_msg"]
        
    st.markdown('<div class="section-title">Register New User</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Add an employee or student to the facial recognition system.</div>', unsafe_allow_html=True)

    face_method_reg = st.radio(
        "Face Photo Source",
        ["Webcam", "Upload"],
        horizontal=True,
        key="reg_face_method",
    )

    face_img = None
    col_cap, col_prev = st.columns([1, 1])
    with col_cap:
        if face_method_reg == "Webcam":
            enable_cam_reg = st.checkbox("Turn on Camera", key="reg_cam_toggle")
            if enable_cam_reg:
                cam2 = st.camera_input("Capture face", key="reg_cam")
                if cam2:
                    face_img = Image.open(cam2)
                    st.session_state["reg_face_bytes"] = cam2.getvalue()
                elif st.session_state.get("reg_face_bytes"):
                    face_img = Image.open(io.BytesIO(st.session_state["reg_face_bytes"]))
            elif st.session_state.get("reg_face_bytes"):
                face_img = Image.open(io.BytesIO(st.session_state["reg_face_bytes"]))
        else:
            up2 = st.file_uploader("Upload face photo", type=["jpg", "jpeg", "png"], key="reg_up")
            if up2:
                face_img = Image.open(up2)
                st.session_state["reg_face_bytes"] = up2.getvalue()
            elif st.session_state.get("reg_face_bytes"):
                face_img = Image.open(io.BytesIO(st.session_state["reg_face_bytes"]))

    with col_prev:
        if face_img:
            # Convert PIL image to base64 for embedding in HTML card
            buffered = io.BytesIO()
            face_img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            st.markdown(f"""
            <div class="glass-card" style="min-height:280px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <img src="data:image/jpeg;base64,{img_str}" style="max-width:100%; border-radius:12px; margin-bottom:12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style='font-weight:600; font-size:0.8rem; color:#4ade80;'>Face Detected</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="glass-card" style="min-height:280px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <div style="color:#64748b; padding:20px 0;">
                    <div style="font-size:4rem; margin-bottom:12px; opacity:0.5;"></div>
                    <div style="font-size:1rem; font-weight:700; color:#94a3b8;">Face Preview</div>
                    <div style="font-size:0.8rem; margin-top:4px; opacity:0.8;">No photo captured yet</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    with st.form("register_form", clear_on_submit=True):
        col_form, col_form2 = st.columns(2)
        with col_form:
            name      = st.text_input("Full Name *", placeholder="e.g. Harshit Sharma")
            emp_id    = st.text_input("ID / Roll Number *", placeholder="e.g. EMP001")
        with col_form2:
            dept      = st.text_input("Department / Class", placeholder="e.g. Engineering")
            role      = st.selectbox("Role", ["employee", "student"])
            is_in_food_program = st.checkbox("Enroll in Food Program", value=True)

        submitted_reg = st.form_submit_button("Register User", use_container_width=True)

    if submitted_reg:
        # Re-load face from session
        _face_bytes = st.session_state.get("reg_face_bytes")
        if _face_bytes and face_img is None:
            face_img = Image.open(io.BytesIO(_face_bytes))

        errors = []
        if not name.strip():      errors.append("Name is required.")
        if not emp_id.strip():    errors.append("ID is required.")
        if face_img is None:      errors.append("Please capture or upload a face photo before submitting.")

        if errors:
            for e in errors:
                st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
        else:
            with st.spinner("Encoding face…"):
                encoding, ok, msg = encode_face(face_img)

            if not ok:
                st.markdown(f'<div class="error-box">{msg}<br><small>User was not saved.</small></div>', unsafe_allow_html=True)
            else:
                try:
                    import face_recognition
                    known_users = get_all_face_encodings()
                    is_duplicate = False
                    duplicate_name = ""
                    
                    if known_users:
                        all_known_encs = [u["encoding"] for u in known_users]
                        matches = face_recognition.compare_faces(all_known_encs, encoding, tolerance=0.50)
                        if True in matches:
                            match_idx = matches.index(True)
                            duplicate_name = known_users[match_idx]["name"]
                            is_duplicate = True

                    if is_duplicate:
                        st.markdown(f'<div class="error-box">Face already registered to <b>{duplicate_name}</b>. Cannot register duplicates.</div>', unsafe_allow_html=True)
                    else:
                        normalized_emp_id = emp_id.strip().upper()
                        photo_dir = os.path.join(os.path.dirname(__file__), "data", "faces")
                        os.makedirs(photo_dir, exist_ok=True)
                        photo_path = os.path.join(photo_dir, f"{normalized_emp_id}.jpg")
                        face_img.save(photo_path)

                        success, db_msg = add_user(
                            name=name.strip(),
                            employee_id=normalized_emp_id,
                            department=dept.strip() or None,
                            role=role,
                            face_encoding=encoding,
                            photo_path=photo_path,
                            is_in_food_program=1 if is_in_food_program else 0,
                        )
                        if success:
                            st.session_state.pop("reg_face_bytes", None)
                            st.session_state["reg_success_msg"] = f'<div class="success-box">{db_msg} — <b>{name.strip()}</b> ({normalized_emp_id})</div>'
                            st.rerun()
                        else:
                            st.markdown(f'<div class="error-box">{db_msg}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="error-box">Failed to save user: {e}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — RECORDS
# ════════════════════════════════════════════════════════════════════════════════
with tab_records:
    st.markdown('<div class="section-title">Attendance Logs</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns([1.2, 1.2, 1.2, 1])
    with fc1:
        f_from = st.date_input("From", value=date.today() - timedelta(days=7))
    with fc2:
        f_to   = st.date_input("To",   value=date.today())
    with fc3:
        depts  = ["All"] + get_departments()
        f_dept = st.selectbox("Department", depts)
    with fc4:
        f_emp  = st.text_input("Filter by ID", placeholder="Leave blank for all")

    records = get_meal_logs(
        date_from=f_from,
        date_to=f_to,
        department=None if f_dept == "All" else f_dept,
        employee_id=f_emp.strip().upper() if f_emp.strip() else None,
    )

    df = records_to_df(records)

    if df.empty:
        st.markdown('<div class="info-box">No records found.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="info-box">Showing <b>{len(df)}</b> records</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df_to_csv_bytes(df)
        st.download_button("Export as CSV", data=csv, file_name=f"meals_{f_from}_{f_to}.csv", mime="text/csv")
        
    st.markdown("---")
    with st.expander("Danger Zone"):
        st.warning("This will permanently delete all meal logs in the system.")
        if st.button("Delete All Meal Logs", type="primary", use_container_width=True):
            clear_meal_logs()
            st.success("All meal logs cleared.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — REPORTS
# ════════════════════════════════════════════════════════════════════════════════
with tab_reports:
    st.markdown('<div class="section-title">Analytics overview</div>', unsafe_allow_html=True)

    daily = get_daily_meal_counts(days=14)
    if daily:
        df_daily = pd.DataFrame(daily)
        fig_line = px.area(
            df_daily, x="date", y="count",
            title="Total Meals Logged Trend (Last 14 Days)",
            labels={"date": "Date", "count": "Meals"},
            color_discrete_sequence=["#6c63ff"],
            template="plotly_dark",
        )
        fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e8eaf6")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.markdown('<div class="info-box">Not enough data.</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — MANAGE USERS
# ════════════════════════════════════════════════════════════════════════════════
with tab_users:
    st.markdown('<div class="section-title">Directory</div>', unsafe_allow_html=True)

    if not active_users:
        st.markdown('<div class="info-box">No users registered.</div>', unsafe_allow_html=True)
    else:
        # Use columns for the grid
        cols_per_row = 3
        for i in range(0, len(active_users), cols_per_row):
            row_users = active_users[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, u in enumerate(row_users):
                with cols[j]:
                    st.markdown(f"""
                    <div class="user-card">
                        <div class="user-card-header">
                            <div class="avatar">{u['name'][0].upper()}</div>
                            <div>
                                <div style="font-weight:700; color:#f8fafc; font-size:1rem;">{u['name']}</div>
                                <div style="font-size:0.75rem; color:#6366f1; font-weight:600;">{u['employee_id']}</div>
                            </div>
                        </div>
                        <div class="user-card-content">
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="font-size:0.8rem;">Role</span>
                                <span class="badge badge-purple">{u['role']}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="font-size:0.8rem;">Dept</span>
                                <span style="color:#e2e8f0; font-weight:600; font-size:0.85rem;">{u.get('department') or '—'}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-size:0.8rem;">Food Plan</span>
                                <span style="color:{'#4ade80' if u.get('is_in_food_program') else '#f87171'}; font-weight:700; font-size:0.85rem;">
                                    {'Active' if u.get('is_in_food_program') else 'Inactive'}
                                </span>
                            </div>
                            <div style="font-size:0.7rem; color:#64748b; margin-top:10px;">
                                Joined {str(u['registered_at'])[:10]}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_del, col_toggle = st.columns(2)
                    with col_del:
                        if st.button(f"Delete", key=f"del_{u['employee_id']}", use_container_width=True):
                            deactivate_user(u["employee_id"])
                            st.success(f"Removed")
                            st.rerun()
                    with col_toggle:
                        new_state = 0 if u.get('is_in_food_program') else 1
                        btn_txt = "Opt Out" if u.get('is_in_food_program') else "Enroll"
                        if st.button(btn_txt, key=f"tog_{u['employee_id']}", use_container_width=True):
                            toggle_food_program(u["employee_id"], new_state)
                            st.success(f"Toggled enrollment")
                            st.rerun()
