"""합성 생산자료의 불량 파레토와 생산 수율을 탭으로 제공하는 Streamlit 앱."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = APP_DIR / "data" / "SYNTHETIC_production.csv"
REQUIRED_COLUMNS = [
    "lot_id",
    "work_date",
    "equipment_id",
    "inspected_qty",
    "good_qty",
    "defect_type",
]
INTEGER_PATTERN = re.compile(r"^[0-9]+$")
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
TEAL = "#159D9A"
PURPLE = "#7652B7"
ORANGE = "#EF7D31"


st.set_page_config(
    page_title="합성 생산자료 분석",
    page_icon="📊",
    layout="wide",
)


def configure_font() -> None:
    """Windows에서는 맑은 고딕을 우선하고, 배포 환경에서는 한글 글꼴 패키지를 사용한다."""
    malgun = Path("C:/Windows/Fonts/malgun.ttf")
    if malgun.exists():
        font_manager.fontManager.addfont(malgun)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=malgun).get_name()
    else:
        try:
            import koreanize_matplotlib  # noqa: F401
        except ImportError:
            plt.rcParams["font.family"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


@st.cache_data(show_spinner=False)
def read_default_csv(path_text: str) -> pd.DataFrame:
    """기본 CSV를 문자열 그대로 읽는다."""
    return pd.read_csv(
        path_text,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )


def read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(
        uploaded_file,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )


def validate_data(df: pd.DataFrame) -> tuple[pd.DataFrame | None, pd.DataFrame]:
    """원본 값을 고치거나 삭제하지 않고 오류를 행 단위로 수집한다."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        errors = pd.DataFrame(
            [{
                "CSV 줄 번호": 1,
                "LOT 번호": "(확인 불가)",
                "오류 사유": "필수 열 누락: " + ", ".join(missing_columns),
            }]
        )
        return None, errors
    if df.empty:
        return None, pd.DataFrame(
            [{"CSV 줄 번호": 2, "LOT 번호": "(누락)", "오류 사유": "데이터 행이 없음"}]
        )

    trimmed_lot = df["lot_id"].str.strip()
    duplicated_lot = trimmed_lot.ne("") & trimmed_lot.duplicated(keep=False)
    error_rows: list[dict[str, int | str]] = []

    for index, row in df.iterrows():
        csv_line = int(index) + 2
        raw_lot = row["lot_id"]
        reasons: list[str] = []

        if not raw_lot.strip():
            reasons.append("LOT 번호 누락")
        if duplicated_lot.loc[index]:
            reasons.append(f"앞뒤 공백 제거 후 LOT 번호 중복: {raw_lot.strip()}")
        if not row["equipment_id"].strip():
            reasons.append("설비 번호 누락")
        if not row["defect_type"].strip():
            reasons.append("불량유형 누락")

        raw_date = row["work_date"]
        exact_date = bool(DATE_PATTERN.fullmatch(raw_date))
        parsed_date = (
            pd.to_datetime(raw_date, format="%Y-%m-%d", errors="coerce")
            if exact_date
            else pd.NaT
        )
        if not exact_date or pd.isna(parsed_date):
            reasons.append("실제 존재하는 YYYY-MM-DD 날짜가 아님")

        parsed_quantities: dict[str, int] = {}
        for column, label in (("inspected_qty", "검사수량"), ("good_qty", "양품수량")):
            value = row[column]
            if not INTEGER_PATTERN.fullmatch(value):
                reasons.append(f"{label}이 0~9 숫자로만 구성된 정수가 아님")
            else:
                parsed_quantities[column] = int(value)

        inspected = parsed_quantities.get("inspected_qty")
        good = parsed_quantities.get("good_qty")
        if inspected is not None and inspected <= 0:
            reasons.append("검사수량이 0보다 크지 않음")
        if inspected is not None and good is not None and not 0 <= good <= inspected:
            reasons.append("양품수량이 0 이상 검사수량 이하가 아님")

        if reasons:
            error_rows.append(
                {
                    "CSV 줄 번호": csv_line,
                    "LOT 번호": raw_lot if raw_lot.strip() else "(누락)",
                    "오류 사유": "; ".join(reasons),
                }
            )

    if error_rows:
        return None, pd.DataFrame(error_rows)

    validated = df.copy()
    validated["lot_id"] = trimmed_lot
    validated["equipment_id"] = validated["equipment_id"].str.strip()
    validated["defect_type"] = validated["defect_type"].str.strip()
    validated["work_date"] = pd.to_datetime(validated["work_date"], format="%Y-%m-%d")
    validated["inspected_qty"] = validated["inspected_qty"].astype("int64")
    validated["good_qty"] = validated["good_qty"].astype("int64")
    validated["defect_qty"] = validated["inspected_qty"] - validated["good_qty"]
    return validated, pd.DataFrame(columns=["CSV 줄 번호", "LOT 번호", "오류 사유"])


