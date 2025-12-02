import streamlit as st
import random
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import pytz
import time

# --- CSS and Configuration ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
    <style>
        th {
            font-weight: normal !important;
            font-size: 13px !important; 
        }
        td {
            font-size: 13px; 
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Force fixed layout and equal width columns */
table {
    table-layout: fixed;
    width: 100%;
    border-collapse: collapse;
}
th, td {
    width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    font-weight: normal;
}
</style>
""", unsafe_allow_html=True)


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
# -----------------------------------------------------------------


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
    "R": "Rahyanath JTO", "K": "Khamarunnesa JTO", "A": "Alim JTO", "P": "Pradeep JTO", 
    "SHA": "Shafeeq SDE", "B": "Bahna JTO", "SH": "Shihar JTO", "ST": "Sreejith JTO ",
    "I": "Ilyas SDE", "JM": "Jithush JTO", "JD": "Jimshad JTO", "RK": "Rajesh JTO",
    "RKM": "Riyaz JTO", "AMP": "Abdulla SDE", "N": "Naveen JTO"
}

# --- Header and Home Button ---
col1, col2 = st.columns([1,4])

with col1:
    if st.button("🏠"):
        # Reset everything to default and rerun
        st.session_state.week_option = "-- Select a Week --"
        st.session_state.individual_option = "-- Select the individual --"
        st.session_state.weekly_expander_open = False
        st.session_state.individual_expander_open = False
        st.rerun()

with col2:
    st.markdown("""
        <h3 style="margin: 0; font-weight: 500; font-size: 22px;">
            Attendance Viewer
        </h3>
    """, unsafe_allow_html=True)


# -------------------------------
# Google Sheets Authentication & Data Loading
# -------------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

try:
    # Use st.secrets on Streamlit Cloud
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
except Exception:
    # Fallback for local development if a key file is present
    try:
        creds = Credentials.from_service_account_file("attendance-app-479515-a2c99015276e.json", scopes=scope)
    except FileNotFoundError:
        st.error("Service account credentials not found. Please check `st.secrets` or local key file.")
        st.stop()


client = gspread.authorize(creds)
#sheet = client.open("AppTester").sheet1
sheet = client.open("MLP ONENOC DUTYCHART").sheet1



@st.cache_data(ttl=30) 
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
        # NOTE: Keeping .dt.date here means df["Date"] is a Python date object (pandas dtype=object)
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce").dt.date

    return df

df = load_sheet(sheet)













# Your known employee codes (MUST be sorted by length descending)
code_list = sorted(code_to_name.keys(), key=lambda x: -len(x))

def extract_employee_code(raw_value):
    import re
    if pd.isna(raw_value) or not raw_value:
        return None
        
    raw_value = str(raw_value).upper().strip()

    # --- Step 1: Aggressive Cleanup to Isolate Potential Codes ---
    # Removes parenthesis contents, slashes, and common status descriptors (W-OFF, LEAVE, etc.) 
    # This leaves behind strings like 'RKM' or 'RKMCOFF' or 'RKM LEAVE'
    
    # Pattern: remove dates/parentheses (Group 1) OR remove descriptive words + space (Group 2)
    cleaned = re.sub(r'(\s*\([^)]*\))|(\/.*)|(\s+W-OFF|\s+LEAVE|\s+COFF|\s+GUEST)', '', raw_value, flags=re.IGNORECASE).strip()
    
    # If the cleanup resulted in an empty string, return None
    if not cleaned:
        return None
        
    # --- Step 2: Extract ALL Contiguous Alphabetic/Code Candidates ---
    # This splits strings like 'RKMLEAVE' into ['RKM', 'LEAVE'] or 'COFFRKM' into ['COFF', 'RKM']
    candidates = re.findall(r'[A-Z]{1,}', cleaned)
    
    # --- Step 3: Cascading Match (Longest Valid Code First) ---
    for code in code_list:
        # Check if the valid code is present in ANY of the candidates
        # E.g., if 'RKM' is a valid code, and the candidates list contains 'RKM', 
        # this will find it.
        
        # We check the raw cleaned string first, as codes like RKM might be merged (e.g., COFFRKM -> RKM)
        if code in cleaned:
            # Crucial check: we need to ensure the match isn't part of a larger, invalid code.
            # E.g., if 'RKM' is the longest match found, it's the intended code.
            
            # Since 'code_list' is sorted by length, the FIRST code that successfully 
            # matches the longest valid code in the cleaned string is the one we want.
            return code
            
    # --- Step 4: No Match Found ---
    return None

# Then, you would apply this function to your DataFrame:
for col in df.columns:
    if col not in ["Date", "Day"]:  # Skip non-attendance columns
        df[col] = df[col].apply(extract_employee_code)
















# ================================================================
# FUNCTIONS
# ================================================================
def get_attendance_for_date(target_date):
    # This comparison works because both df["Date"] and target_date are Python date objects
    data = df[df["Date"] == target_date].copy()
    if data.empty: return None

    # This creates a copy of the original "Date" column (which holds the Python date objects)
    
    data = data.replace("", pd.NA).dropna(axis=1, how="all")
    day_name = target_date.strftime("%A")
    formatted_date_part = target_date.strftime("%d-%m-%Y")
    
    # --- STEP 1: Create the new display string in a temporary column ---
    data["Date_display"] = f"{day_name}, {formatted_date_part}"
    
    data = data.drop(columns=["Day"], errors="ignore")

    hide_cols_2=["Duty Leave_10"]
    data = data.drop(columns=[c for c in hide_cols_2 if c in data.columns])

    # NIGHT SHIFT CLEANUP + ORDER RESTORE
    # ... (Night Shift logic remains unchanged) ...
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

    # Replace codes → names
    for col in data.columns:
        if col not in ["Date", "Date_display"]: 
            data[col] = data[col].map(code_to_name).fillna(data[col])

    # GENERAL SHIFT LOGIC
    # ... (General Shift logic remains unchanged) ...
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
    
    # --- STEP 2: DROP THE ORIGINAL DATE COLUMN (The source of the problem) ---
    # This explicitly removes the column holding the Python date object.
    data = data.drop(columns=["Date"], errors="ignore") 
    
    # --- STEP 3: RENAME the DISPLAY column to "Date" for final display functions ---
    # Now, ONLY the formatted string remains and is named "Date".
    data = data.rename(columns={"Date_display": "Date"})
    
    # The redundant "Date_1" column is no longer an issue if step 2 works correctly.
    data = data.drop(columns=["Date_1"], errors="ignore") 

    return data


ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.datetime.now(ist)
today = now_ist.date()
tomorrow = today + datetime.timedelta(days=1)

def render_simple_text_block(title, data_df):
    if data_df is None or data_df.empty:
        st.warning(f"{title}: No data available.")
        return
    row = data_df.iloc[0]
    
    # FIX: Ensure we extract the clean formatted date string
    date_str = row["Date"] 
    
    st.markdown(f"### {title}")
    st.markdown(f"**Date:** {date_str}\n")
    
    # Loop over columns, skipping the 'Date' column which holds the clean string
    for col in data_df.columns:
        if col == "Date" or col == "Date_1": continue
        value = str(row[col]).strip()
        if value and value.lower() != "nan": st.markdown(f"**{col}:** {value}")
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

def render_card_block(title, data_df, color_emoji="🟦"):
    if data_df is None or data_df.empty:
        st.warning(f"{title}: No data available.")
        return
    row = data_df.iloc[0]
    
    # FIX: Ensure we extract the clean formatted date string
    date_str = row["Date"]
    
    st.markdown(f"{color_emoji} **{title}**")
    st.markdown(f" **{date_str}**\n")
    
    # Loop over columns, skipping the 'Date' column which holds the clean string
    for col in data_df.columns:
        if col == "Date" or col == "Date_1": continue
        value = str(row[col]).strip()
        if value and value.lower() != "nan": st.markdown(f"- **{col}:** {value}")
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

def show_attendance_block(title, date, display_style):
    df_data = get_attendance_for_date(date)
    if df_data is None or df_data.empty:
        st.warning(f"{title}: No data available.")
        return
    # if display_style == "A": render_simple_text_block(title, df_data)
    # else: render_card_block(title, df_data) 
    render_simple_text_block(title, df_data)

# MODIFIED: Accepts target_month and target_year
def show_individual_report(individual_name, target_month, target_year):
    if individual_name == "-- Select the individual --": return
    name_to_code = {v: k for k, v in code_to_name.items()}
    selected_code = name_to_code.get(individual_name)
    if not selected_code:
        st.warning(f"No code found for {individual_name}")
        return

    # --- 1. DETERMINE ALL DATES IN THE TARGET MONTH ---
    try:
        start_date = datetime.date(target_year, target_month, 1)
        # Calculate the end date by moving to the 1st of the next month and subtracting one day
        if target_month == 12:
            end_date = datetime.date(target_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(target_year, target_month + 1, 1) - datetime.timedelta(days=1)
    except ValueError:
        st.info("Invalid month/year selection for report generation.")
        return

    # Create a range of all dates in the month
    delta = end_date - start_date
    all_dates_in_month = [start_date + datetime.timedelta(days=i) for i in range(delta.days + 1)]
    
    # Initialize dictionary to store shifts for every day in the month
    attendance_by_day = {date_dt.strftime('%Y-%m-%d'): [] for date_dt in all_dates_in_month}
        
    # --- 2. POPULATE SHIFTS (FILTERING CORRECTED FOR PYTHON DATE OBJECTS) ---
    
    # FIX APPLIED HERE: Filter using Python date object attributes (.month, .year) instead of .dt
    df_month = df[
        (df["Date"].apply(lambda d: d.month) == target_month) & 
        (df["Date"].apply(lambda d: d.year) == target_year)
    ]
    
    for idx, row in df_month.iterrows():
        # date_val is already a Python date object thanks to load_sheet
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

    # --- 3. DISPLAY THE REPORT (MODIFIED FOR TABLE OUTPUT) ---
    month_name_year = start_date.strftime('%B %Y')
    
    # Use your custom HTML heading for margin control
    st.markdown(
        f"<div style='margin-bottom:4px;'><h5>Attendance Report for {individual_name} ({month_name_year})</h5></div>",
        unsafe_allow_html=True
    )

    # --- Data Collection for Table ---
    # --- Data Collection for Table (Revised) ---
    report_data = []
    # Removed: today = datetime.date.today() 
    
    sorted_keys = sorted(attendance_by_day.keys()) 
    
    for key in sorted_keys:
        date_dt = datetime.datetime.strptime(key, '%Y-%m-%d').date()
        formatted_day = date_dt.strftime('%a, %d %b') # Shorter day format
        shifts = " / ".join(attendance_by_day[key])
        
        # Determine Status for visual clarity
        if not shifts:
            # If the shifts list is empty, always label it as UNRECORDED,
            # regardless of whether the date is past or future.
            status = "❓ UNRECORDED" 
        else:
            status = shifts
            
        report_data.append({
            "Day": formatted_day,
            "Shift/Status": status
        })

    # --- Table Generation (Remains the same) ---
    df_report = pd.DataFrame(report_data)
    # ... (rest of the function remains the same)
    
    st.dataframe(
        df_report,
        use_container_width=True,
        hide_index=True
    )
    
    # Add a tight separator at the end of the report block
    st.markdown("<hr style='border: none; border-top: 1px solid #eee; margin: 15px 0;'>", unsafe_allow_html=True)
    
    
week_options = ["-- Select a Week --", "This Week", "Next Week", "Last Week"]

# --- FIX: Sort the list of names alphabetically ---
sorted_names = sorted(code_to_name.values())
individual_options = ["-- Select the individual --"] + sorted_names

# --- Indexing ---
week_index = 0
if st.session_state.week_option in week_options:
    week_index = week_options.index(st.session_state.week_option)
    
individual_index = 0
if st.session_state.individual_option in individual_options:
    individual_index = individual_options.index(st.session_state.individual_option)

#st.markdown("<br>", unsafe_allow_html=True) 

# --- CSS (for expander) ---
st.markdown("""
    <style>
        button[data-testid="stExpanderHeader"] > div:first-child {
            font-weight: bold !important;
            font-size: 50px !important;
        }
    </style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------
# LAYOUT IMPLEMENTATION
# -----------------------------------------------------------------

if individual_index != 0:
    # A. Individual is selected: Show ONLY the Individual Expander
    with st.expander("🗓️ **CHOOSE INDIVIDUAL REPORT**", expanded=True):
        st.selectbox(
            "Individual Selection",
            individual_options,
            index=individual_index,
            key="individual_option",
            label_visibility="collapsed",
            on_change=reset_weekly 
        )

elif week_index != 0:
    # B. Week is selected: Show ONLY the Weekly Expander
    with st.expander("🗓️ **CHOOSE A WEEKLY ATTENDANCE**", expanded=True):
        st.selectbox(
            "Weekly Selection",
            week_options,
            index=week_index,
            key="week_option",
            label_visibility="collapsed",
            on_change=reset_individual 
        )

else:
    # C. Neither is selected: Show BOTH Expanders (default landing view)
    with st.expander("🗓️ **CHOOSE WEEKLY ATTENDANCE**", expanded=st.session_state.weekly_expander_open):
        st.selectbox(
            "Weekly Selection",
            week_options,
            index=week_index,
            key="week_option",
            label_visibility="collapsed",
            on_change=reset_individual 
        )

    with st.expander("🗓️ **CHOOSE INDIVIDUAL REPORT**", expanded=st.session_state.individual_expander_open):
        st.selectbox(
            "Individual Selection",
            individual_options,
            index=individual_index,
            key="individual_option",
            label_visibility="collapsed",
            on_change=reset_weekly 
        )

# -----------------------------------------------------------------
#st.markdown("---") # Visual separator between controls and report area


# Add spacing
#st.markdown("<br>", unsafe_allow_html=True)

display_style = random.choice(["A", "B"])


# -------------------------------
# DISPLAY LOGIC 
# -------------------------------

if individual_index != 0:
    # A. Show Individual Report 
    individual_name = st.session_state.individual_option
    
    # --- Determine Current Month/Year ---
    current_month = now_ist.month
    current_year = now_ist.year
    
    # --- Determine Previous Month/Year ---
    first_of_current_month = now_ist.date().replace(day=1)
    prev_date = first_of_current_month - datetime.timedelta(days=1)
    prev_month = prev_date.month
    prev_year = prev_date.year
    
    #st.markdown("#### Individual Attendance Report")
    
    # 1. Show Current Month
    #st.markdown("---")
    show_individual_report(individual_name, current_month, current_year)

    # 2. Show Previous Month
    st.markdown("---") # Visual separator between months
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

    # Use a clear, consistent heading size (####)
    st.markdown(f"###### Report for {st.session_state.week_option}")

    # --- START OF SINGLE SCROLLABLE CONTAINER ---
    all_days_html = []
    
    for i in range(7):
        day = monday + datetime.timedelta(days=i)
        result = get_attendance_for_date(day)
        
        # 1. Day Heading HTML
        day_heading_html = f"""
            <div style='text-align:right; font-size:13px; color:#777; margin:2px 0 2px 0; padding-right: 5px;'>
                {day.strftime('%A, %d %b %Y')}
            </div>
        """
        all_days_html.append(day_heading_html)
        
        if result is None:
            # 2. No Data HTML (Uses a tight separator with minimal margin)
            no_data_html = f"""
                <div style='padding: 5px; background-color: #f0f2f6; color: #888; border-radius: 3px; text-align: center;'>
                    No attendance found.
                </div>
                <hr style='border: none; border-top: 1px solid #eee; margin: 5px 0;'>
            """
            all_days_html.append(no_data_html)
            continue

        # 3. Table HTML
        result = result.drop(columns=["Date", "Day"], errors="ignore") 
        result = result.replace("</div>", "", regex=False)
        styled = result.style.hide(axis="index")
        
        # NOTE: Do NOT wrap the table in the scrollable div here.
        html_table = styled.to_html(escape=False).strip() 
        all_days_html.append(html_table)
        
        # 4. Separator HTML (Use a tight, consistent separator between days)
        #separator_html = "<hr style='border: none; border-top: 1px solid #eee; margin: 10px 0;'>"
        #separator_html = "<hr style='border: none; border-top: 1px solid #888;  margin: 10px 0;'>"
        separator_html = "<hr style='margin: 25px 0;'>"
        all_days_html.append(separator_html)

    # --- END OF LOOP ---
    
    # --- RENDER ALL CONTENT INSIDE ONE SCROLLABLE CONTAINER ---
    # This single div applies overflow-x: auto to the entire weekly stack.
    # ... (all loop logic to populate all_days_html) ...

    # --- RENDER ALL CONTENT INSIDE ONE SCROLLABLE CONTAINER ---
    final_weekly_html = (
        "<div style='overflow-x:auto; white-space: nowrap;'>"
        + "".join(all_days_html)
        + "</div>"
    )

    st.markdown(final_weekly_html, unsafe_allow_html=True)


else:
    # C. Show Today/Tomorrow (i.e., when neither report is selected)
    #st.markdown("## Current & Upcoming Attendance")
    show_attendance_block("🗓️ Today's Attendance", today, display_style)
    show_attendance_block("🗓️ Tomorrow's Attendance", tomorrow, display_style)