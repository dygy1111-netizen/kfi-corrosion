# analyze.py — 전문가용 위험 분석 (KFI 맞춤형)
import math
import io
import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =========================
# 0) 입력/상태 확인
# =========================

# 조회값들 가져오기
df = st.session_state.get("filtered", None)
내부식률 = st.session_state.get("내부식률", None)
측정두께 = st.session_state.get("측정두께", None)
사용연수_내탱크 = st.session_state.get("사용연수_내탱크", None)

재질 = st.session_state.get("재질", None)
품명 = st.session_state.get("품명", None)
탱크형상 = st.session_state.get("탱크형상", None)
히팅코일 = st.session_state.get("히팅코일", None)
지역 = st.session_state.get("지역", None)

# 🔥 초기 상태: 조회탭에서 아무것도 선택되지 않았을 때
if df is None:
    st.info("조회 조건을 먼저 선택하세요.")
    st.stop()

# 🔥 표본 0개 → 분석 불가 메시지 출력 (UI 유지)
if isinstance(df, pd.DataFrame) and df.empty:
    st.warning("해당 조건의 표본이 없습니다. 조건을 변경해 주세요.")
    st.stop()

# 🔥 내 탱크 입력값이 없을 경우 → 일부 분석 비활성화
if 내부식률 is None or 측정두께 is None:
    st.warning("내 탱크 데이터가 없어 일부 분석을 진행할 수 없습니다.")
    st.stop()

ALLOWABLE = 3.2  # 허용두께

# =========================
# 기본 통계 계산
# =========================
df_valid = df["부식률"].astype(float).dropna()

mean_r = max(df_valid.mean(), 0.0005)
p50 = max(df_valid.quantile(0.50), 0.0005)
p75 = max(df_valid.quantile(0.75), 0.0005)
p90 = max(df_valid.quantile(0.90), 0.0005)

# =========================
# 1) Risk Index 계산
# =========================
def compute_risk_index(my_rate, my_thk, years):

    # 절대 위험 (0~40점)
    margin = my_thk - ALLOWABLE
    abs_score = min(40, max(0, (5 - margin)) / 5 * 40)

    # 상대 위험 (0~30점)
    rel_score = min(30, (my_rate / mean_r) * 15)

    # 미래 위험 (0~30점)
    pred20 = my_thk - my_rate * 20
    fut_score = 30 if pred20 <= ALLOWABLE else max(0, (10 - pred20) * 3)

    total = abs_score + rel_score + fut_score
    total = min(total, 100)

    # 등급
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
    st.metric("Risk Index (0~100)", f"{risk:.1f}")
with colB:
    st.metric("위험등급", grade)
st.markdown("""
### 📝 위험등급 평가 기준 설명

Risk Index(0~100점)는 다음 3가지 요소를 합산하여 계산합니다.

#### 1) 절대 위험도 (최대 40점)
- 현재 두께가 허용두께(3.2mm)에 얼마나 근접했는지를 평가  
- 여유가 적을수록 점수가 높아져 위험 판정

#### 2) 상대 위험도 (최대 30점)
- 동일 조건 표본의 평균부식률 대비 현재 부식률이 얼마나 높은지 평가  
- 평균 대비 2배 빠르면 약 30점 수준

#### 3) 미래 위험도 (최대 30점)
- 향후 20년 후 예상두께를 계산  
- 20년 후 허용두께 이하로 내려가는 경우 위험 점수 증가

#### 👉 최종 등급 기준
- **A (0~29점):** 안전  
- **B (30~54점):** 주의 필요  
- **C (55~79점):** 경계 (추가 관리 필요)  
- **D (80~100점):** 위험 (빠른 조치 필요)

---
""")

st.markdown("---")

# =========================
# 2) 향후 20년 두께 예측 그래프
# =========================
st.markdown("## 📈 향후 20년 두께 예측 (AVG / P75 / P90)")

years = np.array([0, 5, 10, 20])

def predict(rate):
    return 측정두께 - rate * years

fig = go.Figure()
fig.add_trace(go.Scatter(x=years, y=predict(p50), mode="lines+markers", name="평균(P50)"))
fig.add_trace(go.Scatter(x=years, y=predict(p75), mode="lines+markers", name="보수(P75)"))
fig.add_trace(go.Scatter(x=years, y=predict(p90), mode="lines+markers", name="매우보수(P90)"))

fig.add_hline(y=ALLOWABLE, line_dash="dot", annotation_text="허용두께 3.2mm")
fig.update_layout(template="plotly_white", xaxis_title="경과년수(년)", yaxis_title="예상두께(mm)")

st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# =========================
# 3) 동일 조건 전기방식 비교
# =========================
st.markdown("## ⚡ 동일 조건 전기방식 효과 분석 (O vs X)")

df_source = st.session_state.get("full_df", None)

if df_source is None:
    st.warning("전체 데이터(df)가 필요합니다. 조회탭에서 full_df 저장 코드를 추가하세요.")
else:
    # 동일조건 (전기방식 제외)
    cond = (
        (df_source["재질"] == 재질) &
        (df_source["품명"] == 품명) &
        (df_source["탱크형상"] == 탱크형상) &
        (df_source["히팅코일"] == 히팅코일) &
        (df_source["지역"] == 지역)
    )
    
    comp = df_source[cond].copy()
    
    # 사용연수 기반 그룹 평균
    comp_O = comp[comp["전기방식"] == "O"].groupby("사용연수")["부식률"].mean().reset_index()
    comp_X = comp[comp["전기방식"] == "X"].groupby("사용연수")["부식률"].mean().reset_index()

    # 평균 수치 출력
    col1, col2 = st.columns(2)
    with col1:
        st.metric("전기방식 O 전체 평균부식률", f"{comp_O['부식률'].mean():.5f}" if len(comp_O) else "-")
    with col2:
        st.metric("전기방식 X 전체 평균부식률", f"{comp_X['부식률'].mean():.5f}" if len(comp_X) else "-")

    # 꺾은선 그래프
    fig_line = go.Figure()
    
    if len(comp_O):
        fig_line.add_trace(go.Scatter(
            x=comp_O["사용연수"], y=comp_O["부식률"],
            mode="lines+markers",
            name="전기방식 O",
            line=dict(color="green")
        ))
    if len(comp_X):
        fig_line.add_trace(go.Scatter(
            x=comp_X["사용연수"], y=comp_X["부식률"],
            mode="lines+markers",
            name="전기방식 X",
            line=dict(color="red")
        ))

    fig_line.update_layout(
        template="plotly_white",
        xaxis_title="사용연수(년)",
        yaxis_title="평균 부식률(mm/년)",
        title="전기방식 유무에 따른 사용연수별 평균 부식률 비교"
    )

    st.plotly_chart(fig_line, use_container_width=True)

    # 전기방식 효과 계산
    if len(comp_O) and len(comp_X):
        diff = (1 - comp_O["부식률"].mean() / comp_X["부식률"].mean()) * 100
        st.success(f"📉 전기방식 설치 시 평균 **{diff:.1f}%** 부식률 감소 효과")
    else:
        st.info("전기방식 O/X 중 하나의 표본이 부족합니다.")


st.markdown("---")

st.caption("※ 본 분석은 통계적 참고자료이며, 최종 안전판정은 관련 법령·기준 및 공인검사 절차에 따릅니다.")
