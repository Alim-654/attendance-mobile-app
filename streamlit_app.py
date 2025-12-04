import streamlit as st
import random
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import pytz
import time

# ----------------------------------------------------
# CSS and Configuration
# ----------------------------------------------------
st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        th { font-weight: normal !important; font-size: 13px !important; }
        td { font-size: 13px; }
        table { table-layout: fixed; width: 100%; border-collapse: collapse; }
        th, td { width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: normal; }
        button[data-testid="stExpanderHeader"] > div:first-child { font-weight: bold !important; font-size: 50px !important; }
    </style>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------
# Session State Initialization
# ----------------------------------------------------
if "weekly_expander_open" not in st.session_state:
    st.session_state.weekly_expander_open = False
if "individual_expander_open" not in st.session_state:
    st.session_state.individual_expander_open = False

if "week_option" not in st.session_state:
    st.session_state.week_option = "-- Select a Week --"

if "individual_option" not in st.session_state:
    st.session_state.individual_option = "-- Select the individual --" 

# -----------------------------------------------------------------
# Define Callback Functions for Mutual Exclusivity
# -----------------------------------------------------------------
def reset_weekly():
    """When Individual is selected, reset weekly selection."""
    st.session_state.week_option = "-- Select a Week --"
    st.session_state.weekly_expander_open = False
    st.session_state.individual_expander_open = True

def reset_individual():
    """When Week is selected, reset individual selection."""
    st.session_state.individual_option = "-- Select the individual --"
    st.session_state.individual_expander_open = False
    st.session_state.weekly_expander_open = True

# -------------------------------
# Helper & Mapping
# -------------------------------
def make_unique(headers):
    counts = {}
    new_headers = []
    for h in headers:
        if h not in counts:
            counts[h] = 1
            new_headers.append(h)
        else:
            counts[h] += 1
            new_headers.append(f"{h}_{counts[h]}")
    return new_headers

code_to_name = {
    "R": "Rahyanath JTO", "K": "Khamarunneesa JTO", "A": "Alim JTO", "P": "Pradeep JTO", 
    "SHA": "Shafeeq SDE", "B": "Bahna JTO", "SH": "Shihar JTO", "ST": "Sreejith JTO ",
    "I": "Ilyas SDE", "JM": "Jithush JTO", "JD": "Jimshad JTO", "RK": "Rajesh JTO",
    "RKM": "Riyaz JTO", "AMP": "Abdulla SDE", "N": "Naveen JTO"
}

# --- Header and Home Button ---
col1, col2 = st.columns([1,4])
with col1:
    if st.button("🏠"):
        st.session_state.week_option = "-- Select a Week --"
        st.session_state.individual_option = "-- Select the individual --"
        st.session_state.weekly_expander_open = False
        st.session_state.individual_expander_open = False
        st.rerun()

with col2:
    st.markdown("""<h3 style="margin: 0; font-weight: 500; font-size: 22px;">Attendance Viewer</h3>""", unsafe_allow_html=True)

# -------------------------------
# Google Sheets Authentication & Data Loading
# -------------------------------
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    # Use st.secrets on Streamlit Cloud
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
except Exception:
    try:
        creds = Credentials.from_service_account_file("attendance-app-479515-a2c99015276e.json", scopes=scope)
    except FileNotFoundError:
        st.error("Service account credentials not found. Please check `st.secrets` or local key file.")
        st.stop()

client = gspread.authorize(creds)
#sheet = client.open("AppTester").sheet1
sheet = client.open("MLP ONENOC DUTYCHART").sheet1

@st.cache_data(ttl=60) 
def load_sheet(_sheet):
    values = _sheet.get_all_values()
    raw_header = values[0]
    header = [h if h.strip() != "" else f"col_{i}" for i, h in enumerate(raw_header)]
    fixed_header = []
    last_header = None
    for h in header:
        if not h.startswith("col_"):
            last_header = h
            fixed_header.append(h)
        else:
            fixed_header.append(last_header)

    final_header = make_unique(fixed_header)
    df = pd.DataFrame(values[1:], columns=final_header)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce").dt.date

    return df

df = load_sheet(sheet)

# Your known employee codes (MUST be sorted by length descending)
code_list = sorted(code_to_name.keys(), key=lambda x: -len(x))

