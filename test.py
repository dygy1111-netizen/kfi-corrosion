import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# 데이터 불러오기
# -----------------------------
df = pd.read_excel("data.xlsx", sheet_name="Sheet1", engine="openpyxl")
if "사용연수.1" in df.columns:
    df = df.drop(columns=["사용연수.1"])

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(page_title="위험물탱크 부식률 조회", layout="wide")
st.title("⚡ 위험물탱크 평균 부식률 조회 시스템")
st.markdown("---")

# =============================
# ① 조건별 조회 + ② 내 탱크 데이터 입력
# =============================
col1, col2 = st.columns(2)

with col1:
    st.subheader("① 조건별 조회")
    재질 = st.selectbox("재질", sorted(df["재질"].unique()))
    품명 = st.selectbox("품명", sorted(df["품명"].unique()))
    탱크형상 = st.selectbox("탱크형상", sorted(df["탱크형상"].unique()))
    전기방식 = st.selectbox("전기방식", ["O", "X"], index=1)
    히팅코일 = st.selectbox("히팅코일", ["O", "X"], index=1)
    지역 = st.selectbox("지역", sorted(df["지역"].unique()))

    cond = (
        (df["재질"] == 재질) & (df["품명"] == 품명) &
        (df["탱크형상"] == 탱크형상) & (df["전기방식"] == 전기방식) &
        (df["히팅코일"] == 히팅코일) & (df["지역"] == 지역)
    )
    filtered = df[cond]

with col2:
    st.subheader("② 내 탱크 데이터 입력")
    c1, c2, c3 = st.columns(3)
    with c1:
        설계두께 = st.number_input("설계두께(mm)", min_value=0.0, format="%.2f")
    with c2:
        측정두께 = st.number_input("측정두께(mm)", min_value=0.0, format="%.2f")
    with c3:
        사용연수 = st.number_input("사용연수(년)", min_value=0.0, value=10.0)
    내부식률 = None
    if 설계두께 > 0 and 측정두께 > 0 and 사용연수 > 0:
        내부식률 = (설계두께 - 측정두께) / 사용연수
        st.info(f"🧮 내 탱크 부식률: **{내부식률:.5f} mm/년**")

st.markdown("---")

# =============================
# ③ 향후 부식 예측 및 기대수명 (단독 블록)
# =============================
st.subheader("③ 향후 부식 예측 및 기대수명")

if 설계두께 > 0 and 측정두께 > 0 and 사용연수 > 0:
    bins = [0, 10, 20, 30, 200]
    labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    df["연수구간"] = pd.cut(df["사용연수"], bins=bins, labels=labels, right=False)
    내연수_라벨 = pd.cut([사용연수], bins=bins, labels=labels, right=False)[0]

    cond_pred = (
        (df["재질"] == 재질) & (df["품명"] == 품명) &
        (df["탱크형상"] == 탱크형상) & (df["전기방식"] == 전기방식) &
        (df["히팅코일"] == 히팅코일) & (df["지역"] == 지역) &
        (df["연수구간"] == 내연수_라벨)
    )
    filtered_pred = df[cond_pred]

    if len(filtered_pred) >= 10:
        평균부식률 = filtered_pred["부식률"].mean()
        표본수 = len(filtered_pred)
    else:
        평균부식률 = df["부식률"].mean()
        표본수 = len(filtered_pred)
        st.warning(f"⚠️ 표본이 {표본수}개로 적어 전체 평균 사용")

    # 🔹 입력란 (49%, 49%)
    c1, c2 = st.columns([0.49, 0.49])
    with c1:
        산정방식 = st.selectbox("부식률 산정 방식", ["평균", "중위수(P50)", "상위 75%", "상위 90%"])
    with c2:
        남은기간 = st.number_input("다음 검사까지 남은 기간(년)", value=3.0, step=0.5)

    if 산정방식 == "평균":
        대표부식률 = 평균부식률
    elif 산정방식 == "중위수(P50)":
        대표부식률 = filtered_pred["부식률"].median() if len(filtered_pred) > 0 else 평균부식률
    elif 산정방식 == "상위 75%":
        대표부식률 = filtered_pred["부식률"].quantile(0.75) if len(filtered_pred) > 0 else 평균부식률
    else:
        대표부식률 = filtered_pred["부식률"].quantile(0.9) if len(filtered_pred) > 0 else 평균부식률

    대표부식률 = max(대표부식률, 0.0005)
    예상부식량 = 대표부식률 * 남은기간
    예상두께 = 측정두께 - 예상부식량
    기대수명 = (측정두께 - 3.2) / 대표부식률 if 대표부식률 > 0 else 0

    if 기대수명 > 100:
        기대수명_text = "100년 초과 (표시 생략)"
    elif 기대수명 > 0:
        기대수명_text = f"{기대수명:.1f} 년 남음"
    else:
        기대수명_text = "3.2mm 이하 상태 가능"

    # 🔹 판정
    if 예상두께 >= 3.2:
        판정 = "✅ 적합(합격)"
        색 = "#065f46"
        글자색 = "#d1fae5"
    else:
        판정 = "⚠️ 부적합(불합격)"
        색 = "#7f1d1d"
        글자색 = "#fee2e2"

    # 🔹 표 스타일 (모바일 대응)
    st.markdown(f"""
        <style>
        .tbl {{width:98%;border-collapse:collapse;margin-top:10px;font-size:0.9rem;}}
        .tbl th {{background:#1f2937;color:white;text-align:left;padding:8px;}}
        .tbl td {{background:#111827;color:#e5e7eb;padding:8px;border-bottom:1px solid #333;}}
        .tbl tr:nth-child(even) td{{background:#0b1220;}}
        .tbl .result{{background-color:{색};color:{글자색};font-weight:bold;}}
        @media (max-width:768px){{.tbl{{width:100%;font-size:0.85rem;}}}}
        </style>
        <table class="tbl">
            <tr><th>항목</th><th>값</th></tr>
            <tr><td>사용연수 구간</td><td>{내연수_라벨}</td></tr>
            <tr><td>표본수</td><td>{표본수}</td></tr>
            <tr><td>부식률 산정 방식</td><td>{산정방식}</td></tr>
            <tr><td>대표 부식률</td><td>{대표부식률:.5f} mm/년</td></tr>
            <tr><td>남은 기간</td><td>{남은기간:.1f} 년</td></tr>
            <tr><td>예상 두께 ({남은기간:.1f}년 후)</td><td>{예상두께:.3f} mm</td></tr>
            <tr class="result"><td>판정 결과</td><td>{판정}</td></tr>
            <tr><td>예상 잔여 수명</td><td>{기대수명_text}</td></tr>
        </table>
    """, unsafe_allow_html=True)

