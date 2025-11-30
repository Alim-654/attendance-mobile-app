import streamlit as st
import random
# --- Remove bold header from all tables ---

st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;
        }
    </style>
""", unsafe_allow_html=True)
# Add a single line break
st.markdown("<br>", unsafe_allow_html=True)


st.markdown("""
    <style>
        th {
            font-weight: normal !important;
            font-size: 13px !important;  /* reduce from default ~16px */
        }
        td {
            font-size: 13px;  /* optional: make cell text a bit smaller too */
        }
    </style>
""", unsafe_allow_html=True)

# --- CSS for fixed-width table columns ---
st.markdown("""
<style>
/* Force fixed layout and equal width columns */
table {
    table-layout: fixed;
    width: 100%;
    border-collapse: collapse;
}
th, td {
    width: 100px;  /* Adjust this width as needed */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;  /* matches previous styling */
    font-weight: normal;
}
</style>
""", unsafe_allow_html=True)





import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

import pytz
if "reset_week" not in st.session_state:
    st.session_state.reset_week = False
if "expander_collapsed" not in st.session_state:
    st.session_state.expander_collapsed = True


# -------------------------------
# Helper: Make headers unique
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


# -------------------------------
# Mapping Codes → Names
# -------------------------------
code_to_name = {
    "R": "Rahyanath JTO",
    "K": "Khamarunnesa JTO",
    "A": "Alim JTO",
    "P": "Pradeep JTO",
    "SHA": "Shafeeq  SDE",
    "B": "Bahna JTO",
    "SH": "Shihar JTO",
    "ST": "Sreejith JTO ",
    "I": "Ilyas SDE",
    "JM": "Jithush JTO",
    "JD": "Jimshad JTO",
    "RK": "Rajesh JTO",
    "RKM": "Riyaz JTO",
    "AMP": "Abdulla SDE",
    "N":  "Naveen JTO"
}

# col1, col2 = st.columns([4,1])

# with col1:
#     st.title("Attendance Viewer")

# with col2:
    
#         if st.button("🏠 Home"):
#             st.session_state.reset_week = True
#             st.rerun()

# if st.button("🏠 Attendance Viewer", key="home_btn"):
#     st.session_state.reset_week = True
#     st.rerun()

# st.markdown("""
#     <h3 style="display:inline-block; margin-left: 10px; font-weight: 500; font-size: 22px;">
#         Attendance Viewer
#     </h3>
# """, unsafe_allow_html=True)


col1, col2 = st.columns([1,4])

with col1:
    if st.button("🏠"):
        st.session_state.reset_week = True
        st.session_state.expander_collapsed = True  # collapse expander
        st.session_state.week_option = "-- Select a Week --"
        st.rerun()

with col2:
    st.markdown("""
        <h3 style="margin: 0; font-weight: 500; font-size: 22px;">
            Attendance Viewer
        </h3>
    """, unsafe_allow_html=True)




# col1, col2 = st.columns([1,4])

# with col1:
#     if st.button("🏠 Attendance Viewer"):
#         st.session_state.reset_week = True
#         st.rerun()

# with col2:
#     st.markdown("""
#         <h3 style="font-weight: 400; font-size: 22px; margin: 0;">Attendance Viewer</h3>
#     """, unsafe_allow_html=True)



# -------------------------------
# Google Sheets Authentication
# -------------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

try:
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
except Exception:
    creds = Credentials.from_service_account_file("attendance-app-479515-a2c99015276e.json", scopes=scope)


#creds = Credentials.from_service_account_file("attendance-app-479515-a2c99015276e.json", scopes=scope)
#creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
client = gspread.authorize(creds)
#sheet = client.open("AppTester").sheet1
sheet = client.open("MLP ONENOC DUTYCHART").sheet1

# Load raw sheet
values = sheet.get_all_values()

# -------------------------------
# Fix headers
# -------------------------------
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

# Convert date
df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce").dt.date


