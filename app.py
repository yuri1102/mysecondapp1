import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 기본 설정 (전문적인 대시보드 느낌의 와이드 레이아웃)
st.set_page_config(
    page_title="수업 활동 점검 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 커스텀 (기획안의 블루/그린/주황 포인트 반영)
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .metric-box { background-color: #FFFFFF; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("📊 수업 활동 점검 대시보드")
st.caption("학생들의 활동 결과를 분석하고 회의용 요약을 자동으로 생성합니다.")
st.write("---")

# 2. 사이드바: 파일 업로드 및 설정
with st.sidebar:
    st.header("📁 데이터 업로드 및 설정")
    uploaded_file = st.file_uploader("활동 결과 CSV 파일을 선택하세요.", type=["csv"])
    
    st.write("---")
    st.header("🔒 개인정보 보호")
    # 이름 숨기기 옵션 제공
    mask_privacy = st.checkbox("학생 이름 숨기기 (student_id만 표시)", value=True)
    
    st.info("⚠️ 본 대시보드는 브라우저 메모리 내에서만 데이터를 처리하며, 어떠한 개인정보도 서버에 저장하지 않습니다.")

# 3. 데이터 로드 및 메인 대시보드 로직
if uploaded_file is not None:
    try:
        # CSV 로드
        df = pd.read_csv(uploaded_file)
        
        # 필수 컬럼 검증 (학번, 이름, 반, 모둠, 제출여부, 점수)
        required_cols = ['student_id', 'name', 'class', 'team', 'submitted', 'score']
        if not all(col in df.columns for col in required_cols):
            st.error(f"CSV 파일의 컬럼을 확인해주세요. 필수 컬럼: {', '.join(required_cols)}")
            st.stop()
            
        # 개인정보 마스킹 처리
        if mask_privacy:
            df['display_name'] = df['student_id'].astype(str)
        else:
            df['display_name'] = df['name'] + "(" + df['student_id'].astype(str) + ")"

        # 사이드바 필터 적용
        st.sidebar.write("---")
        st.sidebar.header("🔍 필터 설정")
        
        all_classes = sorted(df['class'].unique())
        selected_class = st.sidebar.selectbox("반 선택", ["전체"] + list(all_classes))
        
        # 선택한 반에 따른 모둠 필터 가변 처리
        if selected_class != "전체":
            filtered_df = df[df['class'] == selected_class]
            all_teams = sorted(filtered_df['team'].unique())
        else:
            filtered_df = df
            all_teams = sorted(df['team'].unique())
            
        selected_team = st.sidebar.selectbox("모둠 선택", ["전체"] + list(all_teams))
        
        if selected_team != "전체":
            filtered_df = filtered_df[filtered_df['team'] == selected_team]

        # 4. 핵심 지표 (KPI Metrics) 표시
        total_students = len(filtered_df)
        submitted_students = len(filtered_df[filtered_df['submitted'] == 'Y'])
        submission_rate = (submitted_students / total_students * 100) if total_students > 0 else 0
        avg_score = filtered_df[filtered_df['submitted'] == 'Y']['score'].mean() if submitted_students > 0 else 0
        not_submitted = total_students - submitted_students

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="📈 제출률", value=f"{submission_rate:.1f}%", delta=f"{submitted_students}/{total_students} 명")
        with col2:
            st.metric(label="⭐ 제출자 평균 점수", value=f"{avg_score:.1f} 점")
        with col3:
            # 미제출자가 있을 경우 주황색 경고 느낌을 주기 위해 delta에 표시
            st.metric(label="⚠️ 미제출 학생 수", value=f"{not_submitted} 명", delta=f"-{not_submitted}" if not_submitted > 0 else None, delta_color="inverse")

        st.write("---")

        # 5. 시각화 및 상세 명단 (2단 레이아웃)
        layout_col1, layout_col2 = st.columns([3, 2])

        with layout_col1:
            st.subheader("👥 모둠별 평균 점수 및 제출 현황")
            # 모둠별 데이터 집계
            team_summary = filtered_df.groupby('team').agg(
                평균점수=('score', 'mean'),
                제출자수=('submitted', lambda x: (x == 'Y').sum())
            ).reset_index()
            
            # Plotly 막대그래프 (전문적인 블루/그린 톤 활용)
            fig = px.bar(
                team_summary, 
                x='team', 
                y='평균점수', 
                text_auto='.1f',
                title="모둠별 평균 점수 (제출자 기준)",
                color_discrete_sequence=['#1F77B4']
            )
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with layout_col2:
            st.subheader("🚨 미제출 / 보완 필요 대상")
            
            # 미제출자 명단
            unsubmitted_list = filtered_df[filtered_df['submitted'] == 'N'][['class', 'team', 'display_name']]
            st.markdown("**❌ 미제출자 명단**")
            if not unsubmitted_list.empty:
                st.dataframe(unsubmitted_list, use_container_width=True, hide_index=True)
            else:
                st.success("모든 학생이 제출했습니다! 🎉")
                
            # 보완 필요자 명단 (예: 제출했으나 점수가 60점 미만인 학생)
            st.markdown("**⚠️ 피드백 필요 학생 (60점 미만)**")
            needs_help = filtered_df[(filtered_df['submitted'] == 'Y') & (filtered_df['score'] < 60)][['class', 'team', 'display_name', 'score']]
            if not needs_help.empty:
                st.dataframe(needs_help, use_container_width=True, hide_index=True)
            else:
                st.info("보완이 필요한 학생이 없습니다.")

        st.write("---")

        # 6. 회의용 자동 요약 기능
        st.subheader("📝 교과협의회 / 학년부 회의용 요약 브리핑")
        
        # 텍스트 요약 자동 생성
        summary_text = f"""[수업 활동 결과 요약 리포트]
- 대상: {selected_class if selected_class != '전체' else '전체 학급'} ({selected_team if selected_team != '전체' else '전체 모둠'})
- 총원: {total_students}명 중 {submitted_students}명 제출 (제출률 {submission_rate:.1f}%)
- 제출자 평균 점수: {avg_score:.1f}점
- 미제출 학생: {', '.join(unsubmitted_list['display_name'].tolist()) if not unsubmitted_list.empty else '없음'}
- 주요 특이사항: 모둠별 평균 확인 결과, 점수 편차에 따른 후속 피드백 예정."""

        st.text_area("아래 내용을 복사하여 회의록이나 메신저에 공유하세요.", value=summary_text, height=180)

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")

else:
    # 파일 업로드 전 가이드 화면
    st.info("💡 대시보드를 시작하려면 좌측 사이드바에서 학생 활동 결과 CSV 파일을 업로드해주세요.")
    
    # 테스트용 샘플 데이터 구조 안내
    st.subheader("📋 올바른 CSV 파일 예시 형식")
    sample_data = {
        'student_id': [10101, 10102, 10103, 10104],
        'name': ['김철수', '이영희', '박민수', '최지우'],
        'class': [1, 1, 1, 1],
        'team': ['1모둠', '1모둠', '2모둠', '2모둠'],
        'submitted': ['Y', 'Y', 'N', 'Y'],
        'score': [85, 90, 0, 55]
    }
    st.table(pd.DataFrame(sample_data))
