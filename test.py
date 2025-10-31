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
    사용연수_내탱크 = st.number_input("사용연수(년)", min_value=0.1, max_value=100.0, value=10.0, format="%.1f")

# -----------------------------
# 조건 필터링 (사용연수 제외)
# -----------------------------
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
# 내 탱크 부식률 계산 (mm/년)
# -----------------------------
내부식률 = None
if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:
    내부식률 = (설계두께 - 측정두께) / 사용연수_내탱크
    st.info(f"🧮 내 탱크 연평균 부식률: **{내부식률:.4f} mm/년**")
elif 설계두께 > 0 and 측정두께 > 설계두께:
    st.warning("⚠️ 측정두께가 설계두께보다 큽니다. 입력값을 확인하세요.")

st.markdown("---")

# -----------------------------
# ③ 조건에 맞는 표본 수 및 연수구간별 부식률표
# -----------------------------
st.subheader("③ 조건에 맞는 표본 수 및 연수구간별 부식률표")

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
# ④ 그래프 비교 (조건별 평균 vs 내탱크)
# -----------------------------
st.subheader("④ 그래프 비교")

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
        fig1.update_layout(width=650, height=400)
        st.plotly_chart(fig1, use_container_width=False)

    with col_g2:
        if 내부식률 is not None:
            fig2 = px.histogram(
                filtered, x="부식률", nbins=20, color_discrete_sequence=["#ff7f0e"],
                title="같은 조건 표본 분포와 내 탱크 위치", template="plotly_white"
            )
            fig2.add_vline(x=내부식률, line_dash="dash", line_color="red",
                           annotation_text="내 탱크", annotation_position="top left")
            fig2.update_layout(width=650, height=400)
            st.plotly_chart(fig2, use_container_width=False)

st.markdown("---")

# -----------------------------
# ⑤ 전체 데이터 요약 (3개 그래프)
# -----------------------------
st.subheader("⑤ 전체 데이터 요약")

# 재질별 평균
mat_avg = df.groupby("재질").agg(
    평균부식률=("부식률","mean"),
    표본수=("부식률","count")
).reset_index()
mat_avg = mat_avg[mat_avg["표본수"] >= 300].sort_values("평균부식률")

# 연수 구간별 평균
bins_all = [0, 10, 20, 30, 200]
labels_all = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
df["연수구간"] = pd.cut(df["사용연수"], bins=bins_all, labels=labels_all, right=False)
year_avg = df.groupby("연수구간")["부식률"].mean().reset_index()

# 지역별 평균
region_avg = df.groupby("지역")["부식률"].mean().reset_index().sort_values("부식률")

col1, col2, col3 = st.columns(3)

with col1:
    st.dataframe(mat_avg, use_container_width=True, height=200)
    fig3 = px.bar(mat_avg, x="재질", y="평균부식률", color="평균부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="재질별 평균 부식률 (표본≥300)", template="plotly_white")
    fig3.update_layout(width=650, height=400)
    st.plotly_chart(fig3, use_container_width=False)

with col2:
    st.dataframe(year_avg, use_container_width=True, height=200)
    fig4 = px.bar(year_avg, x="연수구간", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="사용연수 구간별 평균 부식률", template="plotly_white")
    ymax_all = year_avg["부식률"].max() * 2
    fig4.update_yaxes(range=[0, ymax_all])
    fig4.update_layout(width=650, height=400)
    st.plotly_chart(fig4, use_container_width=False)

with col3:
    st.dataframe(region_avg, use_container_width=True, height=200)
    fig5 = px.bar(region_avg, x="지역", y="부식률", color="부식률",
                  color_continuous_scale=px.colors.sequential.Viridis,
                  title="지역별 평균 부식률", template="plotly_white")
    fig5.update_layout(width=650, height=400)
    st.plotly_chart(fig5, use_container_width=False)
