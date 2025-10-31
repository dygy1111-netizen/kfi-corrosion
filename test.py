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

# -----------------------------
# ① 조건별 조회
# -----------------------------
st.subheader("① 조건별 조회")

mat_order = df["재질"].value_counts().index.tolist()

재질 = st.selectbox("재질 선택", mat_order)
품명 = st.selectbox("품명 선택", sorted(df["품명"].unique()))
탱크형상 = st.selectbox("탱크형상 선택", sorted(df["탱크형상"].unique()), 
                      index=sorted(df["탱크형상"].unique()).index("고정지붕"))
전기방식 = st.selectbox("전기방식", ["O", "X"], index=1)
히팅코일 = st.selectbox("히팅코일", ["O", "X"], index=1)
지역 = st.selectbox("지역 선택", sorted(df["지역"].unique()), 
                  index=sorted(df["지역"].unique()).index("울산"))

# ✅ 조건 필터 먼저 계산
cond = (
    (df["재질"] == 재질) &
    (df["품명"] == 품명) &
    (df["탱크형상"] == 탱크형상) &
    (df["전기방식"] == 전기방식) &
    (df["히팅코일"] == 히팅코일) &
    (df["지역"] == 지역)
)
filtered = df[cond]

# -----------------------------
# ② 내 탱크 데이터 입력
# -----------------------------
st.subheader("② 내 탱크 데이터 입력")

col1, col2, col3 = st.columns(3)
with col1:
    설계두께 = st.number_input("설계두께(mm)", min_value=0.0, format="%.2f")
with col2:
    측정두께 = st.number_input("측정두께(mm)", min_value=0.0, format="%.2f")
with col3:
    사용연수_내탱크 = st.number_input("내 탱크 사용연수 (년)", min_value=0.0, max_value=100.0, value=10.0)

내부식률 = None
if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:
    내부식률 = (설계두께 - 측정두께) / (사용연수_내탱크)
    st.info(f"🧮 내 탱크 계산된 부식률: **{내부식률:.5f} mm/년**")

st.markdown("---")

# -----------------------------
# ③ 향후 부식 예측 및 기대수명 (표 + 가독성 + 보수적 산정)
# -----------------------------
st.subheader("③ 향후 부식 예측 및 기대수명")

if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:
    # ① 사용연수 → 구간 라벨
    bins = [0, 10, 20, 30, 200]
    labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    내연수_라벨 = pd.cut([사용연수_내탱크], bins=bins, labels=labels, right=False)[0]

    # ② 연수구간 컬럼 생성(없을 때만)
    if "연수구간" not in df.columns:
        df["연수구간"] = pd.cut(df["사용연수"], bins=bins, labels=labels, right=False)

    # ③ 조건 + 연수구간 필터
    cond_base = (
        (df["재질"] == 재질) &
        (df["품명"] == 품명) &
        (df["탱크형상"] == 탱크형상) &
        (df["전기방식"] == 전기방식) &
        (df["히팅코일"] == 히팅코일) &
        (df["지역"] == 지역)
    )
    filtered_pred = df[cond_base & (df["연수구간"] == 내연수_라벨)]
    표본수 = len(filtered_pred)

    # ④ 부식률 산정 방식(보수성 선택) + 하한/상한 설정
    colA, colB, colC = st.columns([1.2, 1, 1])
    with colA:
        산정방식 = st.selectbox("부식률 산정 방식", ["평균", "중위수(P50)", "상위 75% (보수)", "상위 90% (매우 보수)"])
    with colB:
        최소하한 = st.number_input("최소 부식률 하한(mm/년)", min_value=0.0, value=0.001, step=0.001, format="%.3f")
    with colC:
        수명표시상한 = st.number_input("기대수명 표기 상한(년)", min_value=1.0, value=50.0, step=1.0, format="%.0f")

    # 표본 부족 시 전체로 대체
    rates = (filtered_pred["부식률"] if 표본수 >= 10 else df["부식률"]).dropna()
    if 표본수 < 10:
        st.warning(f"⚠️ 같은 연수구간 표본이 {표본수}개로 적어 전체 데이터로 보정하여 계산합니다.")

    # ⑤ 산정방식에 따른 대표값 계산
    if 산정방식 == "평균":
        대표부식률 = rates.mean()
    elif 산정방식 == "중위수(P50)":
        대표부식률 = rates.median()
    elif 산정방식 == "상위 75% (보수)":
        대표부식률 = rates.quantile(0.75)
    else:  # 상위 90%
        대표부식률 = rates.quantile(0.90)

    # 하한 적용(너무 낮으면 보수적 보정)
    대표부식률 = max(대표부식률, 최소하한)

    # ⑥ 남은 기간 입력(상한 없음)
    남은기간 = st.number_input("다음 정밀정기검사까지 남은 기간 (년)", min_value=0.0, value=3.0, step=0.5)

    # ⑦ 예측 계산 (부식률은 mm/년 기준)
    예상부식량 = 대표부식률 * 남은기간
    예상두께 = 측정두께 - 예상부식량

    # 판정
    if 예상두께 >= 3.2:
        판정 = "✅ 적합 (합격)"
        판정색 = "#065f46"   # 짙은 초록(다크테마 가독)
        판정글 = "#d1fae5"
    else:
        판정 = "⚠️ 부적합 (불합격)"
        판정색 = "#7f1d1d"   # 짙은 빨강
        판정글 = "#fee2e2"

    # 기대수명
    if 대표부식률 > 0:
        기대수명_raw = (측정두께 - 3.2) / 대표부식률
        기대수명 = f"≥ {수명표시상한:.0f} 년" if 기대수명_raw > 수명표시상한 else f"{기대수명_raw:.1f} 년"
    else:
        기대수명 = "데이터 부족"

    # ⑧ 결과 표 (다크테마 가독성 강화)
    st.markdown(
        f"""
        <style>
            .tbl-kfi {{
                width: 65%; border-collapse: collapse; margin-top: 10px;
                border: 1px solid #374151; font-size: 0.95rem;
            }}
            .tbl-kfi th {{
                text-align: left; padding: 10px; 
                background-color: #111827; color: #e5e7eb; 
                border-bottom: 2px solid #374151;
            }}
            .tbl-kfi td {{
                padding: 8px; border-bottom: 1px solid #374151; color: #e5e7eb;
            }}
            .tbl-kfi tr:nth-child(even) td {{ background-color: #0b1220; }}
            .result-row {{
                background-color: {판정색};
                color: {판정글};
                font-weight: 600;
            }}
            .muted {{ color: #9ca3af; }}
        </style>
        <table class="tbl-kfi">
            <tr>
                <th>항목</th><th>값</th>
            </tr>
            <tr><td>사용연수 구간</td><td>{내연수_라벨}</td></tr>
            <tr><td>표본수</td><td>{표본수 if 표본수>=10 else f"{표본수} (전체로 보정)"}</td></tr>
            <tr><td>부식률 산정 방식</td><td>{산정방식}</td></tr>
            <tr><td>해당 조건 대표 부식률</td><td>{대표부식률:.5f} mm/년 <span class="muted">(하한 적용: {최소하한:.3f})</span></td></tr>
            <tr><td>다음 정밀정기검사까지 기간</td><td>{남은기간:.1f} 년</td></tr>
            <tr><td>예상 부식량</td><td>{예상부식량:.3f} mm</td></tr>
            <tr><td>예상 두께 ({남은기간:.1f}년 후)</td><td>{예상두께:.3f} mm</td></tr>
            <tr class="result-row"><td>판정 결과</td><td>{판정}</td></tr>
            <tr><td>예상 잔여 수명 (3.2mm 도달)</td><td>{기대수명}</td></tr>
        </table>
        """,
        unsafe_allow_html=True
    )



