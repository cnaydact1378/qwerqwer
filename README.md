# 합성 생산자료 Streamlit 대시보드

현재 프로젝트에서 수행한 두 분석을 작업별 탭으로 통합한 배포용 앱입니다.

- `① 불량 파레토`: `defect_qty = inspected_qty - good_qty`를 유형별로 합산하고 누적비중을 표시합니다.
- `② 생산 수율`: 모든 달력일을 포함해 일별 수율과 검사수량을 표시합니다.
- `③ 검증·내보내기`: 자동 검증/사람 승인 상태와 CSV·JSON·PNG 다운로드를 제공합니다.

## 폴더 구조

```text
ax_work/
└─ streamlit_dashboard_20261026_132510/
   ├─ streamlit_app.py                  # Streamlit 진입점
   ├─ requirements.txt
   ├─ README.md
   ├─ data/
   │  └─ SYNTHETIC_production.csv       # 배포용 합성 입력 사본
   └─ .streamlit/
      └─ config.toml
```

앱은 코드 파일 기준 `data/SYNTHETIC_production.csv`를 기본 입력으로 사용합니다. 이 파일은 프로젝트의 합성 `원본/production.csv`와 SHA-256이 같은 읽기 전용 배포 사본입니다. 사이드바에서 다른 합성 CSV를 올릴 수도 있습니다. 합성 표기 규칙을 충족하지 않는 파일은 처리하지 않습니다.

## 로컬 실행

PowerShell에서 다음 명령을 실행합니다.

```powershell
cd C:\Users\eyeqlab010\Desktop\ax_work\streamlit_dashboard_20261026_132510
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

브라우저가 자동으로 열리지 않으면 터미널에 표시되는 `Local URL`을 엽니다.

## Streamlit Community Cloud 배포

외부 공개 배포에는 GitHub와 Streamlit 계정 인증이 필요합니다.

1. [Streamlit Community Cloud](https://share.streamlit.io/)에서 **Create app**을 선택합니다.
2. 저장소 `cnaydact1378/qwerqwer`와 브랜치 `main`을 선택합니다.
3. 배포 설정을 엽니다.
4. `qwerqwer` 저장소에서는 Main file path를 다음과 같이 지정합니다.

   ```text
   streamlit_app.py
   ```

5. 배포를 시작합니다. 별도 비밀값이나 API 키는 필요하지 않습니다.

합성 연습자료만 저장소에 포함해야 하며 실제 개인정보나 업무 원본은 올리지 마세요.

## 데이터 처리 원칙

- CSV는 `encoding="utf-8-sig"`, `dtype=str`로 읽은 뒤 검증을 통과한 경우에만 형 변환합니다.
- 오류 행은 삭제하거나 자동 수정하지 않습니다.
- 결측일은 0이나 보간값으로 채우지 않습니다.
- 수율은 LOT별 단순 평균이 아니라 수량 합계로 계산합니다.
- 파레토 순위는 우선 검토 근거이며 원인 증명이 아닙니다.
- 자동 검증 통과와 사람 승인은 별도로 표시합니다.

