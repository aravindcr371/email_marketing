
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from supabase import create_client

# ------------------ Page config ------------------
st.set_page_config(layout="wide")

# ------------------ Supabase setup ------------------
SUPABASE_URL = "https://vupalstqgfzwxwlvengp.supabase.co"   # TODO: replace
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1cGFsc3RxZ2Z6d3h3bHZlbmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcwMTI0MjIsImV4cCI6MjA4MjU4ODQyMn0.tQsnAFYleVlRldH_nYW3QGhMvEQaYVH0yXNpkJqtkBY"  # TODO: replace
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TEAM = "Email Marketing"
MEMBERS = ["-- Select --","Rakesh","Sindhu","Swathi"]
COMPONENTS = ["-- Select --","Edits","Email Built","Legal","Meeting","Others",
              "PUSH","SMS","Wireframe Creation","Leave"]

RESET_KEYS = [
    "date_field", "member_field", "component_field",
    "tickets_field", "hours_field", "minutes_field", "comments_field"
]

if st.session_state.get("do_reset"):
    for k in RESET_KEYS:
        st.session_state.pop(k, None)
    st.session_state["do_reset"] = False

# ------------------ Public holidays ------------------
PUBLIC_HOLIDAYS = {
    date(2024, 12, 25),
    date(2025, 1, 1),
}

# ------------------ Shared helpers ------------------
def end_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return (date(y, m + 1, 1) - timedelta(days=1))

def working_days_between(start: date, end: date):
    days = pd.date_range(start, end, freq="D")
    return [d.normalize() for d in days if d.weekday() < 5 and d.date() not in PUBLIC_HOLIDAYS]

def build_period_options_and_months(df_dates: pd.Series):
    today = date.today()
    current_weekday = today.weekday()
    current_month = today.month
    current_year = today.year

    year_month = pd.to_datetime(df_dates, errors="coerce").dt.to_period("M")
    months_union = sorted([
        m for m in year_month.unique()
        if (m.year > 2024 or (m.year == 2024 and m.month >= 11))
    ])

    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    previous_month_period = pd.Period(f"{prev_year}-{prev_month:02d}")

    filtered_months = [m for m in months_union if m != previous_month_period]
    month_labels = [f"{m.strftime('%B %Y')}" for m in filtered_months]

    options = ["Current Week", "Previous Week", "Current Month", "Previous Month"] + month_labels
    return options, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year

def compute_weekdays_for_choice(choice, filtered_months, month_labels,
                                previous_month_period, today, current_weekday, current_month, current_year):
    if choice == "Current Week":
        start = today - timedelta(days=current_weekday)
        end = today
    elif choice == "Previous Week":
        start = today - timedelta(days=current_weekday + 7)
        end = start + timedelta(days=4)
    elif choice == "Current Month":
        start = date(current_year, current_month, 1)
        end = today
    elif choice == "Previous Month":
        pm = previous_month_period
        start = date(pm.year, pm.month, 1)
        end = end_of_month(pm.year, pm.month)
    else:
        sel_period = filtered_months[month_labels.index(choice)]
        start = date(sel_period.year, sel_period.month, 1)
        end = end_of_month(sel_period.year, sel_period.month)

    return working_days_between(start, end)

# ------------------ Tabs ------------------
tab1, tab2, tab3 = st.tabs(["📝 Email Marketing", "📊 Visuals", "📈 Utilization & Occupancy"])

# ------------------ TAB 1 ------------------
with tab1:
    st.title("Email Marketing")
    st.text_input("Team", TEAM, disabled=True)

    with st.form(key="entry_form", clear_on_submit=False):
        date_value = st.date_input("Date")
        c1, c2 = st.columns(2)
        with c1:
            member = st.selectbox("Member", MEMBERS)
        with c2:
            component = st.selectbox("Component", COMPONENTS)

        tickets = st.number_input("Tickets", min_value=0, step=1, key="tickets_field")

        c3, c4 = st.columns(2)
        with c3:
            hours = st.selectbox("Hours", list(range(24)), key="hours_field")
        with c4:
            minutes = st.selectbox("Minutes", list(range(60)), key="minutes_field")

        comments = st.text_area("Comments", key="comments_field")
        submitted = st.form_submit_button("Submit")

    if submitted:
        if isinstance(date_value, (datetime, date)) and member != "-- Select --" and component != "-- Select --":
            d = date_value if isinstance(date_value, date) else date_value.date()
            duration_minutes = int(hours) * 60 + int(minutes)
            new_row = {
                "team": TEAM,
                "date": d.isoformat(),
                "week": d.isocalendar()[1],
                "month": d.strftime("%B"),
                "member": member,
                "component": component,
                "tickets": int(tickets),
                "duration": duration_minutes,
                "comments": (comments or "").strip() or None
            }
            try:
                res = supabase.table("email_marketing").insert(new_row).execute()
                if res.data:
                    st.success("Saved successfully")
                    st.session_state["do_reset"] = True
                    st.rerun()
                else:
                    st.warning("Insert may not have returned data")
            except Exception as e:
                st.error(f"Error inserting: {e}")
        else:
            st.warning("Please select a member and component, and pick a date before submitting.")

    # Fetch and filter by team only
    try:
        response = supabase.table("email_marketing").select("*").order("date", desc=True).execute()
        df1 = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        df1 = pd.DataFrame()

    if not df1.empty:
        df1["date"] = pd.to_datetime(df1["date"], errors="coerce")
        df1 = df1[df1["team"] == TEAM]  # Show only entries for TEAM

        # Drop unwanted columns: id, banners, sku, pages if present
        drop_cols = [col for col in ["id", "banners", "sku", "pages"] if col in df1.columns]
        df1 = df1.drop(columns=drop_cols)

        st.subheader(f"Latest entries for {TEAM} (sorted by Date descending)")
        st.dataframe(df1, use_container_width=True)

