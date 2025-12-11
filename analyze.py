# analyze.py — 전문가용 위험 분석 (로컬 계산만 사용)
import math
import io
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.caption("조회탭에서 선택한 조건 표본과 입력값을 기반으로 심층 위험분석을 제공합니다.")

# =========================
# 0) 입력/상태 확인
# =========================
df: pd.DataFrame = st.session_state.get("filtered")
내부식률 = st.session_state.get("내부식률")
설계두께 = st.session_state.get("설계두께")
측정두께 = st.session_state.get("측정두께")
사용연수_내탱크 = st.session_state.get("사용연수_내탱크")

if df is None or len(df) == 0:
    st.warning("조회탭에서 조건을 먼저 선택하세요.")
    st.stop()

ALLOWABLE = 3.2

df_valid = df["부식률"].astype(float).dropna()
mean_r = df_valid.mean()
p50 = df_valid.quantile(0.50)
p75 = df_valid.quantile(0.75)
p90 = df_valid.quantile(0.90)

# 너무 낮은 값 방지
mean_r = max(mean_r, 0.0005)
p75 = max(p75, 0.0005)
p90 = max(p90, 0.0005)

# =========================
# 1) 위험등급 평가 (Risk Index)
# =========================

def compute_risk_index(my_rate, my_thk, years):
    if pd.isna(my_rate) or pd.isna(my_thk):
        return None, None

    # 부식률 점수 (높을수록 위험)
    rate_score = min(my_rate / mean_r * 50, 50)

    # 두께 여유 점수
    margin = my_thk - ALLOWABLE
    if margin <= 0:
        thk_score = 50
    else:
        thk_score = max(0, 50 - margin * 10)  # 여유가 5mm 이상이면 0점

    # 누적 사용연수 점수
    age_score = min(years * 1.5, 30)

    risk_index = rate_score + thk_score + age_score
    risk_index = min(risk_index, 100)

    # 등급
    if risk_index < 30:
        grade = "A (안전)"
    elif risk_index < 55:
        grade = "B (주의)"
    elif risk_index < 80:
        grade = "C (경계)"
    else:
        grade = "D (위험)"

    return risk_index, grade

st.markdown("## 📌 위험등급 평가 (Risk Index)")
risk, grade = compute_risk_index(내부식률, 측정두께, 사용연수_내탱크)

col1, col2 = st.columns(2)
with col1:
    st.metric("Risk Index", f"{risk:.1f}" if risk else "-")
with col2:
    st.metric("위험등급", grade if grade else "-")

st.markdown("---")

# =========================
# 2) 향후 20년 예측 그래프
# =========================
st.markdown("## 📈 향후 20년 두께 예측 (평균·보수·매우보수)")

years = np.array([0, 5, 10, 20])

def predict_thk(rate):
    return 측정두께 - rate * years

pred_mean = predict_thk(mean_r)
pred_care = predict_thk(p75)
pred_vcare = predict_thk(p90)

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=pred_mean, mode='lines+markers', name='평균 시나리오'))
fig.add_trace(go.Scatter(x=years, y=pred_care, mode='lines+markers', name='보수(P75)'))
fig.add_trace(go.Scatter(x=years, y=pred_vcare, mode='lines+markers', name='매우보수(P90)'))

fig.add_hline(y=ALLOWABLE, line_dash='dot', annotation_text="허용두께 3.2mm")

fig.update_layout(
    template="plotly_white",
    xaxis_title="향후 경과년수",
    yaxis_title="예상 두께(mm)"
)

st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# =========================
# 3) Monte Carlo 기반 위험 확률 분석
# =========================
st.markdown("## 🎲 Monte Carlo 시뮬레이션 (10,000회)")

N = 10000
sim_rates = np.random.normal(mean_r, df_valid.std(), N)
sim_rates = np.clip(sim_rates, 0.0005, None)

fail_years = (측정두께 - ALLOWABLE) / sim_rates

fail_prob_5y = np.mean(fail_years < 5) * 100
fail_prob_10y = np.mean(fail_years < 10) * 100

colA, colB = st.columns(2)
with colA:
    st.metric("📉 5년 내 불합격 확률", f"{fail_prob_5y:.1f}%")
with colB:
    st.metric("📉 10년 내 불합격 확률", f"{fail_prob_10y:.1f}%")

st.markdown("---")

# =========================
# 4) 자동 액션 플래너
# =========================
st.markdown("## 🛠 자동 액션 플래너")

actions = []

if risk >= 80:
    actions.append("⚠️ 즉시 상세검사 또는 단기 재측정 필요 (고위험)")
elif risk >= 55:
    actions.append("⚠️ 1년 이내 재측정 권고 (중위험)")
elif risk >= 30:
    actions.append("📌 2~3년 주기 점검을 유지 (주의군)")
else:
    actions.append("✅ 현행 유지 가능 (저위험)")

# 두께 여유 기반
if 측정두께 - ALLOWABLE <= 1:
    actions.append("⚠️ 두께 여유 1mm 이하 → 보수/코팅 검토")

# Monte Carlo 분석 기반
if fail_prob_10y > 50:
    actions.append("⚠️ 10년 내 불합격 가능성 높음 → 정밀점검 간격 단축 권고")

if fail_prob_5y > 20:
    actions.append("⚠️ 5년 내 불합격 가능성 있음 → 중기 검사 계획 필요")

if len(actions) == 0:
    actions.append("정상 범위입니다.")

for a in actions:
    st.write("- " + a)

st.markdown("---")
