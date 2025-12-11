# analyze.py — 전문가용 위험 분석 (KFI 맞춤형)
import math
import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =========================
# 0) 입력/상태 확인
# =========================

df = st.session_state.get("filtered")
내부식률 = st.session_state.get("내부식률")
측정두께 = st.session_state.get("측정두께")
사용연수_내탱크 = st.session_state.get("사용연수_내탱크")

재질 = st.session_state.get("재질")
품명 = st.session_state.get("품명")
탱크형상 = st.session_state.get("탱크형상")
히팅코일 = st.session_state.get("히팅코일")
지역 = st.session_state.get("지역")

if df is None:
    st.info("조회 조건을 먼저 선택하세요.")
    st.stop()
if df.empty:
    st.warning("해당 조건의 표본이 없습니다. 조건을 변경해 주세요.")
    st.stop()
if 내부식률 is None or 측정두께 is None:
    st.warning("내 탱크 데이터가 없어 일부 분석을 진행할 수 없습니다.")
    st.stop()

ALLOWABLE = 3.2

# =========================
# 기본 통계
# =========================

df_valid = df["부식률"].astype(float).dropna()
mean_r = max(df_valid.mean(), 0.0005)
p50 = max(df_valid.quantile(0.5), 0.0005)
p75 = max(df_valid.quantile(0.75), 0.0005)
p90 = max(df_valid.quantile(0.90), 0.0005)

# =========================
# 위험등급 계산 함수
# =========================
def compute_risk_index(my_rate, my_thk):
    margin = my_thk - ALLOWABLE
    abs_score = min(40, max(0, (5 - margin)) / 5 * 40)
    rel_score = min(30, (my_rate / mean_r) * 15)

    pred20 = my_thk - my_rate * 20
    fut_score = 30 if pred20 <= ALLOWABLE else max(0, (10 - pred20) * 3)

    total = min(abs_score + rel_score + fut_score, 100)

    if total < 30: grade = ("A (안전)", "#0f9d58")
    elif total < 55: grade = ("B (주의)", "#f4b400")
    elif total < 80: grade = ("C (경계)", "#db4437")
    else: grade = ("D (위험)", "#a50e0e")

    return total, grade


# =========================
# 1) 위험등급 표시 (강조 디자인)
# =========================

risk, (grade_text, grade_color) = compute_risk_index(내부식률, 측정두께)

st.markdown("## 📌 위험등급 평가 (Risk Index)")

risk_col1, risk_col2 = st.columns([1, 1])

with risk_col1:
    st.markdown(f"""
    <div style='padding:15px;border-radius:10px;border:2px solid #333;
                background-color:#222;color:white;text-align:center;'>
        <div style='font-size:22px;font-weight:600;'>Risk Index</div>
        <div style='font-size:40px;font-weight:700;color:#4fc3f7;'>{risk:.1f}</div>
    </div>
    """, unsafe_allow_html=True)

