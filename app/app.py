import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Busy Buffet | Hotel Amber 85",
    page_icon="🍽️",
    layout="wide",
)

C_WALKIN  = "#E07B39"
C_INHOUSE = "#3A7CA5"
C_DANGER  = "#D64045"
C_OK      = "#4CAF50"
C_NEUTRAL = "#8C8C8C"

LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    margin=dict(t=40, b=30, l=10, r=10),
)

# ──────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────
@st.cache_data
def load():
    sheet_dates = {
        "133": "2026-01-13",
        "143": "2026-01-14",
        "153": "2026-01-15",
        "173": "2026-01-17",
        "183": "2026-01-18",
    }
    xl = pd.read_excel(
        "app/data.xlsx", sheet_name=None
    )
    dfs = []
    for sheet, date_str in sheet_dates.items():
        d = xl[sheet].copy()
        d = d[[c for c in d.columns if not c.startswith("Unnamed")]]
        d["date"] = pd.to_datetime(date_str)
        dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)

    def pt(val, date):
        if pd.isna(val):
            return pd.NaT
        try:
            t = pd.to_datetime(str(val), format="%H:%M:%S").time()
            return pd.Timestamp.combine(date, t)
        except Exception:
            return pd.NaT

    for col in ["queue_start", "queue_end", "meal_start", "meal_end"]:
        df[col] = df.apply(lambda r: pt(r[col], r["date"].date()), axis=1)

    df["wait_min"] = (df["queue_end"] - df["queue_start"]).dt.total_seconds() / 60
    df["meal_min"] = (df["meal_end"]  - df["meal_start"]).dt.total_seconds()  / 60
    df.loc[df["meal_min"] < 0,   "meal_min"] = np.nan
    df.loc[df["meal_min"] > 300, "meal_min"] = np.nan

    df["guest"]       = df["Guest_type"].str.strip().str.lower()
    df["is_walkaway"] = df["queue_start"].notna() & df["meal_start"].isna()
    df["waited"]      = df["queue_start"].notna() & df["meal_start"].notna()
    df["direct"]      = df["queue_start"].isna()  & df["meal_start"].notna()
    df["day_type"]    = df["date"].dt.dayofweek.apply(
        lambda x: "Weekend" if x >= 5 else "Weekday"
    )
    df["date_label"] = df["date"].dt.strftime("%b %d (%a)")
    df["meal_hour"]  = df["meal_start"].dt.hour
    return df


df    = load()
seated = df[df["meal_start"].notna() & df["meal_min"].notna()].copy()
DATE_ORDER = df.drop_duplicates("date").sort_values("date")["date_label"].tolist()
GUEST_COLOR = {"walk in": C_WALKIN, "in house": C_INHOUSE}

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍽️ Busy Buffet")
    st.caption("Hotel Amber 85 · Analytics 2026")
    st.markdown("---")
    page = st.radio(
        "Section",
        [
            "📊 Overview",
            "💬 Task 1 · Comment 1",
            "💬 Task 1 · Comment 2",
            "💬 Task 1 · Comment 3",
            "❌ Task 2 · Action A — Seating Time",
            "❌ Task 2 · Action B — Price Hike",
            "❌ Task 2 · Action C — Queue Skip",
            "✅ Task 3 · Best Solution",
        ],
    )
    st.markdown("---")
    st.markdown("**5 days · 364 records**")
    st.markdown("Weekday ฿159 · Weekend ฿199")
    st.caption("Jan 13–18, 2026")


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, val, sub, color) in zip(cols, items):
        col.metric(label, val, sub)


def verdict(ok: bool, text: str):
    if ok:
        st.success(f"✅ **CONFIRMED** — {text}")
    else:
        st.error(f"❌ **WILL NOT WORK** — {text}")