# -----------------------------
# ④ 조건에 맞는 표본 수 및 연수구간별 부식률표
# -----------------------------
st.subheader("④ 조건에 맞는 표본 수 및 연수구간별 부식률표")

if len(filtered) < 30:
    st.warning(f"⚠️ 표본 수가 {len(filtered)}개로 너무 적습니다. (최소 30개 이상 필요)")
else:
    st.success(f"조건에 맞는 표본 수: {len(filtered)}개")

    bins = [0, 10, 20, 30, 200]
    labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    filtered["연수구간"] = pd.cut(filtered["사용연수"], bins=bins, labels=labels, right=False)

    grouped = filtered.groupby("연수구간").agg(
        평균부식률=("부식률", "mean"),
        표본수=("부식률", "count")
    ).reset_index()

    st.dataframe(grouped, use_container_width=True, height=200)

st.markdown("---")

# -----------------------------
# ⑤ 그래프 비교
# -----------------------------
st.subheader("⑤ 그래프 비교")

col_g1, col_g2 = st.columns(2)

if len(filtered) >= 30:
    with col_g1:
        fig1 = px.bar(
            grouped,
            x="연수구간",
            y="평균부식률",
            text="평균부식률",
            color="평균부식률",
            color_continuous_scale=px.colors.sequential.Viridis,
            title="조건별 사용연수 구간 평균 부식률",
            template="plotly_white"
        )
        ymax = grouped["평균부식률"].max() * 2
        fig1.update_yaxes(range=[0, ymax])
        fig1.update_traces(
            texttemplate="%{text:.4f}<br>(n=%{customdata[0]})",
            textposition="outside",
            customdata=grouped[["표본수"]].values
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_g2:
        if 내부식률 is not None:
            fig2 = px.histogram(
                filtered, x="부식률", nbins=20, color_discrete_sequence=["#ff7f0e"],
                title="같은 조건 표본 분포와 내 탱크 위치", template="plotly_white"
            )
            fig2.add_vline(x=내부식률, line_dash="dash", line_color="red",
                           annotation_text="내 탱크", annotation_position="top left")
            st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# -----------------------------
# ⑥ 전체 데이터 요약
# -----------------------------
st.subheader("⑥ 전체 데이터 요약")

mat_avg = df.groupby("재질").agg(
    평균부식률=("부식률","mean"),
    표본수=("부식률","count")
).reset_index()
mat_avg = mat_avg[mat_avg["표본수"] >= 300].sort_values("평균부식률")

bins_all = [0, 10, 20, 30, 200]
labels_all = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
df["연수구간"] = pd.cut(df["사용연수"], bins=bins_all, labels=labels_all, right=False)

year_avg = df.groupby("연수구간")["부식률"].mean().reset_index()
region_avg = df.groupby("지역")["부식률"].mean().reset_index().sort_values("부식률")

col1, col2, col3 = st.columns(3)

with col1:
    st.dataframe(mat_avg, use_container_width=True, height=200)
    fig3 = px.bar(mat_avg, x="재질", y="평균부식률", color="평균부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="재질별 평균 부식률 (표본≥300)", template="plotly_white")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.dataframe(year_avg, use_container_width=True, height=200)
    fig4 = px.bar(year_avg, x="연수구간", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="사용연수 구간별 평균 부식률", template="plotly_white")
    ymax_all = year_avg["부식률"].max() * 2
    fig4.update_yaxes(range=[0, ymax_all])
    st.plotly_chart(fig4, use_container_width=True)

with col3:
    st.dataframe(region_avg, use_container_width=True, height=200)
    fig5 = px.bar(region_avg, x="지역", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="지역별 평균 부식률", template="plotly_white")
    st.plotly_chart(fig5, use_container_width=True)
