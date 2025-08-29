#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="US Population Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("default")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

/* 👇 KPI 카드( st.metric )을 하얀 배경으로 변경 */
[data-testid="stMetric"] {
    background-color: #ffffff !important;
    color: #000000 !important;
    text-align: center;
    padding: 15px 0;
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
  color: #000000 !important;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)
#######################
# Load data
df_reshaped = pd.read_csv('(개인데이터분석 파일)서울시 지하철 호선별 역별 시간대별 승하차 인원 정보.csv', encoding = "cp949") ## 분석 데이터 넣기
#######################
# Sidebar
with st.sidebar:
    # --- Title ---
    st.title("서울시 지하철 이용 분석")
    st.caption("사이드바 필터 변경 시 본문 차트가 동기 갱신됩니다.")

    # --- Helpers ---
    import re

    cols = list(df_reshaped.columns)

    def get_time_slots():
        # 예: "07시-08시 승차인원" -> "07시-08시"
        time_cols = [c for c in cols if ("시-" in c and ("승차인원" in c or "하차인원" in c))]
        slots = sorted({re.findall(r"(\d{2}시-\d{2}시)", c)[0] for c in time_cols})
        return slots

    time_slots = get_time_slots()

    # --- Filters: Month / Line / Station ---
    # 사용월
    if "사용월" in cols:
        month_options = sorted(df_reshaped["사용월"].astype(str).unique())
        sel_month = st.selectbox("사용월", month_options, index=len(month_options) - 1)
    else:
        sel_month = None
        st.warning("데이터에 '사용월' 컬럼이 없습니다.")

    # 호선명
    if "호선명" in cols:
        line_options = sorted(df_reshaped["호선명"].astype(str).unique())
        sel_lines = st.multiselect("호선명", options=line_options, default=line_options[:1])
    else:
        sel_lines = []
        st.warning("데이터에 '호선명' 컬럼이 없습니다.")

    # 지하철역 (선택된 호선에 따라 종속)
    if "지하철역" in cols:
        if sel_lines:
            station_options = sorted(
                df_reshaped[df_reshaped["호선명"].astype(str).isin(sel_lines)]["지하철역"].astype(str).unique()
            )
        else:
            station_options = sorted(df_reshaped["지하철역"].astype(str).unique())
        sel_stations = st.multiselect("지하철역", options=station_options, placeholder="역을 선택하지 않으면 전체")
    else:
        sel_stations = []
        st.warning("데이터에 '지하철역' 컬럼이 없습니다.")

    st.divider()

    # --- Metric & Time controls ---
    metric = st.radio("지표", ["승차", "하차", "합계"], horizontal=True)
    if time_slots:
        start_slot, end_slot = st.select_slider(
            "시간대 범위",
            options=time_slots,
            value=(time_slots[0], time_slots[-1]),
        )
        # 선택된 구간에 포함되는 모든 슬롯 구하기
        start_idx, end_idx = time_slots.index(start_slot), time_slots.index(end_slot)
        selected_slots = time_slots[start_idx : end_idx + 1]
    else:
        selected_slots = []
        st.warning("시간대 컬럼(예: '07시-08시 승차인원')을 찾지 못했습니다.")

    st.divider()

    # --- View / Theme / Ranking ---
    view_mode = st.radio("표시 형태", ["히트맵", "테이블"], horizontal=True)
    top_n = st.slider("Top N (랭킹)", 5, 30, 10)
    theme = st.selectbox("테마", ["Dark/Blue", "Light"])

    # --- Apply filters & share state ---
    df_f = df_reshaped.copy()
    if sel_month is not None and "사용월" in cols:
        df_f = df_f[df_f["사용월"].astype(str) == str(sel_month)]
    if sel_lines and "호선명" in cols:
        df_f = df_f[df_f["호선명"].astype(str).isin(sel_lines)]
    if sel_stations and "지하철역" in cols:
        df_f = df_f[df_f["지하철역"].astype(str).isin(sel_stations)]

    # 시간대에 해당하는 실제 컬럼 이름 결정
    def resolve_time_columns(slots, which):
        # which: "승차" | "하차" | "합계"
        ride_cols = [f"{s} 승차인원" for s in slots if f"{s} 승차인원" in cols]
        alight_cols = [f"{s} 하차인원" for s in slots if f"{s} 하차인원" in cols]
        if which == "승차":
            return ride_cols
        if which == "하차":
            return alight_cols
        return ride_cols + alight_cols  # 합계는 이후 계산 시 두 집합을 사용

    selected_time_cols = resolve_time_columns(selected_slots, metric)

    # 전역 상태로 공유 (본문 차트에서 사용)
    st.session_state["filters"] = {
        "month": sel_month,
        "lines": sel_lines,
        "stations": sel_stations,
        "metric": metric,
        "time_slots": selected_slots,
        "view_mode": view_mode,
        "top_n": top_n,
        "theme": theme,
    }
    st.session_state["df_filtered"] = df_f
    st.session_state["selected_time_cols"] = selected_time_cols


#######################
# Plots

#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]:
    st.subheader("📊 요약 지표")

    df_f = st.session_state.get("df_filtered", pd.DataFrame())
    time_cols = st.session_state.get("selected_time_cols", [])
    metric = st.session_state["filters"]["metric"]

    if not df_f.empty and time_cols:
        # --- KPI 계산 ---
        # 승차/하차 각각 합산
        ride_cols = [c for c in time_cols if "승차인원" in c]
        alight_cols = [c for c in time_cols if "하차인원" in c]

        total_ride = df_f[ride_cols].sum().sum() if ride_cols else 0
        total_alight = df_f[alight_cols].sum().sum() if alight_cols else 0

        if metric == "승차":
            total = total_ride
        elif metric == "하차":
            total = total_alight
        else:
            total = total_ride + total_alight

        # --- KPI 카드 표시 ---
        st.metric("총 이용객 수", f"{int(total):,} 명")

        # --- 도넛 차트 데이터 ---
        pie_data = pd.DataFrame({
            "구분": ["승차", "하차"],
            "인원": [total_ride, total_alight]
        })

        fig = px.pie(
            pie_data,
            names="구분",
            values="인원",
            hole=0.5,
            color="구분",
            color_discrete_map={"승차": "#1f77b4", "하차": "#ff7f0e"}
        )
        fig.update_layout(
            title_text="승차 vs 하차 비율",
            title_x=0.5,
            showlegend=True,
            margin=dict(t=40, b=10, l=10, r=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("좌측 사이드바에서 데이터를 선택하면 지표가 표시됩니다.")


with col[1]:
    st.subheader("🗺️ 노선별/역별 시각화")

    df_f = st.session_state.get("df_filtered", pd.DataFrame())
    time_cols = st.session_state.get("selected_time_cols", [])
    filters = st.session_state.get("filters", {})

    if not df_f.empty and time_cols:
        # --- 집계: 역별 합계 ---
        df_f["선택기간합계"] = df_f[time_cols].sum(axis=1)
        station_summary = (
            df_f.groupby(["호선명", "지하철역"], as_index=False)["선택기간합계"].sum()
            .sort_values("선택기간합계", ascending=False)
        )

        # -----------------------------
        # 1. 노선/역별 막대 차트 (임시 지도 대체)
        # -----------------------------
        fig_bar = px.bar(
            station_summary.head(20),
            x="선택기간합계",
            y="지하철역",
            color="호선명",
            orientation="h",
            title="역별 총 이용객 (Top 20)",
        )
        fig_bar.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # -----------------------------
        # 2. 시간대별 히트맵 or 테이블
        # -----------------------------
        st.markdown("### ⏰ 시간대별 패턴")

        if filters.get("view_mode") == "히트맵":
            # 시간대별 합계 (역별 x 시간대)
            heatmap_df = (
                df_f.groupby("지하철역")[time_cols]
                .sum()
                .reset_index()
            )
            # melt → long form
            heatmap_long = heatmap_df.melt(
                id_vars="지하철역", var_name="시간대", value_name="이용객수"
            )

            fig_heatmap = px.imshow(
                heatmap_df.set_index("지하철역")[time_cols],
                labels=dict(x="시간대", y="지하철역", color="이용객수"),
                aspect="auto",
                title="시간대별 이용객 히트맵"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

        else:  # 테이블 모드
            table_df = (
                df_f.groupby("지하철역")[time_cols]
                .sum()
                .sort_values(time_cols[-1], ascending=False)
                .reset_index()
            )
            st.dataframe(table_df, use_container_width=True)

    else:
        st.info("사이드바에서 필터를 선택하면 시각화가 표시됩니다.")


with col[2]:
    st.subheader("🏆 Top 역 / 노선 & About")

    df_f = st.session_state.get("df_filtered", pd.DataFrame())
    time_cols = st.session_state.get("selected_time_cols", [])
    filters = st.session_state.get("filters", {})
    top_n = int(filters.get("top_n", 10))

    if not df_f.empty and time_cols:
        # 선택 구간 합계 산출
        agg_col = "선택기간합계"
        df_f = df_f.copy()
        df_f[agg_col] = df_f[time_cols].sum(axis=1)

        # ---- TOP 역 랭킹 ----
        if {"지하철역"}.issubset(df_f.columns):
            top_station = (
                df_f.groupby("지하철역", as_index=False)[agg_col]
                .sum()
                .sort_values(agg_col, ascending=False)
            )
            # KPI
            best_row = top_station.iloc[0]
            st.metric("가장 혼잡한 역(선택 기간)", f"{best_row['지하철역']}", f"{int(best_row[agg_col]):,} 명")

            # Bar chart
            fig_top_station = px.bar(
                top_station.head(top_n),
                x=agg_col,
                y="지하철역",
                orientation="h",
                title=f"역별 이용객 Top {min(top_n, len(top_station))}",
                labels={agg_col: "이용객 수", "지하철역": "역명"},
            )
            fig_top_station.update_layout(yaxis=dict(autorange="reversed"),
                                          margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_top_station, use_container_width=True)
        else:
            st.warning("데이터에 '지하철역' 컬럼이 없어 역 랭킹을 표시할 수 없습니다.")

        st.divider()

        # ---- TOP 노선 랭킹 ----
        if {"호선명"}.issubset(df_f.columns):
            top_line = (
                df_f.groupby("호선명", as_index=False)[agg_col]
                .sum()
                .sort_values(agg_col, ascending=False)
            )
            st.metric("가장 혼잡한 노선(선택 기간)", f"{top_line.iloc[0]['호선명']}",
                      f"{int(top_line.iloc[0][agg_col]):,} 명")

            fig_top_line = px.bar(
                top_line,
                x="호선명",
                y=agg_col,
                title="노선별 총 이용객",
                labels={"호선명": "노선", agg_col: "이용객 수"},
            )
            fig_top_line.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_top_line, use_container_width=True)
        else:
            st.warning("데이터에 '호선명' 컬럼이 없어 노선 랭킹을 표시할 수 없습니다.")

    else:
        st.info("사이드바에서 필터를 선택하면 Top 랭킹과 About 정보가 표시됩니다.")

    # ---- About 패널 ----
    with st.expander("ℹ️ About"):
        st.markdown(
            """
            **데이터 출처:** 서울열린데이터광장  
            **설명:** 월별·호선별·역별·시간대별 승하차 인원 자료를 바탕으로
            선택한 기간(시간대)의 합계를 사용해 랭킹과 시각화를 제공합니다.

            **대시보드 사용법**
            - 사이드바에서 `사용월`, `호선명`, `지하철역`, `시간대 범위`, `지표`를 선택하세요.
            - 히트맵/테이블 전환 및 Top N 크기를 조절할 수 있습니다.
            """
        )
        # 업데이트 일자 노출 (있을 때만)
        if "작업일자" in df_reshaped.columns:
            try:
                last_updated = pd.to_datetime(df_reshaped["작업일자"]).max()
                st.caption(f"최근 작업일자: {last_updated.date()}")
            except Exception:
                st.caption(f"최근 작업일자: {df_reshaped['작업일자'].max()}")