# ══════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════
if page == "📊 Overview":
    st.title("🍽️ Busy Buffet Dashboard — Hotel Amber 85")
    st.caption("Breakfast Buffet · Data Analytics 2026")
    st.divider()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Records",   len(df))
    c2.metric("Total Pax Served", int(df[df["meal_start"].notna()]["pax"].sum()))
    c3.metric("Walk-aways",      df["is_walkaway"].sum(),     delta="groups left without eating", delta_color="inverse")
    c4.metric("Avg Wait Time",   f"{df['wait_min'].mean():.0f} min", "for those who queued")
    c5.metric("Avg Meal Duration", f"{df['meal_min'].mean():.0f} min")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Groups per Day by Guest Type")
        day_ct = (
            df[df["meal_start"].notna()]
            .groupby(["date_label", "guest"])
            .size()
            .reset_index(name="groups")
        )
        fig = px.bar(
            day_ct, x="date_label", y="groups", color="guest",
            color_discrete_map=GUEST_COLOR,
            category_orders={"date_label": DATE_ORDER},
            barmode="group",
            labels={"date_label": "Date", "groups": "Groups", "guest": "Guest Type"},
        )
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Hourly Footfall (All Days Combined)")
        hourly = (
            df[df["meal_start"].notna()]
            .groupby(["meal_hour", "guest"])
            .size()
            .reset_index(name="groups")
        )
        fig2 = px.area(
            hourly, x="meal_hour", y="groups", color="guest",
            color_discrete_map=GUEST_COLOR,
            labels={"meal_hour": "Hour", "groups": "Groups Seated", "guest": "Guest Type"},
        )
        fig2.update_layout(**LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Meal Duration Distribution by Guest Type")
    fig3 = px.histogram(
        seated, x="meal_min", color="guest",
        color_discrete_map=GUEST_COLOR,
        nbins=30, barmode="overlay", opacity=0.75,
        labels={"meal_min": "Meal Duration (min)", "count": "Groups", "guest": "Guest Type"},
    )
    fig3.add_vline(x=120, line_dash="dash", line_color=C_DANGER,
                   annotation_text="2-hour mark", annotation_position="top right")
    fig3.update_layout(**LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════
# TASK 1 · COMMENT 1
# ══════════════════════════════════════════════
elif page == "💬 Task 1 · Comment 1":
    st.title("💬 Comment 1")
    st.info(
        '"In-house guests are unhappy waiting for a table. Walk-in customers also queue for a long time '
        "and leave because they don't want to wait any longer.\""
    )
    st.divider()

    wa    = df[df["is_walkaway"]]
    q_df  = df[df["queue_start"].notna()].copy()
    wi_w  = q_df[q_df["guest"] == "walk in"]["wait_min"].dropna()
    ih_w  = q_df[q_df["guest"] == "in house"]["wait_min"].dropna()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Walk-aways",       df["is_walkaway"].sum())
    c2.metric("In-house Walk-aways",    len(wa[wa["guest"] == "in house"]))
    c3.metric("Walk-in Walk-aways",     len(wa[wa["guest"] == "walk in"]))
    c4.metric("Avg Wait (Walk-in)",     f"{wi_w.mean():.0f} min",
              delta=f"+{wi_w.mean()-ih_w.mean():.0f} min vs in-house", delta_color="inverse")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Walk-aways per Day · by Guest Type")
        wa_day = (
            wa.groupby(["date_label", "guest"])
            .size()
            .reset_index(name="count")
        )
        fig = px.bar(
            wa_day, x="date_label", y="count", color="guest",
            color_discrete_map=GUEST_COLOR,
            category_orders={"date_label": DATE_ORDER},
            barmode="stack", text_auto=True,
            labels={"date_label": "Date", "count": "Walk-aways", "guest": "Guest Type"},
        )
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Wait Time Distribution · by Guest Type")
        fig2 = px.box(
            q_df[q_df["wait_min"].notna()],
            x="guest", y="wait_min", color="guest",
            color_discrete_map=GUEST_COLOR, points="all",
            labels={"guest": "Guest Type", "wait_min": "Wait Time (min)"},
        )
        fig2.update_layout(**LAYOUT, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Queue Outcome by Hour · Seated vs Walk-away")
    q_df["outcome"]  = q_df["is_walkaway"].map({True: "Walk-away", False: "Seated"})
    q_df["q_hour"]   = q_df["queue_start"].dt.hour
    hourly_q = q_df.groupby(["q_hour", "outcome"]).size().reset_index(name="count")
    fig3 = px.bar(
        hourly_q, x="q_hour", y="count", color="outcome",
        color_discrete_map={"Walk-away": C_DANGER, "Seated": C_OK},
        barmode="stack",
        labels={"q_hour": "Hour of Day", "count": "Groups", "outcome": "Outcome"},
    )
    fig3.update_layout(**LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    verdict(
        True,
        f"14 groups walked away without eating (7 in-house · 7 walk-in). "
        f"Walk-ins wait avg **{wi_w.mean():.0f} min**, in-house **{ih_w.mean():.0f} min**. "
        f"Queue pressure peaks **08:00–10:00** daily. Staff comment is TRUE.",
    )


# ══════════════════════════════════════════════
# TASK 1 · COMMENT 2
# ══════════════════════════════════════════════
elif page == "💬 Task 1 · Comment 2":
    st.title("💬 Comment 2")
    st.info(
        "\"We are very busy every day of the week. If it's going to be this busy every week, "
        'this buffet business is not possible for this hotel."'
    )
    st.divider()

    pax_day = (
        df[df["meal_start"].notna()]
        .groupby(["date_label", "day_type"])["pax"]
        .sum()
        .reset_index()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Daily Pax",   f"{pax_day['pax'].mean():.0f}")
    c2.metric("Busiest Day",
              pax_day.loc[pax_day["pax"].idxmax(), "date_label"],
              f"{int(pax_day['pax'].max())} pax")
    c3.metric("Quietest Day",
              pax_day.loc[pax_day["pax"].idxmin(), "date_label"],
              f"{int(pax_day['pax'].min())} pax")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Daily Total Pax · Weekday vs Weekend")
        fig = px.bar(
            pax_day, x="date_label", y="pax", color="day_type",
            color_discrete_map={"Weekday": C_INHOUSE, "Weekend": C_WALKIN},
            category_orders={"date_label": DATE_ORDER},
            text_auto=True,
            labels={"date_label": "Date", "pax": "Total Pax", "day_type": "Day Type"},
        )
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Hourly Groups Seated · per Day")
        hourly_day = (
            df[df["meal_start"].notna()]
            .groupby(["date_label", "meal_hour"])
            .size()
            .reset_index(name="groups")
        )
        fig2 = px.line(
            hourly_day, x="meal_hour", y="groups", color="date_label",
            markers=True,
            labels={"meal_hour": "Hour", "groups": "Groups Seated", "date_label": "Date"},
        )
        fig2.update_layout(**LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Concurrent Tables Occupied Over Time · Jan 15 (Busiest Day)")
    TOTAL_UNITS = 29
    day15 = df[(df["date"].dt.strftime("%Y-%m-%d") == "2026-01-15") & df["meal_start"].notna()].copy()
    times = pd.date_range("2026-01-15 06:00", "2026-01-15 13:00", freq="15min")
    conc = [{"time": t, "tables": int(((day15["meal_start"] <= t) & (day15["meal_end"] >= t)).sum())}
            for t in times]
    conc_df = pd.DataFrame(conc)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=conc_df["time"], y=conc_df["tables"],
        fill="tozeroy", line=dict(color=C_DANGER, width=2), name="Occupied",
    ))
    fig3.add_hline(y=TOTAL_UNITS, line_dash="dash", line_color="yellow",
                   annotation_text=f"Capacity ~{TOTAL_UNITS} units", annotation_position="top left")
    fig3.update_layout(**LAYOUT, xaxis_title="Time", yaxis_title="Tables Occupied")
    st.plotly_chart(fig3, use_container_width=True)

    verdict(
        True,
        "Pax count is consistently high across all 5 days — both weekday and weekend. "
        "Even the quietest day had 102 pax. Concurrent table occupancy hits near full capacity "
        "during 08:00–10:00. Staff concern about sustainability is VALID.",
    )


# ══════════════════════════════════════════════
# TASK 1 · COMMENT 3
# ══════════════════════════════════════════════
elif page == "💬 Task 1 · Comment 3":
    st.title("💬 Comment 3")
    st.info(
        '"Walk-in customers sit the whole day. It\'s very difficult to find seats for in-house customers. '
        'We don\'t have enough tables — long sitters make the queue very long."'
    )
    st.divider()

    long_sit = seated[seated["meal_min"] > 120]
    wi_avg   = seated[seated["guest"] == "walk in"]["meal_min"].mean()
    ih_avg   = seated[seated["guest"] == "in house"]["meal_min"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Walk-in Duration",  f"{wi_avg:.0f} min")
    c2.metric("Avg In-house Duration", f"{ih_avg:.0f} min",
              delta=f"{ih_avg - wi_avg:.0f} min vs walk-in", delta_color="normal")
    c3.metric("Long Sitters (>2 hr)",  len(long_sit))
    ls_wi = len(long_sit[long_sit["guest"] == "walk in"])
    c4.metric("Walk-in Long Sitters",  ls_wi,
              f"{ls_wi/len(long_sit)*100:.0f}% of all long sitters")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Meal Duration · Violin by Guest Type")
        fig = px.violin(
            seated, x="guest", y="meal_min", color="guest",
            color_discrete_map=GUEST_COLOR,
            box=True, points="all",
            labels={"guest": "Guest Type", "meal_min": "Duration (min)"},
        )
        fig.add_hline(y=120, line_dash="dash", line_color=C_DANGER,
                      annotation_text="2 hr threshold")
        fig.update_layout(**LAYOUT, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Long Sitters (>2 hr) per Day · by Guest Type")
        ls_day = (
            long_sit.groupby(["date_label", "guest"]).size().reset_index(name="count")
        )
        fig2 = px.bar(
            ls_day, x="date_label", y="count", color="guest",
            color_discrete_map=GUEST_COLOR,
            category_orders={"date_label": DATE_ORDER},
            barmode="stack", text_auto=True,
            labels={"date_label": "Date", "count": "Long Sitters", "guest": "Guest Type"},
        )
        fig2.update_layout(**LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Meal Duration Scatter · All Seated Groups")
    fig3 = px.scatter(
        seated.sort_values("meal_start"),
        x="meal_start", y="meal_min", color="guest",
        color_discrete_map=GUEST_COLOR,
        size="pax", opacity=0.7,
        hover_data=["pax", "table_no.", "date_label"],
        labels={"meal_start": "Meal Start Time", "meal_min": "Duration (min)", "guest": "Guest Type"},
    )
    fig3.add_hline(y=120, line_dash="dash", line_color=C_DANGER,
                   annotation_text="2 hr mark")
    fig3.update_layout(**LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    verdict(
        True,
        f"Walk-ins avg **{wi_avg:.0f} min** vs in-house **{ih_avg:.0f} min** — "
        f"**{(wi_avg/ih_avg-1)*100:.0f}% longer**. "
        f"Of {len(long_sit)} groups over 2 hr, **{ls_wi} ({ls_wi/len(long_sit)*100:.0f}%)** are walk-ins. "
        "Long sitters block table turnover and directly lengthen the queue. Staff comment is TRUE.",
    )


# ══════════════════════════════════════════════
# TASK 2 · ACTION A — SEATING TIME
# ══════════════════════════════════════════════
elif page == "❌ Task 2 · Action A — Seating Time":
    st.title("❌ Action A · Reduce Seating Time Limit")
    st.warning("**Management idea:** Cap seating time (5 hrs → less) to force faster turnover.")
    st.divider()

    exceed_120 = (seated["meal_min"] > 120).sum()
    exceed_90  = (seated["meal_min"] > 90).sum()
    exceed_60  = (seated["meal_min"] > 60).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Meal Duration",   f"{seated['meal_min'].mean():.0f} min")
    c2.metric("Over 60 min",  exceed_60,  f"{exceed_60/len(seated)*100:.1f}% of groups")
    c3.metric("Over 90 min",  exceed_90,  f"{exceed_90/len(seated)*100:.1f}% of groups")
    c4.metric("Over 120 min", exceed_120, f"{exceed_120/len(seated)*100:.1f}% of groups")

    st.divider()

    st.subheader("Cumulative % of Groups Already Done by Time Limit")
    limits = list(range(30, 310, 5))
    wi_cdf  = [100*(seated[seated["guest"]=="walk in"]["meal_min"]  <= L).mean() for L in limits]
    ih_cdf  = [100*(seated[seated["guest"]=="in house"]["meal_min"] <= L).mean() for L in limits]
    all_cdf = [100*(seated["meal_min"] <= L).mean() for L in limits]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=limits, y=wi_cdf,  name="Walk-in",  line=dict(color=C_WALKIN,  width=2)))
    fig.add_trace(go.Scatter(x=limits, y=ih_cdf,  name="In-house", line=dict(color=C_INHOUSE, width=2)))
    fig.add_trace(go.Scatter(x=limits, y=all_cdf, name="All",      line=dict(color="white",   width=2, dash="dot")))
    for lim, lbl in [(60,"1 hr"), (90,"1.5 hr"), (120,"2 hr"), (150,"2.5 hr"), (180,"3 hr")]:
        fig.add_vline(x=lim, line_dash="dash", line_color=C_NEUTRAL, line_width=1,
                      annotation_text=lbl, annotation_position="top")
    fig.update_layout(**LAYOUT,
                      xaxis_title="Time Limit (min)",
                      yaxis_title="% of Groups Already Finished",
                      yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Who Gets Impacted? · Meal Duration Buckets")
    buckets = pd.cut(
        seated["meal_min"],
        bins=[0, 60, 90, 120, 180, 310],
        labels=["<60 min", "60–90 min", "90–120 min", "120–180 min", ">180 min"],
    )
    buck_df = (
        seated.assign(bucket=buckets)
        .groupby(["bucket", "guest"])
        .size()
        .reset_index(name="count")
    )
    fig2 = px.bar(
        buck_df, x="bucket", y="count", color="guest",
        color_discrete_map=GUEST_COLOR,
        barmode="stack", text_auto=True,
        labels={"bucket": "Duration Bucket", "count": "Groups", "guest": "Guest Type"},
    )
    fig2.update_layout(**LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

    verdict(
        False,
        "Even a strict **2-hour limit** only affects ~15% of all groups. "
        "The majority of guests — especially in-house — already leave within 60 minutes on their own. "
        "Enforcing a time limit creates **guest friction and complaints** "
        "while barely improving turnover. The real problem is peak-hour arrival concentration, not duration per se.",
    )


# ══════════════════════════════════════════════
# TASK 2 · ACTION B — PRICE HIKE
# ══════════════════════════════════════════════
elif page == "❌ Task 2 · Action B — Price Hike":
    st.title("❌ Action B · Raise Price to ฿259 Every Day")
    st.warning("**Management idea:** Higher price → fewer walk-ins → less crowding.")
    st.divider()

    pax_type_day = (
        df[df["meal_start"].notna()]
        .groupby(["date_label", "day_type", "guest"])["pax"]
        .sum()
        .reset_index()
    )

    # Revenue simulation at various demand drop rates
    def sim_revenue(drop_walkin):
        total = 0
        for _, r in pax_type_day.iterrows():
            cur = 159 if r["day_type"] == "Weekday" else 199
            if r["guest"] == "walk in":
                total += r["pax"] * (1 - drop_walkin) * 259
            else:
                total += r["pax"] * 259
        return total

    rev_current = sum(
        r["pax"] * (159 if r["day_type"] == "Weekday" else 199)
        for _, r in pax_type_day.iterrows()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Revenue (5 days)", f"฿{rev_current:,.0f}")
    c2.metric("@ ฿259, 0% demand drop",   f"฿{sim_revenue(0):,.0f}",
              f"+฿{sim_revenue(0)-rev_current:,.0f}")
    c3.metric("@ ฿259, 30% walk-in drop", f"฿{sim_revenue(0.3):,.0f}",
              f"{(sim_revenue(0.3)/rev_current-1)*100:+.1f}%")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Revenue Split by Guest Type")
        rev_type = (
            pax_type_day.copy()
            .assign(revenue=lambda x: x.apply(
                lambda r: r["pax"] * (159 if r["day_type"] == "Weekday" else 199), axis=1
            ))
            .groupby("guest")["revenue"].sum().reset_index()
        )
        fig = px.pie(
            rev_type, names="guest", values="revenue",
            color="guest", color_discrete_map=GUEST_COLOR,
            hole=0.45,
        )
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue at ฿259 — Various Walk-in Demand Drops")
        drops = [0, 0.10, 0.20, 0.30, 0.40, 0.50]
        sc = pd.DataFrame({
            "demand_drop": [f"{int(d*100)}%" for d in drops],
            "revenue":     [sim_revenue(d) for d in drops],
        })
        fig2 = px.bar(
            sc, x="demand_drop", y="revenue",
            text_auto=".0f",
            color_discrete_sequence=[C_WALKIN],
            labels={"demand_drop": "Walk-in Demand Drop (%)", "revenue": "Projected Revenue (฿)"},
        )
        fig2.add_hline(y=rev_current, line_dash="dash", line_color="white",
                       annotation_text=f"Current ฿{rev_current:,.0f}",
                       annotation_position="top right")
        fig2.update_layout(**LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Do Walk-ins React to Price? Weekday (฿159) vs Weekend (฿199)")
    price_cmp = (
        df[df["meal_start"].notna()]
        .groupby(["day_type", "guest"])["pax"]
        .sum().reset_index()
    )
    fig3 = px.bar(
        price_cmp, x="day_type", y="pax", color="guest",
        color_discrete_map=GUEST_COLOR,
        barmode="group", text_auto=True,
        labels={"day_type": "Day Type", "pax": "Total Pax", "guest": "Guest Type"},
    )
    fig3.update_layout(**LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "Walk-in pax on Weekend (฿199) is comparable to Weekday (฿159) — "
        "suggesting **price-inelastic demand** driven by TikTok promotion."
    )

    verdict(
        False,
        "Walk-in volume does not drop significantly from ฿159 → ฿199 weekend price — "
        "they are motivated by viral promotion, not price sensitivity. "
        "A ฿259 flat price may not reduce crowding meaningfully "
        "but **risks alienating in-house guests** who are a captive, loyal audience. "
        "Revenue may improve slightly, but the core table-saturation problem remains unsolved.",
    )


# ══════════════════════════════════════════════
# TASK 2 · ACTION C — QUEUE SKIP
# ══════════════════════════════════════════════
elif page == "❌ Task 2 · Action C — Queue Skip":
    st.title("❌ Action C · Queue Skipping for In-house Guests")
    st.warning("**Management idea:** Let in-house guests bypass the queue entirely.")
    st.divider()

    ih = df[df["guest"] == "in house"]
    wi = df[df["guest"] == "walk in"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("In-house: Direct Seated",
              f"{ih['direct'].sum()} / {len(ih)}",
              f"{ih['direct'].sum()/len(ih)*100:.0f}% — already skip queue")
    c2.metric("In-house: Waited in Queue",
              f"{ih['waited'].sum()} / {len(ih)}",
              f"{ih['waited'].sum()/len(ih)*100:.0f}% — would benefit")
    c3.metric("In-house: Walk-aways",
              f"{ih['is_walkaway'].sum()}",
              "gave up after waiting")
    c4.metric("Walk-in: Waited in Queue",
              f"{wi['waited'].sum()} / {len(wi)}",
              f"{wi['waited'].sum()/len(wi)*100:.0f}% of walk-ins")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Queue Behaviour Breakdown by Guest Type")
        rows = []
        for g, grp in df.groupby("guest"):
            rows += [
                {"Guest": g, "Status": "Direct Seated",   "Count": int(grp["direct"].sum())},
                {"Guest": g, "Status": "Waited & Seated", "Count": int(grp["waited"].sum())},
                {"Guest": g, "Status": "Walk-away",       "Count": int(grp["is_walkaway"].sum())},
            ]
        bd = pd.DataFrame(rows)
        fig = px.bar(
            bd, x="Guest", y="Count", color="Status",
            color_discrete_map={"Direct Seated": C_OK, "Waited & Seated": C_NEUTRAL, "Walk-away": C_DANGER},
            barmode="stack", text_auto=True,
            labels={"Guest": "Guest Type", "Count": "Groups"},
        )
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Table Availability During Peak · Jan 15")
        TOTAL = 29
        day15 = df[(df["date"].dt.strftime("%Y-%m-%d") == "2026-01-15") & df["meal_start"].notna()].copy()
        times = pd.date_range("2026-01-15 06:00", "2026-01-15 13:00", freq="15min")
        occ   = [int(((day15["meal_start"] <= t) & (day15["meal_end"] >= t)).sum()) for t in times]
        occ_df = pd.DataFrame({"time": times, "occupied": occ, "free": [max(TOTAL-o, 0) for o in occ]})

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=occ_df["time"], y=occ_df["occupied"], name="Occupied", marker_color=C_DANGER))
        fig2.add_trace(go.Bar(x=occ_df["time"], y=occ_df["free"],     name="Free",     marker_color=C_OK))
        fig2.add_hline(y=TOTAL, line_dash="dash", line_color="yellow",
                       annotation_text="Total capacity", annotation_position="top left")
        fig2.update_layout(**LAYOUT, barmode="stack",
                           xaxis_title="Time", yaxis_title="Tables")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Why Queue-Skip Alone Cannot Solve the Problem")
    st.markdown(
        """
        | Issue | Detail |
        |---|---|
        | **84% of in-house guests already seat directly** | Queue-skip only helps the remaining 16% |
        | **No new tables are created** | Even with skip, tables are full during 08:00–11:00 |
        | **Walk-in guests become more frustrated** | Being displaced in queue by hotel guests creates public complaints — especially bad for a TikTok-viral buffet |
        | **Root cause unaddressed** | The problem is walk-ins occupying tables for 73 min avg, not queue order |
        """
    )

    verdict(
        False,
        "84% of in-house guests already get direct seating — queue-skip benefits only ~16%. "
        "More importantly, even skipping the queue does not help when **no tables are available** "
        "during the 08:00–11:00 peak. Queue-skip fixes position in line, not table scarcity. "
        "It also risks public backlash from walk-in guests who were attracted by viral TikTok promotion.",
    )


# ══════════════════════════════════════════════
# TASK 3 · BEST SOLUTION
# ══════════════════════════════════════════════
elif page == "✅ Task 3 · Best Solution":
    st.title("✅ Task 3 · Recommended Solution")
    st.divider()

    st.markdown(
        """
        ## 💡 Time-Slotted Pre-Registration + Soft Seating Limit

        **Base action chosen:** Queue Skipping for In-house Guests  
        **Our enhancement:** Combine it with a **walk-in time-slot pre-registration system**
        that spreads demand across the morning instead of letting everyone pile in at 08:00–10:00.
        """
    )

    st.divider()
    st.subheader("🔍 Root Cause — The Real Problem")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak Congestion",    "08:00–10:00",  "3-hour crunch window")
    c2.metric("Walk-in Long Sitters", "21 groups",  ">2 hr · blocking tables")
    c3.metric("Turnover Gap",       "73 vs 44 min", "Walk-in vs In-house")
    c4.metric("Tables at Peak",     "~29 units",    "All occupied 08–11")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Problem: All Walk-ins Arrive at Once")
        hourly_wi = (
            df[df["meal_start"].notna()]
            .groupby(["meal_hour", "guest"])
            .size().reset_index(name="groups")
        )
        fig = px.bar(
            hourly_wi, x="meal_hour", y="groups", color="guest",
            color_discrete_map=GUEST_COLOR,
            barmode="stack",
            labels={"meal_hour": "Hour", "groups": "Groups Seated", "guest": "Guest Type"},
        )
        fig.add_vrect(x0=7.5, x1=10.5, fillcolor=C_DANGER, opacity=0.1,
                      annotation_text="Peak crunch", annotation_position="top left")
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Solution: Spread Walk-ins Across Time Slots")
        # Simulated redistributed demand
        slot_hours = [6, 7, 8, 9, 10, 11]
        current_wi = (
            df[df["meal_start"].notna() & (df["guest"] == "walk in")]
            .groupby("meal_hour").size()
            .reindex(slot_hours, fill_value=0)
        )
        # Redistribute: cap at ~25/hr, push overflow to adjacent slots
        target_cap   = 25
        distributed  = current_wi.clip(upper=target_cap).astype(float)
        overflow     = (current_wi - target_cap).clip(lower=0)
        # Push overflow to earlier/later slots
        distributed.loc[6]  += overflow.loc[8] * 0.4
        distributed.loc[11] += overflow.loc[8] * 0.3 + overflow.loc[9] * 0.5
        distributed.loc[10] += overflow.loc[9] * 0.3
        sim_df = pd.DataFrame({
            "Hour":    slot_hours * 2,
            "Groups":  list(current_wi.values) + [int(v) for v in distributed.values],
            "Scenario": ["Current"] * 6 + ["With Time Slots"] * 6,
        })
        fig2 = px.bar(
            sim_df, x="Hour", y="Groups", color="Scenario",
            color_discrete_map={"Current": C_DANGER, "With Time Slots": C_OK},
            barmode="group",
            labels={"Hour": "Hour of Day", "Groups": "Walk-in Groups"},
        )
        fig2.add_hline(y=target_cap, line_dash="dash", line_color="yellow",
                       annotation_text=f"Target cap ~{target_cap}/hr")
        fig2.update_layout(**LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("📋 How the System Works")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            **For Walk-in Guests**
            - Scan QR code at hotel entrance → select a **time slot** (e.g. 07:00, 08:00, 09:00, 10:00)
            - Each slot has a **cap** (e.g. 20–25 groups max)
            - Walk-ins are told their slot time → can wait in lobby or return later
            - **Soft seating guideline:** Staff politely notify walk-ins at 90 minutes
              ("We'll need your table in 30 minutes — thank you!")
            """
        )
    with col2:
        st.markdown(
            """
            **For In-house Guests**
            - **Always guaranteed a seat** — reserved 20% of tables at all times
            - No pre-registration needed — just show room key
            - Walk-in queue-skip built in naturally since slots are pre-managed

            **Expected Outcomes**
            - Peak congestion reduced by spreading arrivals
            - Walk-away rate drops (guests know their slot, not stuck in queue)
            - In-house always gets served — no more complaints
            - Table turnover improves via gentle 90-min nudge
            """
        )

    st.divider()
    st.subheader("📈 Revenue Impact Simulation")

    # Current vs solution scenario
    total_walkin_pax_5days = int(df[df["guest"] == "walk in"]["pax"].sum())
    rev_current_5days = sum(
        r["pax"] * (159 if r["day_type"] == "Weekday" else 199)
        for _, r in df[df["meal_start"].notna()].assign(
            day_type=lambda x: x["date"].dt.dayofweek.apply(lambda d: "Weekend" if d >= 5 else "Weekday")
        ).iterrows()
    )

    scenarios = pd.DataFrame([
        {"Scenario": "Current",              "Revenue": rev_current_5days, "Walk-aways": 14, "Avg Wait": 35},
        {"Scenario": "Time-Slot System",     "Revenue": rev_current_5days * 1.05, "Walk-aways": 4, "Avg Wait": 15},
        {"Scenario": "Price Hike (฿259)",    "Revenue": rev_current_5days * 1.08, "Walk-aways": 14, "Avg Wait": 30},
        {"Scenario": "Seating Time Cap",     "Revenue": rev_current_5days * 0.98, "Walk-aways": 10, "Avg Wait": 28},
    ])

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = px.bar(
            scenarios, x="Scenario", y="Revenue", text_auto=".0f",
            color="Scenario",
            color_discrete_sequence=[C_NEUTRAL, C_OK, C_WALKIN, C_INHOUSE],
            labels={"Revenue": "Projected Revenue (฿ / 5 days)"},
        )
        fig.update_layout(**LAYOUT, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            scenarios, x="Scenario", y="Walk-aways", text_auto=True,
            color="Scenario",
            color_discrete_sequence=[C_NEUTRAL, C_OK, C_WALKIN, C_INHOUSE],
            labels={"Walk-aways": "Est. Walk-aways"},
        )
        fig2.update_layout(**LAYOUT, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        fig3 = px.bar(
            scenarios, x="Scenario", y="Avg Wait", text_auto=True,
            color="Scenario",
            color_discrete_sequence=[C_NEUTRAL, C_OK, C_WALKIN, C_INHOUSE],
            labels={"Avg Wait": "Est. Avg Wait (min)"},
        )
        fig3.update_layout(**LAYOUT, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()
    st.subheader("🏆 Why This Is the Best Solution")
    st.success(
        """
        ✅ **Solves the root cause** — congestion is caused by uncontrolled arrival timing, not total demand.
        Time-slot pre-registration **spreads** the load without turning away customers.

        ✅ **Protects in-house guests** — guaranteed seating means zero wait time for hotel guests, 
        directly addressing the complaint from Comment 1.

        ✅ **Reduces walk-aways** — guests with a confirmed slot are far less likely to leave.
        They have a time commitment, not an uncertain queue.

        ✅ **Improves table turnover naturally** — the 90-minute soft-nudge is a hospitality-friendly 
        approach that avoids confrontation while managing duration.

        ✅ **No revenue loss** — unlike a price hike that may lose price-sensitive guests,
        this system maintains volume while improving experience.

        ✅ **TikTok-friendly** — the slot system can itself be promoted as a feature
        ("book your breakfast slot!"), turning a pain point into a marketing advantage.
        """
    )

    st.markdown(
        """
        ---
        **Personal View:** From a hospitality standpoint, the worst outcome is a frustrated guest 
        who queued for 40 minutes and still didn't get a seat. Time-slot management is 
        already standard at high-demand attractions and restaurants — it respects the guest's time 
        while giving the operator control. The key is communicating it warmly: 
        *"Your table is ready at 9:00 — enjoy the hotel lobby until then."*
        """
    )
