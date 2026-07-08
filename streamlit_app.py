from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
COLORS = ["#126c70", "#1258b8", "#b45309", "#047857", "#7c3aed", "#b42318", "#64748b"]
TARGET_TOTAL_YIELD = 93.0
TARGET_CATEGORY_YIELD = 20.0


st.set_page_config(
    page_title="PVM肉品产值分析报表",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f4f7fb; color: #122033; }
    .block-container { padding-top: 1.2rem; max-width: 1600px; }
    div[data-testid="stMetric"] {
      background: #fff;
      border: 1px solid #dde6f0;
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 8px 20px rgba(15,23,42,.05);
    }
    .focus-card {
      background: #fff;
      border: 1px solid #dde6f0;
      border-radius: 8px;
      padding: 14px 15px;
      min-height: 112px;
      box-shadow: 0 8px 20px rgba(15,23,42,.05);
    }
    .focus-card.risk { background: #fffaf0; border-color: #f0d9a9; }
    .focus-label { color: #64748b; font-size: 12px; margin-bottom: 8px; }
    .focus-value { color: #122033; font-size: 22px; font-weight: 800; line-height: 1.25; }
    .focus-detail { color: #475569; font-size: 13px; margin-top: 8px; line-height: 1.45; }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_index() -> dict[str, Any]:
    return load_json(DATA_DIR / "index.json")


@st.cache_data(show_spinner=False)
def load_report(date_value: str) -> dict[str, Any]:
    if date_value == "latest":
        return load_json(DATA_DIR / "latest.json")
    return load_json(DATA_DIR / "daily" / f"{date_value}.json")


def num(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}{suffix}"
    return str(value)


def pct(value: Any) -> str:
    return fmt(num(value), "%")


def factory_yield(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产成率"))


def factory_price(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产值"))


def overview_rows(report: dict[str, Any], factories: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for factory in factories:
        for row in factory.get("overview", []):
            rows.append(
                {
                    "工厂": factory.get("factory"),
                    "品类": row.get("项目"),
                    "产量kg": num(row.get("产量(kg)")),
                    "销量kg": num(row.get("销量(kg)")),
                    "产成率": num(row.get("产成率%")),
                    "含税金额": num(row.get("含税金额")),
                    "含税单价": num(row.get("含税单价")),
                    "产销率": num(row.get("产销率")),
                }
            )
    return pd.DataFrame(rows)


def sku_rows(factory: dict[str, Any]) -> pd.DataFrame:
    rows = factory.get("sku", {}).get("top_amount", [])
    return pd.DataFrame(rows)


def card(label: str, value: str, detail: str, risk: bool = False) -> None:
    klass = "focus-card risk" if risk else "focus-card"
    st.markdown(
        f"""
        <div class="{klass}">
          <div class="focus-label">{label}</div>
          <div class="focus-value">{value}</div>
          <div class="focus-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_focus_cards(report: dict[str, Any]) -> None:
    factories = report.get("factories", [])
    rows = overview_rows(report, factories)
    low_yield_factory = min(factories, key=factory_yield) if factories else {}
    high_price_factory = max(factories, key=factory_price) if factories else {}
    low_price_factory = min(factories, key=factory_price) if factories else {}
    weak_category = rows.sort_values("产成率").head(1) if not rows.empty else pd.DataFrame()
    top_category = rows.sort_values("含税金额", ascending=False).head(1) if not rows.empty else pd.DataFrame()

    cols = st.columns(4)
    with cols[0]:
        card(
            "产成率优先看",
            f"{low_yield_factory.get('factory', '-')} {pct(factory_yield(low_yield_factory))}",
            f"目标参考 {TARGET_TOTAL_YIELD:.0f}%，低于目标的厂优先复盘品类结构。",
            risk=True,
        )
    with cols[1]:
        card(
            "总单价区间",
            f"{fmt(factory_price(low_price_factory), ' 元/kg')} - {fmt(factory_price(high_price_factory), ' 元/kg')}",
            f"{high_price_factory.get('factory', '-')} 当前最高，{low_price_factory.get('factory', '-')} 当前最低。",
        )
    with cols[2]:
        if not weak_category.empty:
            row = weak_category.iloc[0]
            card("低产成率品类", f"{row['工厂']} · {row['品类']}", f"产成率 {pct(row['产成率'])}，进入明细确认产量和单价。", risk=True)
        else:
            card("低产成率品类", "-", "暂无品类数据。", risk=True)
    with cols[3]:
        if not top_category.empty:
            row = top_category.iloc[0]
            card("金额贡献最大", f"{row['工厂']} · {row['品类']}", f"含税金额 {fmt(row['含税金额'], ' 元')}，结构变化会影响总单价。")
        else:
            card("金额贡献最大", "-", "暂无品类数据。")


def metric_table(factories: list[dict[str, Any]]) -> None:
    cols = st.columns(max(len(factories), 1))
    for col, factory in zip(cols, factories):
        core = factory.get("daily_core", {})
        with col:
            st.subheader(factory.get("factory", "-"))
            st.caption(factory.get("source_file", ""))
            st.metric("总产成率", pct(core.get("总产成率")))
            st.metric("总单价", fmt(core.get("总产值"), " 元/kg"))
            st.metric("主产品产成率", pct(core.get("主产品产成率")))
            st.metric("主产品单价", fmt(core.get("主产品产值"), " 元/kg"))


def factory_comparison(report: dict[str, Any]) -> None:
    rows = []
    for factory in report.get("factories", []):
        core = factory.get("daily_core", {})
        rows.append({"工厂": factory.get("factory"), "总产成率": num(core.get("总产成率")), "总单价": num(core.get("总产值"))})
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("暂无工厂核心指标。")
        return

    fig = go.Figure()
    fig.add_bar(x=df["工厂"], y=df["总产成率"], name="总产成率", marker_color=COLORS[0], text=df["总产成率"].round(2), textposition="outside")
    fig.add_scatter(x=df["工厂"], y=df["总单价"], name="总单价", yaxis="y2", mode="lines+markers+text", text=df["总单价"].round(2), textposition="top center", marker_color=COLORS[2])
    fig.add_hline(y=TARGET_TOTAL_YIELD, line_dash="dash", line_color="#b42318", annotation_text=f"产成率目标 {TARGET_TOTAL_YIELD:.0f}%")
    fig.update_layout(
        height=420,
        margin=dict(l=20, r=30, t=36, b=20),
        yaxis=dict(title="产成率 %"),
        yaxis2=dict(title="总单价 元/kg", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def category_charts(report: dict[str, Any], factories: list[dict[str, Any]], top_n: int, query: str) -> pd.DataFrame:
    df = overview_rows(report, factories)
    if query:
        df = df[df["品类"].astype(str).str.contains(query, case=False, na=False)]
    if df.empty:
        st.info("暂无品类数据。")
        return df

    amount_df = df.sort_values("含税金额", ascending=False).head(top_n)
    yield_df = df.sort_values("产成率").head(top_n).sort_values("产成率", ascending=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("哪些品类贡献金额最大？")
        fig = px.bar(amount_df, x="含税金额", y="品类", color="工厂", orientation="h", color_discrete_sequence=COLORS)
        fig.update_layout(height=460, margin=dict(l=20, r=20, t=20, b=20), yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("哪些品类产成率拖累最大？")
        fig = px.bar(yield_df, x="产成率", y="品类", color="工厂", orientation="h", color_discrete_sequence=COLORS)
        fig.add_vline(x=TARGET_CATEGORY_YIELD, line_dash="dash", line_color="#b42318", annotation_text=f"参考 {TARGET_CATEGORY_YIELD:.0f}%")
        fig.update_layout(height=460, margin=dict(l=20, r=20, t=20, b=20), yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    return df


def price_charts(df: pd.DataFrame) -> None:
    if df.empty:
        return
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("高单价是否伴随低产成率？")
        fig = px.scatter(
            df,
            x="产成率",
            y="含税单价",
            color="工厂",
            size="含税金额",
            hover_data=["品类", "含税金额"],
            color_discrete_sequence=COLORS,
        )
        fig.add_vline(x=TARGET_CATEGORY_YIELD, line_dash="dash", line_color="#b42318")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("哪些品类单价明显偏高？")
        heat = df.pivot_table(index="工厂", columns="品类", values="含税单价", aggfunc="mean")
        fig = px.imshow(heat, aspect="auto", color_continuous_scale=["#dff3f6", "#7cc7d4", "#2385a8", "#073b63"], text_auto=".2f")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20), coloraxis_colorbar=dict(title="元/kg"))
        st.plotly_chart(fig, use_container_width=True)


def sku_chart(factory: dict[str, Any], top_n: int, query: str) -> None:
    df = sku_rows(factory)
    if df.empty:
        st.info("暂无 SKU 数据。")
        return
    if query:
        mask = (
            df.get("部位大类", "").astype(str).str.contains(query, case=False, na=False)
            | df.get("物料描述", "").astype(str).str.contains(query, case=False, na=False)
            | df.get("子类", "").astype(str).str.contains(query, case=False, na=False)
        )
        df = df[mask]
    df = df.sort_values("含税金额", ascending=False).head(top_n)
    st.subheader(f"{factory.get('factory')} SKU 收入主要来自哪里？")
    fig = px.bar(df.sort_values("含税金额"), x="含税金额", y="物料描述", color="部位大类", orientation="h", color_discrete_sequence=COLORS)
    fig.update_layout(height=480, margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.title("PVM肉品产值分析报表")
    st.caption("Streamlit Cloud 版本。数据来自仓库中的 data/latest.json、data/daily/*.json 和 data/index.json。")

    try:
        index = load_index()
    except FileNotFoundError:
        st.error("没有找到 data/index.json。请先同步日报数据到仓库。")
        return

    latest_date = index.get("latest_date")
    if not latest_date:
        st.warning("暂无日报日期。")
        return

    top_cols = st.columns([1, 1.4])
    report = load_report("latest")
    factories = report.get("factories", [])
    factory_labels = ["三厂对比", *[f.get("factory", "-") for f in factories]]
    with top_cols[0]:
        factory_label = st.selectbox("查看范围", factory_labels, index=0)
    with top_cols[1]:
        query = st.text_input("聚焦品类/SKU", placeholder="腿类、胸类、物料描述...")

    top_n = 8
    selected_factories = factories if factory_label == "三厂对比" else [f for f in factories if f.get("factory") == factory_label]
    if not selected_factories:
        selected_factories = factories

    st.markdown("## 今日重点")
    build_focus_cards(report)

    st.markdown("## 工厂核心指标")
    metric_table(selected_factories)

    st.markdown("## 三厂产成率和单价")
    factory_comparison(report)

    st.markdown("## 品类原因")
    category_df = category_charts(report, selected_factories, top_n, query)

    st.markdown("## 单价质量")
    price_charts(category_df)

    st.markdown("## SKU 和品类明细")
    sku_chart(selected_factories[0], top_n, query)
    st.dataframe(
        category_df.sort_values("含税金额", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "下载当前日报 JSON",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name=f"pvm-report-{report.get('report_date')}.json",
        mime="application/json",
    )


if __name__ == "__main__":
    main()
