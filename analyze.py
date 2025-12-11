# analyze.py — 전문가용 위험 분석 (KFI 맞춤형)
import math
import io
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.caption("조회탭에서 선택한 조건과 내 탱크 데이터를 기반으로 심층 위험분석을 제공합니다.")

# =========================
# 0) 입력/상태 확인
# =========================
df: pd.DataFrame = st.session_state.get("filtered")
내부식률 = st.session_state.get("내부식률")
측정두께 = st.session_state.get("측정두께")
사용연수_내탱크 = st.session_state.get("사용연수_내탱크")

# 조회탭 조건들
재질 = st.session_state.get("재질")
품명 = st.session_state.get("품명")
탱크형상 = st.session_state.get("탱크형상")
히팅코일 = st.session_state.get("히팅코일")
지역 = st.session_state.get("지역")

if df is None or len(df) == 0:
    st.warning("조회탭에서 조건을 먼저 선택하세요.")
    st.stop()

ALLOWABLE = 3.2  # 허용두께

# 기본 통계
df_valid = df["부식률"].astype(float).dropna()
mean_r = max(df_valid.mean(), 0.0005)
p50 = max(df_valid.quantile(0.50), 0.0005)
p75 = max(df_valid.quantile(0.75), 0.0005)
p90 = max(df_valid.quantile(0.90), 0.0005)

# =========================
# 1) Risk Index 계산
# =========================
def compute_risk_index(my_rate, my_thk, years):
    if pd.isna(my_rate) or pd.isna(my_thk):
        return None, None

    # 절대 위험 (0~40점)
    margin = my_thk - ALLOWABLE
    abs_score = min(40, max(0, (5 - margin)) / 5 * 40)

    # 상대 위험 (0~30점) — 표본 대비 속도
    rel_score = min(30, (my_rate / mean_r) * 15)

    # 미래 위험 (0~30점) — 20년 후 예측
    pred20 = my_thk - my_rate * 20
    if pred20 <= ALLOWABLE:
        fut_score = 30
    else:
        fut_score = max(0, (10 - pred20) * 3)

    total = abs_score + rel_score + fut_score
    total = min(total, 100)

    # 등급 분류
    if total < 30:
        grade = "A (안전)"
    elif total < 55:
        grade = "B (주의)"
    elif total < 80:
        grade = "C (경계)"
    else:
        grade = "D (위험)"

    return total, grade


st.markdown("## 📌 위험등급 평가 (Risk Index)")
risk, grade = compute_risk_index(내부식률, 측정두께, 사용연수_내탱크)

colA, colB = st.columns(2)
with colA:
    st.metric("Risk Index (0~100)", f"{risk:.1f}" if risk else "-")
with colB:
    st.metric("위험등급", grade if grade else "-")

st.markdown("---")

# =========================
# 2) 향후 20년 예측 그래프
# =========================
st.markdown("## 📈 향후 20년 두께 예측 (AVG / P75 / P90)")

years = np.array([0, 5, 10, 20])

def predict(rate):
    return 측정두께 - rate * years

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=predict(p50), name="평균(P50)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=years, y=predict(p75), name="보수(P75)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=years, y=predict(p90), name="매우보수(P90)", mode="lines+markers"))
fig.add_hline(y=ALLOWABLE, line_dash="dot", annotation_text="허용두께 3.2mm")
fig.update_layout(template="plotly_white", xaxis_title="경과년수(년)", yaxis_title="예상두께(mm)")

st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# =========================
# 3) 동일 조건 전기방식 비교
# =========================
st.markdown("## ⚡ 동일 조건 전기방식 효과 분석 (O vs X)")

# 동일조건 필터 (전기방식 제외)
df_same = df.copy()

# 전기방식만 제외한 동일 조건으로 원본 전체 df에서 비교
df_source = st.session_state.get("full_df", None)
if df_source is None:
    # 조회탭에서 전체 df를 session_state["full_df"]로 저장하도록 추가 필요
    st.warning("전체 데이터(df)가 필요합니다. 조회탭에서 full_df 저장 코드를 추가하세요.")
else:
    cond = (
        (df_source["재질"] == 재질) &
        (df_source["품명"] == 품명) &
        (df_source["탱크형상"] == 탱크형상) &
        (df_source["히팅코일"] == 히팅코일) &
        (df_source["지역"] == 지역)
    )
    comp = df_source[cond]

    comp_O = comp[comp["전기방식"] == "O"]["부식률"].astype(float).dropna()
    comp_X = comp[comp["전기방식"] == "X"]["부식률"].astype(float).dropna()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("전기방식 O 평균부식률", f"{comp_O.mean():.5f}" if len(comp_O) else "-")
        st.metric("전기방식 X 평균부식률", f"{comp_X.mean():.5f}" if len(comp_X) else "-")

    with col2:
        if len(comp_O) and len(comp_X):
            diff = (1 - comp_O.mean() / comp_X.mean()) * 100
            st.metric("전기방식 효과", f"{diff:.1f}% 감소 효과")
        else:
            st.info("전기방식 O/X 중 하나의 표본이 부족합니다.")

    if len(comp_O) or len(comp_X):
        fig2 = go.Figure()
        fig2.add_trace(go.Box(y=comp_O, name="전기방식 O"))
        fig2.add_trace(go.Box(y=comp_X, name="전기방식 X"))
        fig2.update_layout(template="plotly_white", yaxis_title="부식률(mm/년)")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

st.caption("※ 본 분석은 통계적 참고자료이며, 최종 안전판정은 관련 법령·기준 및 공인검사 절차에 따릅니다.")