def verify_synthetic(df: pd.DataFrame) -> bool:
    """프로젝트 규칙에 맞는 합성 표기가 모든 행에 있는지 확인한다."""
    return bool(
        df["lot_id"].str.startswith("SYN-").all()
        and df["equipment_id"].str.startswith("EQ-SIM-").all()
        and df["defect_type"].str.startswith("SIM-").all()
    )


def build_pareto(df: pd.DataFrame) -> pd.DataFrame:
    pareto = (
        df.groupby("defect_type", as_index=False)["defect_qty"]
        .sum()
        .sort_values(["defect_qty", "defect_type"], ascending=[False, True])
        .reset_index(drop=True)
    )
    total = int(pareto["defect_qty"].sum())
    pareto["share_pct"] = pareto["defect_qty"] / total * 100
    pareto["cumulative_pct"] = pareto["defect_qty"].cumsum() / total * 100
    if not bool(abs(float(pareto.iloc[-1]["cumulative_pct"]) - 100.0) < 1e-10):
        raise RuntimeError("누적 비중 마지막 값이 100%가 아닙니다.")
    return pareto


def build_daily(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
    source_inspected = int(df["inspected_qty"].sum())
    source_good = int(df["good_qty"].sum())
    observed = (
        df.groupby("work_date")
        .agg(
            lot_count=("lot_id", "size"),
            inspected_qty=("inspected_qty", "sum"),
            good_qty=("good_qty", "sum"),
        )
        .sort_index()
    )
    if int(observed["inspected_qty"].sum()) != source_inspected:
        raise RuntimeError("집계 전후 검사수량 합계가 다릅니다.")
    if int(observed["good_qty"].sum()) != source_good:
        raise RuntimeError("집계 전후 양품수량 합계가 다릅니다.")

    calendar = pd.date_range(observed.index.min(), observed.index.max(), freq="D")
    daily = observed.reindex(calendar)
    daily.index.name = "work_date"
    daily["yield_pct"] = daily["good_qty"] / daily["inspected_qty"] * 100
    summary = {
        "period_start": calendar.min().strftime("%Y-%m-%d"),
        "period_end": calendar.max().strftime("%Y-%m-%d"),
        "total_inspected": source_inspected,
        "total_good": source_good,
        "overall_yield_pct": source_good / source_inspected * 100,
        "observed_days": int(observed.shape[0]),
        "missing_days": int(daily["inspected_qty"].isna().sum()),
    }
    return daily, summary


def pareto_figure(pareto: pd.DataFrame) -> plt.Figure:
    fig, left = plt.subplots(figsize=(12, 6.5))
    right = left.twinx()
    x = range(len(pareto))
    bars = left.bar(x, pareto["defect_qty"], color="#3972D5", width=0.58, label="불량수량")
    line = right.plot(
        x,
        pareto["cumulative_pct"],
        color=ORANGE,
        linewidth=2.8,
        marker="o",
        label="누적비중",
    )
    left.bar_label(bars, labels=[f"{value:,}" for value in pareto["defect_qty"]], padding=4)
    for index, value in enumerate(pareto["cumulative_pct"]):
        right.annotate(f"{value:.2f}%", (index, value), xytext=(0, -20), textcoords="offset points", ha="center", color=ORANGE)
    left.set_xticks(list(x), pareto["defect_type"])
    left.set_ylabel("불량수량 (개)")
    right.set_ylabel("누적비중 (%)")
    right.set_ylim(0, 105)
    left.set_title("불량유형 파레토 — 불량수량 기준", loc="left", fontweight="bold")
    left.grid(axis="y", alpha=0.2)
    left.legend([bars, line[0]], ["불량수량", "누적비중"], loc="upper right")
    fig.tight_layout()
    return fig


def yield_figure(daily: pd.DataFrame) -> plt.Figure:
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    top.plot(
        daily.index,
        daily["yield_pct"],
        color=TEAL,
        linewidth=2.3,
        marker="o",
        markersize=4,
        label="일별 수율",
    )
    top.set_title("날짜별 생산 수율", loc="left", fontweight="bold")
    top.set_ylabel("수율 (%)")
    top.set_ylim(0, 100)
    top.grid(axis="y", alpha=0.2)
    top.legend(loc="lower left")

    present = daily["inspected_qty"].notna()
    bottom.bar(
        daily.index[present],
        daily.loc[present, "inspected_qty"],
        width=0.72,
        color=PURPLE,
        label="검사수량",
    )
    bottom.set_title("날짜별 검사수량", loc="left", fontweight="bold")
    bottom.set_ylabel("검사수량 (개)")
    bottom.set_xlabel("작업 날짜")
    bottom.grid(axis="y", alpha=0.2)
    bottom.legend(loc="upper left")
    locator = mdates.AutoDateLocator(minticks=4, maxticks=12)
    bottom.xaxis.set_major_locator(locator)
    bottom.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.text(
        0.5,
        0.005,
        "결측은 0%가 아니라 기록 없음이며, 수율은 수량 합계로 계산함",
        ha="center",
        color="#53606F",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


def figure_png(figure: plt.Figure) -> bytes:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    return buffer.getvalue()


def daily_export(daily: pd.DataFrame) -> pd.DataFrame:
    table = daily.reset_index()
    table["work_date"] = table["work_date"].dt.strftime("%Y-%m-%d")
    output = pd.DataFrame({"work_date": table["work_date"]})
    for column in ("lot_count", "inspected_qty", "good_qty"):
        output[column] = table[column].map(
            lambda value: "데이터 없음" if pd.isna(value) else str(int(value))
        )
    output["yield_pct"] = table["yield_pct"].map(
        lambda value: "데이터 없음" if pd.isna(value) else f"{value:.2f}%"
    )
    return output


def ai_summary(summary: dict[str, int | float | str]) -> dict:
    return {
        "summary_cards": {
            "period": {"start": summary["period_start"], "end": summary["period_end"]},
            "total_inspected": summary["total_inspected"],
            "total_good": summary["total_good"],
            "overall_yield_pct": round(float(summary["overall_yield_pct"]), 2),
            "observed_days": summary["observed_days"],
            "missing_days": summary["missing_days"],
        },
        "interpretation_rules": [
            "결측은 0%가 아니라 기록 없음으로 해석한다.",
            "수율은 LOT별 단순 평균이 아니라 수량 합계로 계산한다.",
            "파레토 순위는 우선 검토 근거이며 원인 증명이 아니다.",
            "제공되지 않은 일별 추세, 불량 원인, 설비 우열은 추측하지 않는다.",
        ],
        "automatic_validation": {"status": "통과"},
        "human_approval": {"status": "미승인", "note": "담당자 검토가 필요합니다."},
    }


def render_metrics(summary: dict[str, int | float | str]) -> None:
    columns = st.columns(6)
    values = [
        ("집계 기간", f"{summary['period_start']} ~ {summary['period_end']}"),
        ("총 검사수량", f"{summary['total_inspected']:,}개"),
        ("총 양품수량", f"{summary['total_good']:,}개"),
        ("전체 수율", f"{summary['overall_yield_pct']:.2f}%"),
        ("검사한 날짜", f"{summary['observed_days']:,}일"),
        ("데이터 없는 날짜", f"{summary['missing_days']:,}일"),
    ]
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)


def main() -> None:
    configure_font()
    st.title("📊 합성 생산자료 분석 대시보드")
    st.caption("불량수량 파레토와 날짜별 생산 수율을 작업별 탭으로 확인합니다.")

    with st.sidebar:
        st.header("입력 자료")
        uploaded = st.file_uploader("합성 production.csv 선택", type=["csv"])
        st.info("업로드 자료도 SYN-/SIM- 표기의 합성 연습자료만 사용할 수 있습니다.")

    try:
        if uploaded is not None:
            raw = read_uploaded_csv(uploaded)
            source_name = uploaded.name
        else:
            raw = read_default_csv(str(DEFAULT_INPUT))
            source_name = str(DEFAULT_INPUT)
    except Exception as exc:
        st.error(f"CSV를 읽을 수 없습니다: {exc}")
        st.stop()

    validated, errors = validate_data(raw)
    if validated is None:
        st.error("입력 데이터 검증에 실패하여 집계를 중단했습니다. 오류 행은 삭제하거나 수정하지 않았습니다.")
        st.dataframe(errors, use_container_width=True, hide_index=True)
        st.stop()
    if not verify_synthetic(validated):
        st.error("합성자료 표기(SYN-, EQ-SIM-, SIM-)를 충족하지 않아 처리를 중단했습니다.")
        st.stop()

    try:
        pareto = build_pareto(validated)
        daily, summary = build_daily(validated)
    except Exception as exc:
        st.error(f"집계 중 오류가 발생했습니다: {exc}")
        st.stop()

    st.success(f"자동 검증 통과 · 입력: {source_name} · {len(validated):,}행")
    pareto_tab, yield_tab, export_tab = st.tabs(
        ["① 불량 파레토", "② 생산 수율", "③ 검증·내보내기"]
    )

    with pareto_tab:
        st.subheader("불량수량 기준 유형별 우선순위")
        st.caption("defect_qty = inspected_qty - good_qty · LOT 건수가 아닌 불량수량 기준")
        pareto_fig = pareto_figure(pareto)
        st.pyplot(pareto_fig, use_container_width=True)
        st.dataframe(
            pareto.style.format(
                {"defect_qty": "{:,.0f}", "share_pct": "{:.2f}%", "cumulative_pct": "{:.2f}%"}
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.warning("이 순위는 우선 검토 근거이며 불량 원인 또는 인과관계의 증명이 아닙니다.")

    with yield_tab:
        st.subheader("날짜별 생산 수율")
        render_metrics(summary)
        yield_fig = yield_figure(daily)
        st.pyplot(yield_fig, use_container_width=True)
        st.dataframe(daily_export(daily), use_container_width=True, hide_index=True)

    with export_tab:
        st.subheader("자동 검증과 결과 다운로드")
        left, right = st.columns(2)
        left.success("자동 검증: 통과")
        right.warning("사람 승인: 미승인")
        st.write("필수 열·LOT·설비·날짜·수량 검증과 집계 전후 수량 합계 일치를 확인했습니다.")

        daily_csv = daily_export(daily).to_csv(index=False).encode("utf-8-sig")
        pareto_csv = pareto.to_csv(index=False).encode("utf-8-sig")
        summary_json = json.dumps(
            ai_summary(summary), ensure_ascii=False, indent=2, allow_nan=False
        ).encode("utf-8")
        dashboard_png = figure_png(yield_figure(daily))

        buttons = st.columns(4)
        buttons[0].download_button("일별 요약 CSV", daily_csv, "daily_summary.csv", "text/csv")
        buttons[1].download_button("파레토 CSV", pareto_csv, "pareto_summary.csv", "text/csv")
        buttons[2].download_button("AI 요약 JSON", summary_json, "ai_summary.json", "application/json")
        buttons[3].download_button("수율 PNG", dashboard_png, "production_dashboard.png", "image/png")
        st.caption("다운로드 결과에는 원본 행 전체를 담지 않으며, 입력 CSV는 수정하지 않습니다.")


if __name__ == "__main__":
    main()

