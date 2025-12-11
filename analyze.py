# analyze.py — 로컬 통계 기반 결과분석 (OpenAI 미사용)
import math
import io
import streamlit as st
import pandas as pd
import plotly.express as px

st.caption("조회탭에서 선택한 조건 표본과 입력값만으로 통계를 생성합니다.")

# =========================
# 0) 입력/상태 확인
# =========================
df: pd.DataFrame = st.session_state.get("filtered")
내부식률 = st.session_state.get("내부식률")
설계두께 = st.session_state.get("설계두께")
측정두께 = st.session_state.get("측정두께")
사용연수_내탱크 = st.session_state.get("사용연수_내탱크")

if df is None or len(df) == 0:
    st.warning("조회탭에서 조건을 먼저 선택하세요. (조건 표본이 없습니다)")
    st.stop()

# 공통 상수
ALLOWABLE_THK = 3.2  # 판정 기준 두께(mm)
YEAR_BINS = [0, 10, 20, 30, 200]
YEAR_LABELS = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]

# =========================
# 1) 유틸/집계
# =========================
def ensure_year_bins(dfin: pd.DataFrame) -> pd.DataFrame:
    out = dfin.copy()
    if "연수구간" not in out.columns:
        out["연수구간"] = pd.cut(out["사용연수"], bins=YEAR_BINS, labels=YEAR_LABELS, right=False)
    return out

def safe_quantile(s: pd.Series, q: float):
    try:
        return float(s.quantile(q))
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def build_aggregates(df_in: pd.DataFrame):
    d = {}
    s = df_in["부식률"].astype(float)
    d["n"] = int(s.notna().sum())
    d["mean"] = float(s.mean())
    d["std"] = float(s.std(ddof=0)) if d["n"] > 1 else 0.0
    d["min"] = float(s.min())
    d["p10"] = safe_quantile(s, 0.10)
    d["p25"] = safe_quantile(s, 0.25)
    d["p50"] = safe_quantile(s, 0.50)
    d["p75"] = safe_quantile(s, 0.75)
    d["p90"] = safe_quantile(s, 0.90)
    d["max"] = float(s.max())

    dfx = ensure_year_bins(df_in)
    yr = dfx.groupby("연수구간", observed=True)["부식률"].agg(["mean","count"]).reset_index()
    d["연수구간"] = yr

    by_mat = df_in.groupby("재질", observed=True)["부식률"].mean().sort_values().reset_index()
    by_reg = df_in.groupby("지역", observed=True)["부식률"].mean().sort_values().reset_index()
    d["재질_top"] = by_mat.head(5)
    d["재질_bottom"] = by_mat.tail(5)
    d["지역_top"] = by_reg.head(5)
    d["지역_bottom"] = by_reg.tail(5)
    return d

aggr = build_aggregates(df)

# =========================
# 2) 시각 요약
# =========================
left, right = st.columns(2)
with left:
    st.metric("조건 표본 수", aggr["n"])
    fig_h = px.histogram(df, x="부식률", nbins=20, title="조건 표본 부식률 분포", template="plotly_white")
    st.plotly_chart(fig_h, use_container_width=True)
with right:
    st.dataframe(
        aggr["연수구간"].rename(columns={"mean": "평균부식률", "count": "표본수"}),
        use_container_width=True, height=230
    )

# =========================
# 3) 내 탱크 위치/간이 판정
# =========================
def local_position_and_assess(df_in: pd.DataFrame, my_rate: float):
    s = df_in["부식률"].astype(float).dropna().sort_values()
    if pd.isna(my_rate):
        return None, "내부식률(내 탱크)이 없어 비교가 제한됩니다."
    # 백분위 위치
    pct = float((s <= my_rate).sum() / len(s) * 100.0) if len(s) else None

    # 간이 판정(보수성 슬라이더)
    factor = 1.5
    thr = aggr["mean"] * factor if aggr["mean"] is not None else None
    if thr is None:
        msg = "조건 평균 부식률을 계산할 수 없습니다."
    else:
        if my_rate <= thr:
            msg = f"내부식률이 조건 평균의 {factor:.1f}배 이하로, 상대적으로 양호합니다."
        else:
            msg = f"내부식률이 조건 평균 대비 높아(>{factor:.1f}배), 보수적 관리가 권장됩니다."
    return pct, msg