with risk_col2:
    st.markdown(f"""
    <div style='padding:15px;border-radius:10px;border:2px solid {grade_color};
                background-color:{grade_color}22;text-align:center;'>
        <div style='font-size:22px;font-weight:600;'>위험등급</div>
        <div style='font-size:40px;font-weight:800;color:{grade_color};'>{grade_text}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# 1-1) 평가 기준 설명 (2열)
# =========================
st.markdown("### 📝 위험등급 평가 기준 설명")

colL, colR = st.columns(2)

with colL:
    st.markdown("""
#### 1) 절대 위험도 (최대 40점)
- 현재 두께가 허용두께(3.2mm)에 얼마나 근접했는지 평가  
- 여유가 적을수록 점수가 높아짐  

#### 2) 상대 위험도 (최대 30점)
- 동일 조건 표본의 평균부식률 대비 현재 부식률 비교  
- 평균 대비 약 **2배 빠르면 최대점(30점)**  
""")

with colR:
    st.markdown("""
#### 3) 미래 위험도 (최대 30점)
- 향후 **20년 예측 두께** 계산  
- 허용두께 이하로 내려가면 위험 점수 증가  

#### 👉 최종 등급 기준
- **A (0~29점):** 안전  
- **B (30~54점):** 주의  
- **C (55~79점):** 경계  
- **D (80~100점):** 위험  
""")

st.markdown("---")

# =========================
# 2 & 3) 예측 + 전기방식 비교 (한 행)
# =========================

left, right = st.columns(2)

# ------------------------------
# 2) 향후 20년 두께 예측
# ------------------------------
with left:
    st.markdown("## 📈 향후 20년 두께 예측")

    years = np.array([0, 5, 10, 20])

    def predict(rate):
        return 측정두께 - rate * years

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=predict(p50), name="평균(P50)", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=predict(p75), name="보수(P75)", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=predict(p90), name="매우보수(P90)", mode="lines+markers"))
    fig.add_hline(y=ALLOWABLE, line_dash="dot", annotation_text="허용두께 3.2mm")

    fig.update_layout(template="plotly_white",
                      xaxis_title="경과년수(년)", yaxis_title="예상두께(mm)")

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# 3) 전기방식 유무 비교 그래프 (5년 구간 + 스무딩)
# ------------------------------
with right:
    st.markdown("## ⚡ 전기방식설비 유무 비교")

    df_source = st.session_state.get("full_df", None)

    if df_source is None:
        st.warning("전체 데이터(df)를 찾을 수 없습니다. 조회탭에서 먼저 조회를 실행하세요.")
    else:
        # 조회탭과 동일 조건(전기방식만 제외)
        cond = (
            (df_source["재질"] == 재질) &
            (df_source["품명"] == 품명) &
            (df_source["탱크형상"] == 탱크형상) &
            (df_source["히팅코일"] == 히팅코일) &
            (df_source["지역"] == 지역)
        )

        comp = df_source[cond].copy()

        if comp.empty:
            st.info("해당 조건에서 전기방식 O/X 비교 가능한 표본이 없습니다.")
        else:
            # 🔹 5년 단위 사용연수 구간 생성 (0,5,10,15,...)
            comp["사용연수구간"] = (comp["사용연수"] // 5) * 5

            # O / X 각각 5년 구간별 평균 부식률
            comp_O = (
                comp[comp["전기방식"] == "O"]
                .groupby("사용연수구간")["부식률"]
                .mean()
                .reset_index()
                .sort_values("사용연수구간")
            )
            comp_X = (
                comp[comp["전기방식"] == "X"]
                .groupby("사용연수구간")["부식률"]
                .mean()
                .reset_index()
                .sort_values("사용연수구간")
            )

            # 🔹 이동평균(스무딩) 함수
            def smooth(series, window=2):
                return series.rolling(window=window, min_periods=1).mean()

            if len(comp_O):
                comp_O["부식률_smooth"] = smooth(comp_O["부식률"])
            if len(comp_X):
                comp_X["부식률_smooth"] = smooth(comp_X["부식률"])

            # 🔹 그래프 그리기
            fig2 = go.Figure()

            if len(comp_O):
                fig2.add_trace(go.Scatter(
                    x=comp_O["사용연수구간"],
                    y=comp_O["부식률_smooth"],
                    name="전기방식설비 설치",
                    mode="lines+markers",
                    line=dict(color="green", width=3)
                ))

            if len(comp_X):
                fig2.add_trace(go.Scatter(
                    x=comp_X["사용연수구간"],
                    y=comp_X["부식률_smooth"],
                    name="전기방식설비 미설치",
                    mode="lines+markers",
                    line=dict(color="red", width=3)
                ))

            fig2.update_layout(
                template="plotly_white",
                xaxis_title="사용연수",
                yaxis_title="평균 부식률(mm/년)",
                title="전기방식설비 유무에 따른 부식률 경향"
            )

            st.plotly_chart(fig2, use_container_width=True)

            # 🔹 전체 평균 기준 효과 메시지
            if len(comp_O) and len(comp_X):
                diff = (1 - comp_O["부식률"].mean() / comp_X["부식률"].mean()) * 100
                st.success(f"📉 전기방식 설치 시 평균 **{diff:.1f}%** 부식률 감소 효과")
            else:
                st.info("전기방식설비 설치 유무 표본이 부족합니다.")


st.caption("※ 본 분석은 참고자료이며, 최종 안전판정은 관련 법령·기준에 따릅니다.")