st.markdown("---")

# =============================
# ④ 조건에 맞는 표본 수 및 연수구간별 부식률표
# =============================
st.subheader("④ 조건에 맞는 표본 수 및 연수구간별 부식률표")
if len(filtered) > 0:
    bins = [0, 10, 20, 30, 200]
    labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    filtered["연수구간"] = pd.cut(filtered["사용연수"], bins=bins, labels=labels, right=False)
    grouped = filtered.groupby("연수구간").agg(
        평균부식률=("부식률", "mean"),
        표본수=("부식률", "count")
    ).reset_index()
    st.dataframe(grouped, use_container_width=True, height=200)

st.markdown("---")

# =============================
# ⑤ 그래프 비교
# =============================
st.subheader("⑤ 그래프 비교")
if len(filtered) >= 10:
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.bar(grouped, x="연수구간", y="평균부식률",
                      color="평균부식률", text="평균부식률",
                      color_continuous_scale=px.colors.sequential.Viridis,
                      title="연수구간별 평균 부식률", template="plotly_white")
        fig1.update_traces(texttemplate="%{text:.4f}")
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        if 내부식률 is not None:
            fig2 = px.histogram(filtered, x="부식률", nbins=20, title="내 탱크 위치")
            fig2.add_vline(x=내부식률, line_color="red", line_dash="dash")
            st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# =============================
# ⑥ 전체 데이터 요약
# =============================
st.subheader("⑥ 전체 데이터 요약")

mat_avg = df.groupby("재질").agg(평균부식률=("부식률", "mean"), 표본수=("부식률", "count")).reset_index()
mat_avg = mat_avg[mat_avg["표본수"] >= 300].sort_values("평균부식률")
year_avg = df.groupby("연수구간")["부식률"].mean().reset_index()
region_avg = df.groupby("지역")["부식률"].mean().reset_index().sort_values("부식률")

colx, coly, colz = st.columns(3)
with colx:
    st.dataframe(mat_avg, use_container_width=True, height=200)
    fig3 = px.bar(mat_avg, x="재질", y="평균부식률", color="평균부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="재질별 평균 부식률 (표본≥300)", template="plotly_white")
    st.plotly_chart(fig3, use_container_width=True)

with coly:
    st.dataframe(year_avg, use_container_width=True, height=200)
    fig4 = px.bar(year_avg, x="연수구간", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="연수구간별 평균 부식률", template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

with colz:
    st.dataframe(region_avg, use_container_width=True, height=200)
    fig5 = px.bar(region_avg, x="지역", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="지역별 평균 부식률", template="plotly_white")
    st.plotly_chart(fig5, use_container_width=True)
