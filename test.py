# -----------------------------
# ③ 향후 부식 예측 및 기대수명
# -----------------------------
st.subheader("③ 향후 부식 예측 및 기대수명")

if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:
    # 1) 사용연수 구간 설정
    bins = [0, 10, 20, 30, 200]
    labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    내연수_라벨 = pd.cut([사용연수_내탱크], bins=bins, labels=labels, right=False)[0]
    if "연수구간" not in df.columns:
        df["연수구간"] = pd.cut(df["사용연수"], bins=bins, labels=labels, right=False)

    # 2) 조건 필터링
    cond_base = (
        (df["재질"] == 재질) &
        (df["품명"] == 품명) &
        (df["탱크형상"] == 탱크형상) &
        (df["전기방식"] == 전기방식) &
        (df["히팅코일"] == 히팅코일) &
        (df["지역"] == 지역)
    )
    cond_year = (df["연수구간"] == 내연수_라벨)
    filtered_pred = df[cond_base & cond_year]

    if len(filtered_pred) >= 10:
        평균부식률_조건 = filtered_pred["부식률"].mean()
        표본수 = len(filtered_pred)
    else:
        평균부식률_조건 = df["부식률"].mean()
        표본수 = len(filtered_pred)
        st.warning(f"⚠️ 같은 구간 표본이 {표본수}개로 적어 전체 평균 사용")

    # 3) 부식률 산정 방식 및 남은 기간
    col1, col2, col3 = st.columns([0.3, 0.3, 0.4])
    with col1:
        산정방식 = st.selectbox(
            "부식률 산정 방식",
            ["평균", "중위수(P50)", "상위 75% (보수)", "상위 90% (매우 보수)"],
            key="rate_mode"
        )
    with col2:
        남은기간 = st.number_input(
            "다음 정밀정기검사까지 남은 기간 (년)",
            min_value=0.0, value=3.0, step=0.5,
            key="years_left"
        )

    # 4) 대표 부식률 계산
    if 산정방식 == "평균":
        대표부식률 = 평균부식률_조건
    elif 산정방식 == "중위수(P50)":
        대표부식률 = filtered_pred["부식률"].median() if len(filtered_pred) >= 1 else 평균부식률_조건
    elif 산정방식 == "상위 75% (보수)":
        대표부식률 = filtered_pred["부식률"].quantile(0.75) if len(filtered_pred) >= 1 else 평균부식률_조건
    else:
        대표부식률 = filtered_pred["부식률"].quantile(0.9) if len(filtered_pred) >= 1 else 평균부식률_조건

    if 대표부식률 < 0.0005:
        대표부식률 = 0.0005

    # 5) 예측 계산
    예상부식량 = 대표부식률 * 남은기간
    예상두께 = 측정두께 - 예상부식량
    기대수명 = (측정두께 - 3.2) / 대표부식률 if 대표부식률 > 0 else None

    if 기대수명 and 기대수명 > 100:
        기대수명_text = "100년 초과 (표시 생략)"
    elif 기대수명 and 기대수명 > 0:
        기대수명_text = f"{기대수명:.1f} 년 남음"
    else:
        기대수명_text = "3.2mm 이하 상태 가능"

    # 6) 판정
    if 예상두께 >= 3.2:
        판정 = "✅ 적합(합격)"
        판정색 = "#065f46"
        판정글 = "#d1fae5"
    else:
        판정 = "⚠️ 부적합(불합격)"
        판정색 = "#7f1d1d"
        판정글 = "#fee2e2"

    # -------------------------------
    # 7) 📱 반응형 CSS 추가
    # -------------------------------
    st.markdown(f"""
        <style>
            /* PC 기준 기본 */
            .tbl-dark {{
                width: 60%;
                border-collapse: collapse;
                margin: 15px 0 0 0;
                border: 1px solid #374151;
                font-size: 0.95rem;
                table-layout: fixed;
            }}
            .tbl-dark th {{
                width: 40%;
                text-align: left;
                padding: 10px;
                background-color: #1f2937;
                color: #f9fafb;
                border-bottom: 2px solid #4b5563;
                white-space: nowrap;
            }}
            .tbl-dark td {{
                width: 60%;
                padding: 8px;
                color: #e5e7eb;
                border-bottom: 1px solid #374151;
                word-break: keep-all;
            }}
            .tbl-dark tr:nth-child(even) td {{ background-color: #0b1220; }}
            .result-row {{
                background-color: {판정색};
                color: {판정글};
                font-weight: 600;
            }}

            /* ✅ 모바일 (화면 폭 768px 이하) */
            @media (max-width: 768px) {{
                div[data-testid="column"] {{
                    flex-direction: column !important;
                    width: 100% !important;
                }}
                .tbl-dark {{
                    width: 100% !important;
                    font-size: 0.85rem !important;
                }}
                div[data-testid="stHorizontalBlock"] {{
                    flex-direction: column !important;
                }}
            }}
        </style>
    """, unsafe_allow_html=True)

    # -------------------------------
    # 8) 📊 결과 표
    # -------------------------------
    st.markdown(f"""
        <table class="tbl-dark">
            <tr><th>항목</th><th>값</th></tr>
            <tr><td>사용연수 구간</td><td>{내연수_라벨}</td></tr>
            <tr><td>표본수</td><td>{표본수 if 표본수>=10 else f"{표본수} (전체보정)"}</td></tr>
            <tr><td>부식률 산정 방식</td><td>{산정방식}</td></tr>
            <tr><td>대표 부식률</td><td>{대표부식률:.5f} mm/년</td></tr>
            <tr><td>남은 기간</td><td>{남은기간:.1f} 년</td></tr>
            <tr><td>예상 부식량</td><td>{예상부식량:.3f} mm</td></tr>
            <tr><td>예상 두께 ({남은기간:.1f}년 후)</td><td>{예상두께:.3f} mm</td></tr>
            <tr class="result-row"><td>판정 결과</td><td>{판정}</td></tr>
            <tr><td>예상 잔여 수명</td><td>{기대수명_text}</td></tr>
        </table>
    """, unsafe_allow_html=True)

st.markdown("---")
