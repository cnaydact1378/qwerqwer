# 합성 생산자료 Streamlit 대시보드

현재 프로젝트의 입력 확인부터 분석·검증·사람 승인 안내까지 작업별 탭으로 통합한 배포용 앱입니다.

- `폴더`: 배포 파일 구성과 현재 입력 경로
- `작업 안내`: 처리 순서와 해석 원칙
- `CSV 미리보기`: 자동 수정하지 않은 입력값 미리보기
- `데이터 검증`: 필수 열, LOT, 설비, 날짜, 수량, 합성 표기 검사
- `LOT 연결`: LOT와 날짜·설비·불량유형 연결
- `장비별 수율`: 장비별 수량 합계 기준 수율
- `불량 파레토`: 불량수량 합계와 누적비중
- `수율 추이`: 모든 달력일을 포함한 수율·검사수량 그래프
- `검증`: 자동 검증 근거와 결과 다운로드
- `사람 승인`: 자동 검증과 분리된 담당자 확인 안내

## 폴더 구조

```text
ax_work/
└─ streamlit_dashboard_20261026_134301/
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
cd C:\Users\eyeqlab010\Desktop\ax_work\streamlit_dashboard_20261026_134301
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

