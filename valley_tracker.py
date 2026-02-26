import streamlit as st
import pandas as pd
import datetime
import json
import os

# ==========================================
# 1. DATABASE SETUP & TIMEZONE
# ==========================================
DATA_FILE = "atc_data.json"

def load_data():
    """Loads flight data from a permanent file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    """Saves flight data to a permanent file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_ist_now():
    """Calculates India Standard Time safely."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_naive = utc_now.replace(tzinfo=None) + datetime.timedelta(hours=5, minutes=30)
    return ist_naive, utc_now

def log_event(message):
    ist_now, _ = get_ist_now()
    today_date = ist_now.strftime("%Y-%m-%d")
    filename = f"ATC_Log_{today_date}.txt"
    current_time = ist_now.strftime("%H:%M:%S")
    try:
        with open(filename, "a") as file:
            file.write(f"[{current_time}] {message}\n")
    except:
        pass

def parse_time_string(time_str):
    clean_str = str(time_str).replace(":", "").strip()
    if len(clean_str) in [3, 4] and clean_str.isdigit():
        clean_str = clean_str.zfill(4) 
        hour = int(clean_str[:2])
        minute = int(clean_str[2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            ist_now, _ = get_ist_now()
            today = ist_now.date() 
            return datetime.datetime.combine(today, datetime.time(hour, minute))
    return None

# ==========================================
# 2. PAGE CONFIG & INITIALIZATION
# ==========================================
st.set_page_config(page_title="Pasighat ATC Board", layout="wide", initial_sidebar_state="expanded")

local_now, utc_now = get_ist_now()

# LOAD ACTIVE FLIGHTS FROM THE FILE (Refresh Proof)
active_flights = load_data()

route_map = {
    "Juliet (J) Valley": ["YINGKIONG", "TUTING", "PANGIN", "PASIGHAT", "BOLENG", "GELING", "MARIAN"],
    "Kilo (K) Valley": ["ROING", "ANINI", "DIBANG", "HUNLI", "DAMBUEN", "ETALIN", "MALINEY"],
    "Lima (L) Valley": ["TEZU", "HAYULIANG", "WALONG", "ALONG", "CHAGLAGAM", "KIBITHU", "HAWA CAMP"]
}
valley_names = list(route_map.keys())

def get_auto_valley(from_p, to_p):
    combined = [from_p.upper(), to_p.upper()]
    for i, (v_name, points) in enumerate(route_map.items()):
        if any(p in points for p in combined):
            return i
    return 0

# ==========================================
# 3. SIDEBAR (CLOCKS + ADD + MANAGE)
# ==========================================
with st.sidebar:
    st.markdown("### 🕒 MASTER CLOCKS")
    st.info(f"🌐 **UTC (ZULU):** {utc_now.strftime('%H:%M:%S Z')}")
    st.success(f"📍 **PASIGHAT (IST):** {local_now.strftime('%H:%M:%S')}")
    st.markdown("---")

    st.header("🛫 ADD TRAFFIC")
    ac_type = st.text_input("A/C TYPE")
    callsign = st.text_input("CALLSIGN")
    from_loc = st.text_input("FROM")
    to_loc = st.text_input("TO")
    level = st.text_input("LEVEL")
    
    auto_idx = get_auto_valley(from_loc, to_loc)
    target_v = st.selectbox("VALLEY NAME", valley_names, index=auto_idx)
    
    iff_code = st.text_input("IFF / SQUAWK")
    en_str = st.text_input("ENTRY HHMM", value=local_now.strftime("%H%M"))
    exit_str = st.text_input("EXIT HHMM")

    if st.button("✅ ADD AIRCRAFT", use_container_width=True):
        en_o = parse_time_string(en_str)
        ex_o = parse_time_string(exit_str)
        if callsign and en_o and ex_o:
            new_flight = {
                "TYPE": ac_type.upper(), "CALLSIGN": callsign.upper(),
                "FROM": from_loc.upper(), "TO": to_loc.upper(),
                "LEVEL": level.upper(), "VALLEY NAME": target_v,
                "IFF": iff_code, "VALLEY ENTRY": en_o.strftime("%H:%M"),
                "VALLEY EXIT": ex_o.strftime("%H:%M")
            }
            active_flights.append(new_flight)
            save_data(active_flights) # SAVE TO FILE
            log_event(f"ADDED: {callsign.upper()}")
            st.rerun()

    # --- MANAGEMENT SUITE ---
    if active_flights:
        st.markdown("---")
        st.header("🔧 MANAGEMENT")
        active_cs = [f["CALLSIGN"] for f in active_flights]
        sel_ac = st.selectbox("Select A/C to Update", active_cs)
        
        new_rev_exit = st.text_input("New Revised Exit HHMM")
        if st.button("Update Exit Time", use_container_width=True):
            new_ex_o = parse_time_string(new_rev_exit)
            if new_ex_o:
                for f in active_flights:
                    if f["CALLSIGN"] == sel_ac:
                        f["VALLEY EXIT"] = new_ex_o.strftime("%H:%M")
                save_data(active_flights) # SAVE TO FILE
                st.rerun()
        
        if st.button("🚨 REMOVE AIRCRAFT", use_container_width=True):
            active_flights = [f for f in active_flights if f["CALLSIGN"] != sel_ac]
            save_data(active_flights) # SAVE TO FILE
            st.rerun()

# ==========================================
# 4. MAIN DISPLAY (VALLEY TABLES)
# ==========================================
st.title("📡 PASIGHAT ATC: VALLEY TRAFFIC PROGRESS BOARD")
st.markdown("---")

def style_overdue(row):
    if row['Status'] == '🔴 OVERDUE':
        return ['background-color: #8b0000; color: white; font-weight: bold'] * len(row)
    return [''] * len(row)

cols_seq = ["TYPE", "CALLSIGN", "FROM", "TO", "LEVEL", "VALLEY NAME", "IFF", "VALLEY ENTRY", "VALLEY EXIT", "MINS REM", "Status"]

for valley in ["Juliet (J) Valley", "Lima (L) Valley", "Kilo (K) Valley"]:
    st.subheader(f"📍 {valley}")
    v_flights = [f for f in active_flights if f["VALLEY NAME"] == valley]
    
    if v_flights:
        # Sort dynamically by calculating time objects on the fly
        v_flights = sorted(v_flights, key=lambda x: parse_time_string(x["VALLEY EXIT"]) or local_now)
        display_data = []
        
        for idx, f in enumerate(v_flights):
            entry_obj = parse_time_string(f["VALLEY ENTRY"])
            exit_obj = parse_time_string(f["VALLEY EXIT"])
            
            # Safe Countdown
            mins_rem = int((exit_obj - local_now).total_seconds() / 60) if exit_obj else 0
            status = "🔴 OVERDUE" if mins_rem <= 0 else "🟢 ENROUTE"
            
            # Conflict Alert
            for o_f in v_flights[idx+1:]:
                other_entry_obj = parse_time_string(o_f["VALLEY ENTRY"])
                if f["LEVEL"] == o_f["LEVEL"] and entry_obj and other_entry_obj:
                    t_diff = abs((entry_obj - other_entry_obj).total_seconds() / 60)
                    if t_diff <= 10:
                        st.error(f"🚨 CONFLICT: {f['CALLSIGN']} & {o_f['CALLSIGN']} at {f['LEVEL']} (within 10m)")

            display_data.append({
                "TYPE": f["TYPE"], "CALLSIGN": f["CALLSIGN"], "FROM": f["FROM"], "TO": f["TO"],
                "LEVEL": f["LEVEL"], "VALLEY NAME": f["VALLEY NAME"], "IFF": f["IFF"],
                "VALLEY ENTRY": f["VALLEY ENTRY"], "VALLEY EXIT": f["VALLEY EXIT"], 
                "MINS REM": f"{mins_rem}m", "Status": status
            })
            
        df = pd.DataFrame(display_data, columns=cols_seq)
        st.dataframe(df.style.apply(style_overdue, axis=1), hide_index=True, use_container_width=True)
    else:
        st.info(f"No active traffic in {valley}.")
    st.markdown("<br>", unsafe_allow_html=True)

if st.button("Clear All Data (Shift End)"):
    save_data([]) # EMPTIES THE FILE
    st.rerun()