st.markdown("### 🧭 내 탱크 위치(백분위) & 간이 판정")
pct, assess_msg = local_position_and_assess(df, 내부식률)
colp1, colp2 = st.columns([1,3])
with colp1:
    st.metric("내 탱크 위치", f"{pct:.1f} 퍼센타일" if pct is not None else "-")
with colp2:
    st.info(assess_msg)

# 시각적 위치 표시
if not pd.isna(내부식률):
    fig_pos = px.histogram(df, x="부식률", nbins=25, title="분포 대비 내 탱크 위치", template="plotly_white")
    fig_pos.add_vline(x=내부식률, line_dash="dash", line_color="red",
                      annotation_text="내 탱크", annotation_position="top left")
    st.plotly_chart(fig_pos, use_container_width=True)

# =========================
# 4) 이상치(IQR) 점검 (데이터 품질 확인)
# =========================
st.markdown("### 🧪 이상치(IQR) 점검")
s = df["부식률"].astype(float).dropna()
if len(s) >= 5:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outlier_rate = float(((s < low) | (s > high)).sum() / len(s) * 100.0)
    st.write(f"- IQR: {iqr:.6f} / 하한: {low:.6f} / 상한: {high:.6f}")
    st.write(f"- 이상치 비율: **{outlier_rate:.1f}%**")
    if outlier_rate > 10:
        st.warning("이상치 비율이 높습니다. 데이터 클리닝(센서 오류/입력 실수) 검토를 권장합니다.")
else:
    st.caption("표본이 5개 미만이라 IQR 기반 이상치 점검을 생략합니다.")

# =========================
# 5) 시나리오 테이블 (평균/P50/P75/P90)
# =========================
st.markdown("### 🔮 시나리오별 예상두께/수명/판정")
years_left = st.number_input("다음 정밀정기검사까지 남은 기간 (년)", min_value=0.0, value=3.0, step=0.5)

def scenario_rows(my_thk_meas: float, my_rate_input: float, yrs_left: float):
    rows = []
    if len(df) == 0 or pd.isna(my_thk_meas):
        return pd.DataFrame(columns=["시나리오","대표부식률(mm/년)","예상부식량(mm)","예상두께(mm)","잔여수명(년)","판정"])
    series = df["부식률"].astype(float).dropna()
    reps = {
        "평균": series.mean(),
        "중위수(P50)": series.median(),
        "상위75%(보수)": series.quantile(0.75),
        "상위90%(매우보수)": series.quantile(0.90),
    }

    # 최소 하한 적용
    for k in reps:
        if reps[k] < 0.0005:
            reps[k] = 0.0005

    for name, rate in reps.items():
        est_loss = rate * yrs_left
        est_thk = (my_thk_meas or 0.0) - est_loss
        life = (my_thk_meas - ALLOWABLE_THK) / rate if rate > 0 else math.inf
        if est_thk >= ALLOWABLE_THK:
            judge = "✅ 적합"
        else:
            judge = "⚠️ 부적합"
        rows.append({
            "시나리오": name,
            "대표부식률(mm/년)": round(rate, 5),
            "예상부식량(mm)": round(est_loss, 3),
            "예상두께(mm)": round(est_thk, 3),
            "잔여수명(년)": (">100" if life > 100 else round(life, 1)),
            "판정": judge
        })
    return pd.DataFrame(rows)

scenario_df = scenario_rows(측정두께, 내부식률, years_left)
st.dataframe(scenario_df, use_container_width=True, height=200)

# 막대 그래프로 비교(대표부식률 vs 예상두께)
if len(scenario_df) > 0:
    colg1, colg2 = st.columns(2)
    with colg1:
        fig_r = px.bar(scenario_df, x="시나리오", y="대표부식률(mm/년)", title="시나리오별 대표 부식률", template="plotly_white")
        st.plotly_chart(fig_r, use_container_width=True)
    with colg2:
        fig_t = px.bar(scenario_df, x="시나리오", y="예상두께(mm)", title=f"{years_left:.1f}년 후 예상 두께", template="plotly_white")
        fig_t.add_hline(y=ALLOWABLE_THK, line_dash="dot", annotation_text=f"허용두께 {ALLOWABLE_THK}mm")
        st.plotly_chart(fig_t, use_container_width=True)