# ------------------ TAB 2 ------------------
with tab2:
    st.title("Visuals Dashboard")
    try:
        response = supabase.table("email_marketing").select("*").execute()
        vdf = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        vdf = pd.DataFrame()

    if vdf.empty:
        st.info("No data available")
    else:
        vdf["date"] = pd.to_datetime(vdf["date"], errors="coerce")
        options, filtered_months, month_labels, previous_month_period, today, current_weekday, current_month, current_year = build_period_options_and_months(vdf["date"])
        choice = st.selectbox("Select period", options, key="tab2_period")
        weekdays = compute_weekdays_for_choice(choice, filtered_months, month_labels, previous_month_period,
                                               today, current_weekday, current_month, current_year)
        filtered = vdf[vdf["date"].dt.normalize().isin(weekdays)]

        if filtered.empty:
            st.info("No visuals for selected period.")
        else:
            week_grouped = filtered.groupby("week")[["tickets"]].sum().reset_index().sort_values("week")
            member_grouped = filtered.groupby("member")[["tickets"]].sum().reset_index()

            def bar_with_labels(df, x_field, y_field, color, x_type="N", y_type="Q", x_title="", y_title=""):
                bar = alt.Chart(df).mark_bar(color=color).encode(
                    x=alt.X(f"{x_field}:{x_type}", title=x_title),
                    y=alt.Y(f"{y_field}:{y_type}", title=y_title)
                )
                text = alt.Chart(df).mark_text(align="center", baseline="bottom", dy=-5, color="black").encode(
                    x=f"{x_field}:{x_type}",
                    y=f"{y_field}:{y_type}",
                    text=f"{y_field}:{y_type}"
                )
                return bar + text

            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.subheader("Tickets by week")
                chart = bar_with_labels(week_grouped, "week", "tickets", "steelblue",
                                        x_type="O", y_type="Q", x_title="Week", y_title="Tickets")
                st.altair_chart(chart, use_container_width=True)
            with r1c2:
                st.subheader("Tickets by member")
                chart = bar_with_labels(member_grouped, "member", "tickets", "steelblue",
                                        x_type="N", y_type="Q", x_title="Member", y_title="Tickets")
                st.altair_chart(chart, use_container_width=True)

            st.subheader("By Component (Sum of Tickets)")
            component_grouped = filtered.groupby("component")[["tickets"]].sum().reset_index()
            component_grouped["component"] = component_grouped["component"].fillna("Unspecified")
            component_grouped.loc[component_grouped["component"].eq(""), "component"] = "Unspecified"
            component_grouped = component_grouped.sort_values("tickets", ascending=False)

            bar = alt.Chart(component_grouped).mark_bar(color="#4C78A8").encode(
                x=alt.X("component:N", title="Component",
                        sort=alt.SortField(field="tickets", order="descending")),
                y=alt.Y("tickets:Q", title="Tickets")
            ).properties(height=400)
            text = alt.Chart(component_grouped).mark_text(align="center", baseline="bottom", dy=-5, color="black").encode(
                x=alt.X("component:N", sort=alt.SortField(field="tickets", order="descending")),
                y=alt.Y("tickets:Q"),
                text=alt.Text("tickets:Q")
            )
            chart = (bar + text).encode(
                tooltip=[
                    alt.Tooltip("component:N", title="Component"),
                    alt.Tooltip("tickets:Q", title="Tickets"),
                ]
            )
            st.altair_chart(chart, use_container_width=True)