# ================================================================
# FUNCTION: Build attendance table for ANY required date
# ================================================================
def get_attendance_for_date(target_date):
    data = df[df["Date"] == target_date]

    if data.empty:
        return None

    data = data.copy()


       # --- Data Cleaning (Reinserted) ---
    # Convert empty strings from Google Sheets to proper NA values
    data = data.replace("", pd.NA) 
    # Drop columns that are entirely empty for this specific date
    data = data.dropna(axis=1, how="all")
    # ----------------------------------

    # --- New: Format Date/Day as requested: "Sunday, 30-11-2025" ---
    # target_date is a datetime.date object. We assume data only has one row for this date.
    
    # 1. Get the Day name (e.g., 'Sunday') and the formatted date part (DD-MM-YYYY)
    day_name = target_date.strftime("%A")
    formatted_date_part = target_date.strftime("%d-%m-%Y")
    
    # 2. Combine them into the 'Date' column
    combined_date_string = f"{day_name}, {formatted_date_part}"
    data["Date"] = combined_date_string
    
    # 3. Drop the redundant 'Day' column
    data = data.drop(columns=["Day"], errors="ignore")
    # -----------------------------------------------------------------

    

    # Columns to hide
    general_cols_hide = [
        "General", "General_2", "General_3", "General_4", "General_5",
        "General_6", "General_7", "General_8", "General_9", "General_10",
        "General_11", "General_12", "General_13"
    ]

    hide_cols_2=["Duty Leave_10"]

   # data = data.drop(columns=[c for c in general_cols_hide if c in data.columns])
    data = data.drop(columns=[c for c in hide_cols_2 if c in data.columns])










    

        # -------------------------------
    # NIGHT SHIFT CLEANUP + ORDER RESTORE
    # -------------------------------

    # 1. Identify all night columns

    night_cols = [
    c for c in data.columns
    if " ".join(c.split()).startswith("Night 20.00 to 8.00")
    ]

    #night_cols = [c for c in data.columns if c.startswith("Night 20.00 to 8.00")]

    # 2. Remove yesterday's repeat
    yesterday = target_date - datetime.timedelta(days=1)
    prev = df[df["Date"].apply(lambda d: d == yesterday)]
    #prev = df[df["Date"] == yesterday]

    if not prev.empty:
        for col in night_cols:
            #yesterday_people = set(prev[col].dropna().astype(str).str.strip())
            #data[col] = data[col].apply(
            #    lambda x: "" if str(x).strip() in yesterday_people else x
            #)
            yesterday_people = set(prev[col].dropna().astype(str).str.strip().str.upper())  # <-- added .str.upper()
            data[col] = data[col].apply(
            lambda x: "" if str(x).strip().upper() in yesterday_people else x  # <-- added .upper()
             )

    # 3. Find night columns that have data
    eligible_night_cols = [
        c for c in night_cols
        if data[c].dropna().astype(str).str.strip().any()
    ]

    # 4. Save their series data
    eligible_series = [data[c].copy() for c in eligible_night_cols]

    # 5. Get the original start index of night shifts
    if night_cols:
        original_start = data.columns.get_loc(night_cols[0])
    else:
        original_start = len(data.columns)

    # 6. Drop all night columns
    data = data.drop(columns=night_cols)

    # 7. Reinsert at original position with cleaned names
    for i, series in enumerate(eligible_series):
        new_name = "Night 20.00 to 8.00" if i == 0 else f"Night 20.00 to 8.00_{i+1}"
        data.insert(original_start + i, new_name, series)

          
    # Replace codes → names
    for col in data.columns:
        if col not in ["Date"]:
            data[col] = data[col].map(code_to_name).fillna(data[col])

    
  ###############################
  #General shift logic


        # Replace codes → names for all columns except Date
    for col in data.columns:
        if col not in ["Date"]:
            data[col] = data[col].map(code_to_name).fillna(data[col])

    # --- GENERAL SHIFT LOGIC ---
    general_cols = [c for c in data.columns if c.startswith("General")]

    general_count = sum(
        data[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().count()
        for col in general_cols if col in data.columns
    )

    if general_count > 3:
        data = data.drop(columns=[c for c in general_cols if c in data.columns])
    else:
        # Merge non-empty General columns into single "General Shift"
        def merge_general(row):
            names = [str(row[c]).strip() for c in general_cols if c in row and pd.notna(row[c]) and str(row[c]).strip() != ""]
            return ", ".join(names)

        if general_cols:
            first_idx = data.columns.get_loc(general_cols[0])
            data.insert(first_idx, "General Shift", data.apply(merge_general, axis=1))

        # Drop original General columns
        data = data.drop(columns=[c for c in general_cols if c in data.columns])




    #     # --- GENERAL SHIFT LOGIC ---
    # # Identify all general columns
    # general_cols = [c for c in data.columns if c.startswith("General")]

    # # Count how many General shift staff are present
    # general_count = 0
    # for col in general_cols:
    #     if col in data.columns:
    #         general_count += data[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().count()

    # # If more than 3 → hide General columns
    # if general_count > 3:
    #     data = data.drop(columns=[c for c in general_cols_hide if c in data.columns])
    # # else (<=3) → keep all general columns (do nothing)


    data.reset_index(drop=True, inplace=True)
    return data


# ================================================================
# SHOW TODAY + TOMORROW using same function
# ================================================================

ist = pytz.timezone("Asia/Kolkata")

now_ist = datetime.datetime.now(ist)
today = now_ist.date()
tomorrow = today + datetime.timedelta(days=1)


#ist = pytz.timezone("Asia/Kolkata")
#today = datetime.now(ist).date()

#tomorrow = today + datetime.timedelta(days=1)


#today = datetime.date.today()
#tomorrow = today + datetime.timedelta(days=1)

# -------------------------------
# DISPLAY TABLE STRUCTURE
# -------------------------------
# def show_attendance_block(title, date):
#     st.subheader(title)

#     result = get_attendance_for_date(date)

#     if result is None:
#         st.info(f"No attendance found for {date}")
#         return

#     # Detect mobile
#     ua = st.context.headers.get("User-Agent", "").lower()
#     is_mobile = "mobile" in ua or "android" in ua or "iphone" in ua

    


#     styled = (
#                 result.style
#                 .hide(axis="index")  # hide index
#                 .set_table_styles([
#                     {'selector': 'th', 'props': [('font-weight', 'bold'), ('font-size', '13px')]}  # header bold
#                 ])
#                 )
#     st.markdown(styled.to_html(escape=False), unsafe_allow_html=True)

def render_simple_text_block(title, data_df):
    

    if data_df is None or data_df.empty:
        st.warning(f"{title}: No data available.")
        return

    row = data_df.iloc[0]

    date_str = row["Date"]

    st.markdown(f"### {title}")
    st.markdown(f"**Date:** {date_str}\n")

    for col in data_df.columns:
        if col == "Date":
            continue
        value = str(row[col]).strip()
        if value and value.lower() != "nan":
            st.markdown(f"**{col}:** {value}")

    st.markdown("---")


def render_card_block(title, data_df, color_emoji="🟦"):
   

    if data_df is None or data_df.empty:
        st.warning(f"{title}: No data available.")
        return

    row = data_df.iloc[0]

    date_str = row["Date"]

    st.markdown(f"{color_emoji} **{title}**")
    st.markdown(f" **{date_str}**\n")

    for col in data_df.columns:
        if col == "Date":
            continue
        value = str(row[col]).strip()
        if value and value.lower() != "nan":
            st.markdown(f"- **{col}:** {value}")

    st.markdown("---")

   


def show_attendance_block(title, date, display_style):
    df_data = get_attendance_for_date(date)

    if df_data is None or df_data.empty:
        st.warning(f"{title}: No data available.")
        return



    if display_style == "A":
        render_simple_text_block(title, df_data)
    else:
        render_card_block(title, df_data)    

    




# Initialize session state FIRST
if "reset_week" not in st.session_state:
    st.session_state.reset_week = False

if "week_option" not in st.session_state:
    st.session_state.week_option = "-- Select a Week --"


# If reset flag is set, reset the dropdown BEFORE widget is rendered
if st.session_state.reset_week:
    st.session_state.week_option = "-- Select a Week --"
    st.session_state.reset_week = False
    st.rerun()




if "reset_week" not in st.session_state:
    st.session_state.reset_week = False


st.markdown("<br>", unsafe_allow_html=True)    


# with st.expander("📅 Choose a week (click to expand/collapse)", expanded=True):
#     week_option = st.selectbox(
#         "Choose a weekly attendance from the drop down below:",
#         ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
#         key="week_option"
#     )

# with st.expander("Choose a weekly attendance", expanded=True):
#     week_option = st.selectbox(
#         "",
#         ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
#         key="week_option"
#     )

# with st.expander("Choose a weekly attendance (click to expand/collapse)", expanded=False):
#     week_option = st.selectbox(
#         "",
#         ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
#         key="week_option",
#         label_visibility="collapsed"   # hides the label completely
#     )






import streamlit as st

st.markdown("""
    <style>
        /* Target expander title */
        button[data-testid="stExpanderHeader"] > div:first-child {
            font-weight: bold !important;
            font-size: 50px !important;  /* adjust as needed */
        }
    </style>
""", unsafe_allow_html=True)

# with st.expander("🗓️ Choose a weekly attendance", expanded=False):
#     week_option = st.selectbox(
#         "",
#         ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
#         key="week_option",
#         label_visibility="collapsed"
#     )

with st.expander("🗓️ **CHOOSE WEEKLY ATTENDANCE**", expanded=not st.session_state.expander_collapsed):
    week_option = st.selectbox(
        "",
        ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
        key="week_option",
        label_visibility="collapsed"
    )

# Update expander state based on selection
if st.session_state.week_option != "-- Select a Week --":
    st.session_state.expander_collapsed = False
else:
    st.session_state.expander_collapsed = True





# week_option = st.selectbox(
#     "Choose a weekly attendance from the drop down below:",
#     ["-- Select a Week --", "This Week", "Next Week", "Last Week"],
#     key="week_option"
# )

# Add spacing
st.markdown("<br>", unsafe_allow_html=True)  # two line breaks
display_style = random.choice(["A", "B"])

if week_option == "-- Select a Week --":
    show_attendance_block("🗓️ Today’s Attendance", today, display_style)
    show_attendance_block("🗓️ Tomorrow’s Attendance", tomorrow, display_style)


# Only show report if a real week is selected
if week_option != "-- Select a Week --":
    ##today = datetime.date.today()

    if week_option == "This Week":
        monday = today - datetime.timedelta(days=today.weekday())

    elif week_option == "Next Week":
        monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=7)

    elif week_option == "Last Week":
        monday = today - datetime.timedelta(days=today.weekday()) - datetime.timedelta(days=7)

    #if st.button("🏠 Back to Home"):
     #st.session_state.reset_week = True
    # st.rerun()    

    for i in range(7):
        day = monday + datetime.timedelta(days=i)
        result = get_attendance_for_date(day)
        


        if result is None:
            st.info(f"No attendance found for {day.strftime('%A - %d %b %Y')}")
            continue

        result = result.drop(columns=["Date", "Day"], errors="ignore")   
            


        #Display day heading
        st.markdown(
            f"<div style='text-align:right; font-size:13px; color:#777; margin:6px 0;'>"
            f"{day.strftime('%A, %d %b %Y')}"
            f"</div>",
            unsafe_allow_html=True
         )

        # st.markdown(
        #     f"<div style='text-align:right; font-size:14px; color:grey;'>"
        #     f"{day.strftime('%A, %d %b %Y')}"
        #     f"</div>",
        #     unsafe_allow_html=True
        # )



        #st.markdown(f"**{day.strftime('%A, %d %b %Y')}**")
        #st.subheader(day.strftime('%A - %d %b %Y'))

        # Detect mobile (optional, can customize styling)
        # ua = st.context.headers.get("User-Agent", "").lower()
        # is_mobile = "mobile" in ua or "android" in ua or "iphone" in ua2

        # styled = (
        #     result.style.apply(lambda r: ["font-weight: bold;"] * len(r), axis=1)
        #     .hide(axis="index")
        # )
        # st.markdown(styled.to_html(escape=False), unsafe_allow_html=True)

        # 
        
        styled = (
                result.style.hide(axis="index")
            )

        st.markdown(styled.to_html(escape=False), unsafe_allow_html=True)


        st.write("---")