def extract_employee_code(raw_value):
    import re
    if pd.isna(raw_value) or not raw_value: return None
    raw_value = str(raw_value).upper().strip()
    # Step 1: Cleanup
    cleaned = re.sub(r'(\s*\([^)]*\))|(\/.*)|(\s+W-OFF|\s+LEAVE|\s+COFF|\s+GUEST)', '', raw_value, flags=re.IGNORECASE).strip()
    if not cleaned: return None
    # Step 2: Extract Candidates
    candidates = re.findall(r'[A-Z]{1,}', cleaned)
    # Step 3: Match
    for code in code_list:
        if code in cleaned:
            return code
    return None

for col in df.columns:
    if col not in ["Date", "Day"]:
        df[col] = df[col].apply(extract_employee_code)

# -------------------------------
# Functions for Report Generation
# -------------------------------
def get_attendance_for_date(target_date):
    data = df[df["Date"] == target_date].copy()
    if data.empty: return None

    data = data.replace("", pd.NA).dropna(axis=1, how="all")
    day_name = target_date.strftime("%A")
    formatted_date_part = target_date.strftime("%d-%m-%Y")
    data["Date_display"] = f"{day_name}, {formatted_date_part}"
    
    data = data.drop(columns=["Day"], errors="ignore")
    hide_cols_2=["Duty Leave_10"]
    data = data.drop(columns=[c for c in hide_cols_2 if c in data.columns])

    # Night Shift Logic
    night_cols = [c for c in data.columns if " ".join(c.split()).startswith("Night 20.00 to 8.00")]
    yesterday = target_date - datetime.timedelta(days=1)
    prev = df[df["Date"] == yesterday] 
    if not prev.empty:
        for col in night_cols:
            yesterday_people = set(prev[col].dropna().astype(str).str.strip().str.upper()) 
            data[col] = data[col].apply(lambda x: "" if str(x).strip().upper() in yesterday_people else x)

    eligible_night_cols = [c for c in night_cols if data[c].dropna().astype(str).str.strip().any()]
    eligible_series = [data[c].copy() for c in eligible_night_cols]
    if night_cols: original_start = data.columns.get_loc(night_cols[0])
    else: original_start = len(data.columns)
    data = data.drop(columns=night_cols)
    for i, series in enumerate(eligible_series):
        new_name = "Night 20.00 to 8.00" if i == 0 else f"Night 20.00 to 8.00_{i+1}"
        data.insert(original_start + i, new_name, series)

    # Codes to Names
    for col in data.columns:
        if col not in ["Date", "Date_display"]: 
            data[col] = data[col].map(code_to_name).fillna(data[col])

    # General Shift Logic
    general_cols = [c for c in data.columns if c.startswith("General")]
    general_count = sum(data[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().count() for col in general_cols if col in data.columns)

    if general_count > 3:
        data = data.drop(columns=[c for c in general_cols if c in data.columns])
    else:
        def merge_general(row):
            names = [str(row[c]).strip() for c in general_cols if c in row and pd.notna(row[c]) and str(row[c]).strip() != ""]
            return ", ".join(names)
        if general_cols:
            first_general_idx = data.columns.get_loc(general_cols[0]) if general_cols[0] in data.columns else -1
            if first_general_idx != -1:
                data.insert(first_general_idx, "General Shift", data.apply(merge_general, axis=1))
        data = data.drop(columns=[c for c in general_cols if c in data.columns])

    data.reset_index(drop=True, inplace=True)
    data = data.drop(columns=["Date"], errors="ignore") 
    data = data.rename(columns={"Date_display": "Date"})
    data = data.drop(columns=["Date_1"], errors="ignore") 
    return data

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.datetime.now(ist)
today = now_ist.date()
tomorrow = today + datetime.timedelta(days=1)

import html as _html  # stdlib html.escape

def render_simple_text_block(title, data_df):
    if data_df is None or data_df.empty:
        st.warning(f"{title}: No data available.")
        return

    row = data_df.iloc[0]
    date_str = row["Date"]

    st.markdown(f"### {title}")
    st.markdown(f"**{date_str}**")

    # --- color map ---
    color_map = {
        "MORNING": "#dceeff",   # soft blue
        "EVENING": "#ffe6cc",   # soft orange
        "NIGHT":   "#eadcff",   # soft purple
        "W-OFF":   "#d9f7d9",   # mint green
        "LEAVE":   "#ffd6d6",   # light red
        "GENERAL": "#e6f2ff",   # very soft blue
        "C-OFF":   "#d6f5f5",   # soft teal (new)
    }

    # container start
    st.markdown("<div style='margin-top: 6px;'>", unsafe_allow_html=True)

    for col in data_df.columns:
        if col == "Date":
            continue

        raw_val = row[col]
        # convert to str safely and strip
        value = "" if raw_val is None else str(raw_val).strip()
        if not value or value.lower() == "nan":
            continue

        # escape value so any angle-brackets in data won't break HTML
        safe_value = _html.escape(value)

        # determine color by column name
        upper_col = col.upper()
        color = "#f2f2f2"
        for key in color_map:
            if key in upper_col:
                color = color_map[key]
                break

        # single clean HTML block per item (use span for label)
        html = (
            f"<div style='"
            f"background: {color};"
            f"color: black;"
            f"padding: 8px 10px;"
            f"border-radius: 6px;"
            f"margin: 6px 0;"
            f"font-size: 14px;"
            f"max-width: 90%;"
            f"word-wrap: break-word;"
            f"'>"
            f"<span style='font-weight:600'>{_html.escape(col)}:</span>&nbsp;{safe_value}"
            f"</div>"
        )

        st.markdown(html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)


def show_attendance_block(title, date, display_style):
    df_data = get_attendance_for_date(date)
    if df_data is None or df_data.empty:
        st.warning(f"{title}: No data available.")
        return
    render_simple_text_block(title, df_data)

def show_individual_report(individual_name, target_month, target_year):
    if individual_name == "-- Select the individual --": return
    name_to_code = {v: k for k, v in code_to_name.items()}
    selected_code = name_to_code.get(individual_name)
    if not selected_code:
        st.warning(f"No code found for {individual_name}")
        return

    try:
        start_date = datetime.date(target_year, target_month, 1)
        if target_month == 12: end_date = datetime.date(target_year + 1, 1, 1) - datetime.timedelta(days=1)
        else: end_date = datetime.date(target_year, target_month + 1, 1) - datetime.timedelta(days=1)
    except ValueError:
        st.info("Invalid month/year selection.")
        return

    delta = end_date - start_date
    all_dates_in_month = [start_date + datetime.timedelta(days=i) for i in range(delta.days + 1)]
    attendance_by_day = {date_dt.strftime('%Y-%m-%d'): [] for date_dt in all_dates_in_month}
    
    df_month = df[
        (df["Date"].apply(lambda d: d.month) == target_month) & 
        (df["Date"].apply(lambda d: d.year) == target_year)
    ]
    
    for idx, row in df_month.iterrows():
        date_val = row["Date"] 
        key = date_val.strftime('%Y-%m-%d')
        found_shifts = []
        for col in df.columns:
            if col == "Date": continue
            cell_value = str(row[col]).strip().upper()
            if cell_value == selected_code.upper():
                if col.startswith("Morning"): shift_label = "Morning 8.00 to 15.30"
                elif col.startswith("Evening"): shift_label = "Evening 12.30 to 20.00"
                elif col.startswith("Night"): shift_label = "Night 20.00 to 8.00"
                elif col.startswith("General"): shift_label = "General"
                elif col.startswith("W-Off"): shift_label = "W-Off"
                elif col.startswith("Leave"): shift_label = "Leave"
                else: shift_label = col
                found_shifts.append(shift_label)
        if found_shifts:
            attendance_by_day[key] = found_shifts

    if not df_month.empty and all(not shifts for shifts in attendance_by_day.values()):
        pass 
    elif df_month.empty:
        st.info(f"No attendance data found in the sheet for {start_date.strftime('%B %Y')}.")
        return

    month_name_year = start_date.strftime('%B %Y')
    st.markdown(f"<div style='margin-bottom:4px;'><h5>Attendance Report for {individual_name} ({month_name_year})</h5></div>", unsafe_allow_html=True)

    report_data = []
    sorted_keys = sorted(attendance_by_day.keys()) 
    for key in sorted_keys:
        date_dt = datetime.datetime.strptime(key, '%Y-%m-%d').date()
        formatted_day = date_dt.strftime('%a, %d %b')
        shifts = " / ".join(attendance_by_day[key])
        status = shifts if shifts else "❓ UNRECORDED"
        report_data.append({"Day": formatted_day, "Shift/Status": status})

    df_report = pd.DataFrame(report_data)
    st.dataframe(df_report, use_container_width=True, hide_index=True)
    st.markdown("<hr style='border: none; border-top: 1px solid #eee; margin: 15px 0;'>", unsafe_allow_html=True)


# -----------------------------------------------------------------
# LAYOUT & CONTROL LOGIC
# -----------------------------------------------------------------
# -----------------------------------------------------------------
# LAYOUT & CONTROL LOGIC (Replace your existing section with this)
# -----------------------------------------------------------------
week_options = ["-- Select a Week --", "This Week", "Next Week", "Last Week"]
sorted_names = sorted(code_to_name.values())
individual_options = ["-- Select the individual --"] + sorted_names

# --- Calculate Initial Indices ---
week_index = 0
if st.session_state.week_option in week_options:
    week_index = week_options.index(st.session_state.week_option)
    
individual_index = 0
if st.session_state.individual_option in individual_options:
    individual_index = individual_options.index(st.session_state.individual_option)

display_style = random.choice(["A", "B"])

# -----------------------------------------------------------------
# EXPANDER LOGIC
# -----------------------------------------------------------------

if individual_index != 0:
    # A. Individual is ALREADY selected: Show Individual Expander
    real_names = individual_options[1:]

    with st.expander("🗓️ **CHOOSE INDIVIDUAL REPORT**", expanded=st.session_state.individual_expander_open):
        # 1. Search Box
        search_key = "individual_search_input_A"
        search = st.text_input("Search Individual Name:", value="", key=search_key, label_visibility="collapsed", placeholder="Type to search employee...")

        # 2. Filter Logic
        if search:
            filtered_names = [n for n in real_names if search.upper() in n.upper()]
            # --- AUTO-SELECT FIX ---
            # If search results exist, automatically select the first match
            if filtered_names:
                st.session_state.individual_option = filtered_names[0]
                # Also sync the specific widget key to avoid visual mismatch
                st.session_state["individual_option_A"] = filtered_names[0]
        else:
            filtered_names = real_names
            
        filtered_options = individual_options[0:1] + filtered_names 
        
        # 3. Determine Index (Now using the potentially auto-updated value)
        current_value = st.session_state.individual_option
        try:
            current_index = filtered_options.index(current_value)
        except ValueError:
            current_index = 0
            st.session_state.individual_option = individual_options[0]

        # 4. Radio Selection (NOTE: Key is _A to avoid duplicates)
        st.markdown("<div style='max-height:280px; overflow-y:auto; border:1px solid #ddd; border-radius:6px; padding:6px;'>", unsafe_allow_html=True)
        selected_value = st.radio(
            "Select name:",
            filtered_options,
            index=current_index,
            key="individual_option_A",
            on_change=reset_weekly,
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Sync key back to main
        st.session_state.individual_option = selected_value

        # --- RE-CALCULATE INDEX ---
        if st.session_state.individual_option in individual_options:
            individual_index = individual_options.index(st.session_state.individual_option)
        else:
            individual_index = 0
            
        if individual_index != 0:
            week_index = 0 

elif week_index != 0:
    # B. Week is selected: Show ONLY the Weekly Expander
    with st.expander("🗓️ **CHOOSE A WEEKLY ATTENDANCE**", expanded=True):
        st.selectbox("Weekly Selection", week_options, index=week_index, key="week_option", label_visibility="collapsed", on_change=reset_individual)

else:
    # C. Neither is selected: Show BOTH Expanders (Default Landing)
    with st.expander("🗓️ **CHOOSE WEEKLY ATTENDANCE**", expanded=st.session_state.weekly_expander_open):
        st.selectbox("Weekly Selection", week_options, index=week_index, key="week_option", label_visibility="collapsed", on_change=reset_individual)

    real_names = individual_options[1:]
    with st.expander("🗓️ **CHOOSE INDIVIDUAL REPORT**", expanded=st.session_state.individual_expander_open):
        # 1. Search Box
        search_key = "individual_search_input"
        search = st.text_input("Search Individual Name:", value="", key=search_key, label_visibility="collapsed", placeholder="Type to search employee...")

        # 2. Filter Logic
        if search:
            filtered_names = [n for n in real_names if search.upper() in n.upper()]
            # --- AUTO-SELECT FIX ---
            # If search results exist, automatically select the first match
            if filtered_names:
                st.session_state.individual_option = filtered_names[0]
        else:
            filtered_names = real_names
        
        filtered_options = individual_options[0:1] + filtered_names 
        
        # 3. Determine Index (Now using the potentially auto-updated value)
        current_value = st.session_state.individual_option
        try:
            current_index = filtered_options.index(current_value)
        except ValueError:
            current_index = 0
            st.session_state.individual_option = individual_options[0]

        # 4. Radio Selection (Standard key used here)
        st.markdown("<div style='max-height:280px; overflow-y:auto; border:1px solid #ddd; border-radius:6px; padding:6px;'>", unsafe_allow_html=True)
        selected_value = st.radio(
            "Select name:",
            filtered_options,
            index=current_index,
            key="individual_option",
            on_change=reset_weekly,
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # --- RE-CALCULATE INDEX ---
        if st.session_state.individual_option in individual_options:
            individual_index = individual_options.index(st.session_state.individual_option)
        else:
            individual_index = 0

# -------------------------------
# DISPLAY LOGIC 
# -------------------------------

if individual_index != 0:
    # A. Show Individual Report 
    individual_name = st.session_state.individual_option
    current_month = now_ist.month
    current_year = now_ist.year
    first_of_current_month = now_ist.date().replace(day=1)
    prev_date = first_of_current_month - datetime.timedelta(days=1)
    prev_month = prev_date.month
    prev_year = prev_date.year
    
    show_individual_report(individual_name, current_month, current_year)
    st.markdown("---") 
    show_individual_report(individual_name, prev_month, prev_year)

elif week_index != 0:
    # B. Show Weekly Report 
    today_dt = datetime.date.today() 
    if st.session_state.week_option == "This Week":
        monday = today_dt - datetime.timedelta(days=today_dt.weekday())
    elif st.session_state.week_option == "Next Week":
        monday = today_dt - datetime.timedelta(days=today_dt.weekday()) + datetime.timedelta(days=7)
    elif st.session_state.week_option == "Last Week":
        monday = today_dt - datetime.timedelta(days=today_dt.weekday()) - datetime.timedelta(days=7)

    st.markdown(f"###### Report for {st.session_state.week_option}")

    all_days_html = []
    for i in range(7):
        day = monday + datetime.timedelta(days=i)
        result = get_attendance_for_date(day)
        
        day_heading_html = f"""<div style='text-align:right; font-size:13px; color:#777; margin:2px 0 2px 0; padding-right: 5px;'>{day.strftime('%A, %d %b %Y')}</div>"""
        all_days_html.append(day_heading_html)
        
        if result is None:
            no_data_html = f"""<div style='padding: 5px; background-color: #f0f2f6; color: #888; border-radius: 3px; text-align: center;'>No attendance found.</div><hr style='border: none; border-top: 1px solid #eee; margin: 5px 0;'>"""
            all_days_html.append(no_data_html)
            continue

        result = result.drop(columns=["Date", "Day"], errors="ignore") 
        result = result.replace("</div>", "", regex=False)
        styled = result.style.hide(axis="index")
        html_table = styled.to_html(escape=False).strip() 
        all_days_html.append(html_table)
        separator_html = "<hr style='margin: 25px 0;'>"
        all_days_html.append(separator_html)

    final_weekly_html = "<div style='overflow-x:auto; white-space: nowrap;'>" + "".join(all_days_html) + "</div>"
    st.markdown(final_weekly_html, unsafe_allow_html=True)

else:
    # C. Show Today/Tomorrow
    show_attendance_block("🗓️ Today's Attendance", today, display_style)
    st.markdown("<br>", unsafe_allow_html=True)
    show_attendance_block("🗓️ Tomorrow's Attendance", tomorrow, display_style)