# =========================
# 6) 액션 추천(룰 기반)
# =========================
st.markdown("### 🛠️ 권장 조치 (룰 기반)")
tips = []
if pd.isna(내부식률) or pd.isna(측정두께):
    tips.append("측정두께/내부식률을 입력하여 개별 리스크 정밀 분석을 진행하세요.")
else:
    # 평균 대비 비율로 가늠
    mean_rate = aggr["mean"] or 0.0
    ratio = (내부식률 / mean_rate) if (mean_rate > 0 and not pd.isna(내부식률)) else None
    if ratio is not None:
        if ratio <= 1.0:
            tips.append("현재 부식률은 조건 평균 수준 이하입니다. 정기점검 주기는 현행 유지 권장.")
        elif ratio <= 1.5:
            tips.append("부식률이 평균보다 다소 높습니다. 두께 측정 밀도(포인트 수)를 소폭 늘려 추세 확인을 권장.")
        else:
            tips.append("부식률이 평균보다 높습니다. 방식 개선(전기방식 점검/아노드 상태/코팅 보수) 및 단기 재측정 계획을 검토.")
    # 허용두께 접근성
    if 측정두께 - ALLOWABLE_THK <= 1.0:
        tips.append("허용두께(3.2mm)까지 여유가 1.0mm 이내입니다. 단기 보수 또는 사용조건(온도/유속) 재검토를 권장.")
    if years_left >= 3 and len(scenario_df) > 0 and any(scenario_df["판정"] == "⚠️ 부적합"):
        tips.append(f"{years_left:.1f}년 후 부적합 시나리오가 존재합니다. 점검주기를 단축(예: 1~2년)하고 중간 재검을 권장.")
if len(tips) == 0:
    tips.append("추가 리스크 요인이 발견되지 않았습니다. 현행 유지하되 정기점검을 지속하세요.")

for t in tips:
    st.write(f"- {t}")

# =========================
# 7) 보고서 다운로드 (텍스트/CSV)
# =========================
st.markdown("### 🧾 결과 요약 다운로드")

# 텍스트 보고서
def build_text_report() -> str:
    lines = []
    lines.append("=== 위험물탱크 결과 분석 (로컬) ===")
    lines.append(f"표본 수: {aggr['n']}")
    lines.append(f"부식률 통계: mean={aggr['mean']:.5f}, p50={aggr['p50']:.5f}, p75={aggr['p75']:.5f}, p90={aggr['p90']:.5f}")
    if not pd.isna(내부식률):
        lines.append(f"내부식률(내 탱크): {내부식률:.5f} mm/년")
    if not pd.isna(측정두께):
        lines.append(f"현재 측정두께: {측정두께:.3f} mm (허용두께 {ALLOWABLE_THK} mm)")
    if not pd.isna(사용연수_내탱크):
        lines.append(f"사용연수(내 탱크): {사용연수_내탱크:.1f} 년")
    lines.append("")
    lines.append(f"[What-if] 남은기간 = {years_left:.1f} 년")
    if len(scenario_df) > 0:
        for _, r in scenario_df.iterrows():
            lines.append(
                f"- {r['시나리오']}: rate={r['대표부식률(mm/년)']:.5f}, "
                f"loss={r['예상부식량(mm)']:.3f}, thk={r['예상두께(mm)']:.3f}, "
                f"life={r['잔여수명(년)']}, judge={r['판정']}"
            )
    lines.append("")
    lines.append("권장 조치:")
    for t in tips:
        lines.append(f"• {t}")
    return "\n".join(lines)

report_txt = build_text_report()
st.download_button(
    label="⬇️ 텍스트 보고서 다운로드",
    data=report_txt.encode("utf-8"),
    file_name="analysis_report.txt",
    mime="text/plain"
)

# CSV (시나리오 테이블)
if len(scenario_df) > 0:
    csv_buf = io.StringIO()
    scenario_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ 시나리오 테이블 CSV 다운로드",
        data=csv_buf.getvalue(),
        file_name="scenario_analysis.csv",
        mime="text/csv",
    )

st.caption("※ 본 분석은 통계적 참고자료이며, 최종 안전판정은 관련 법령·기준 및 공인검사 절차에 따릅니다.")
