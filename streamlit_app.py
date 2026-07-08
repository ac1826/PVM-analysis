from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

FACTORY_ORDER = ["蚌埠", "大连", "铁岭"]
FACTORY_COLORS = {
    "蚌埠": "#126c70",
    "大连": "#1f5fbf",
    "铁岭": "#b65a08",
}
TARGET_TOTAL_YIELD = 93.0
TARGET_CATEGORY_YIELD = 20.0
TOP_N = 8


st.set_page_config(
    page_title="PVM肉品产值日报",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f4f7fb; color: #122033; }
    .block-container { padding-top: 1.15rem; max-width: 1500px; }
    h1, h2, h3 { color: #0b1f35; letter-spacing: 0; }
    h1 { font-size: 2.25rem; margin-bottom: .2rem; }
    h2 { margin-top: 1.25rem; }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label { color: #334155; font-weight: 750; }
    .report-meta {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 2px 0 18px;
    }
    .pill {
      border: 1px solid #d8e2ef;
      background: #fff;
      border-radius: 999px;
      color: #475569;
      padding: 6px 11px;
      font-size: 13px;
      line-height: 1.2;
    }
    .section-note {
      color: #64748b;
      font-size: 14px;
      margin: -4px 0 14px;
    }
    .summary-panel {
      background: #fff;
      border: 1px solid #d9e3ef;
      border-radius: 8px;
      padding: 18px;
      min-height: 172px;
      box-shadow: 0 8px 22px rgba(15,23,42,.045);
    }
    .summary-kicker {
      color: #64748b;
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 8px;
    }
    .summary-title {
      color: #0b1f35;
      font-size: 24px;
      font-weight: 900;
      line-height: 1.2;
      margin-bottom: 8px;
    }
    .summary-body {
      color: #475569;
      font-size: 14px;
      line-height: 1.55;
    }
    .priority-list {
      margin: 0;
      padding-left: 18px;
      color: #334155;
      font-size: 14px;
      line-height: 1.62;
    }
    .factory-card {
      background: #fff;
      border: 1px solid #d9e3ef;
      border-radius: 8px;
      padding: 16px;
      min-height: 235px;
      box-shadow: 0 8px 22px rgba(15,23,42,.045);
    }
    .factory-head {
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 12px;
      margin-bottom: 14px;
    }
    .factory-name {
      color: #0b1f35;
      font-size: 24px;
      font-weight: 900;
      line-height: 1.1;
    }
    .badge {
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    .badge.good { background: #e9f7ef; color: #136c3a; }
    .badge.warn { background: #fff2d8; color: #9a4f05; }
    .badge.hot { background: #feeceb; color: #a6261b; }
    .metric-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .metric-cell {
      border: 1px solid #e4edf6;
      border-radius: 8px;
      padding: 10px 11px;
      background: #f8fbfe;
    }
    .metric-label {
      color: #64748b;
      font-size: 12px;
      margin-bottom: 6px;
    }
    .metric-value {
      color: #0b1f35;
      font-size: 23px;
      font-weight: 900;
      line-height: 1.15;
    }
    .metric-unit {
      font-size: 15px;
      font-weight: 800;
    }
    .chart-card {
      background: #fff;
      border: 1px solid #d9e3ef;
      border-radius: 8px;
      padding: 14px 16px 8px;
      box-shadow: 0 8px 22px rgba(15,23,42,.045);
      margin-bottom: 16px;
    }
    .chart-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 6px;
    }
    .chart-title strong { color: #0b1f35; font-size: 18px; }
    .chart-title span { color: #64748b; font-size: 13px; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    @media (max-width: 900px) {
      h1 { font-size: 1.85rem; }
      .metric-grid { grid-template-columns: 1fr; }
      .factory-name { font-size: 21px; }
      .summary-title { font-size: 21px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False, ttl=60)
def load_index() -> dict[str, Any]:
    return load_json(DATA_DIR / "index.json")


def load_latest_report() -> dict[str, Any]:
    return load_json(DATA_DIR / "latest.json")


def num(value: Any) -> float:
    try:
        if value in (None, "—", "-", ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value in (None, "—", "-", ""):
        return "-"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def pct(value: Any, digits: int = 2) -> str:
    return fmt(num(value), digits, "%")


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else "-"))


def ordered_factories(report: dict[str, Any]) -> list[dict[str, Any]]:
    factories = report.get("factories", [])
    order = {name: idx for idx, name in enumerate(FACTORY_ORDER)}
    return sorted(factories, key=lambda factory: order.get(factory.get("factory", ""), 99))


def factory_yield(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产成率"))


def factory_price(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产值"))


def chart_shell(title: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="chart-card">
          <div class="chart-title">
            <strong>{esc(title)}</strong>
            <span>{esc(note)}</span>
          </div>
        """,
        unsafe_allow_html=True,
    )


def close_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def overview_rows(factories: list[dict[str, Any]]) -> pd.DataFrame:
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
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["品类"].astype(str).ne("总计")].copy()
    df["工厂"] = pd.Categorical(df["工厂"], FACTORY_ORDER, ordered=True)
    return df.sort_values(["工厂", "含税金额"], ascending=[True, False])


def sku_rows(factory: dict[str, Any], key: str = "top_amount") -> pd.DataFrame:
    rows = factory.get("sku", {}).get(key, [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.rename(columns={"产量(kg)": "产量kg"})
    for col in ["产量kg", "含税金额", "含税单价"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["工厂"] = factory.get("factory")
    return df


def all_sku_rows(factories: list[dict[str, Any]]) -> pd.DataFrame:
    frames = []
    for factory in factories:
        for key in ["top_amount", "top_volume"]:
            frame = sku_rows(factory, key)
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    keys = [col for col in ["工厂", "日期", "子类", "物料描述", "产量kg", "含税金额"] if col in df.columns]
    return df.drop_duplicates(subset=keys)


def trend_rows(factories: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for factory in factories:
        factory_name = factory.get("factory")
        for block in factory.get("trend", {}).get("blocks", []):
            metric = block.get("metric")
            headers = block.get("headers", [])
            for item in block.get("rows", []):
                category = item.get("name")
                for day, value in zip(headers, item.get("values", [])):
                    if value in (None, "—", "-", ""):
                        continue
                    rows.append(
                        {
                            "工厂": factory_name,
                            "指标": metric,
                            "品类": category,
                            "日期": day,
                            "数值": num(value),
                        }
                    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["工厂"] = pd.Categorical(df["工厂"], FACTORY_ORDER, ordered=True)
    return df.sort_values(["工厂", "指标", "品类", "日期"])


def apply_query_to_categories(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not query:
        return df
    return df[df["品类"].astype(str).str.contains(query, case=False, na=False, regex=False)]


def apply_query_to_sku(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not query:
        return df
    mask = pd.Series(False, index=df.index)
    for col in ["部位大类", "物料描述", "子类"]:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.contains(query, case=False, na=False, regex=False)
    return df[mask]


def yield_alert_rows(category_df: pd.DataFrame) -> pd.DataFrame:
    if category_df.empty:
        return pd.DataFrame()
    df = category_df.copy()
    df["金额权重"] = df["含税金额"].abs().map(lambda value: math.log1p(value))
    df["目标差"] = (TARGET_CATEGORY_YIELD - df["产成率"]).clip(lower=0)
    df["风险分"] = (df["目标差"] + 1) * df["金额权重"]
    return df.sort_values(["风险分", "含税金额"], ascending=[False, False])


def price_alert_rows(category_df: pd.DataFrame, reference_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if category_df.empty:
        return pd.DataFrame()
    df = category_df.copy()
    ref = reference_df if reference_df is not None and not reference_df.empty else df
    medians = ref.groupby("品类", observed=True)["含税单价"].median()
    overall_median = ref["含税单价"].median()
    df["参考单价"] = df["品类"].map(medians).fillna(overall_median)
    df["单价偏离"] = df["含税单价"] - df["参考单价"]
    df["偏离幅度"] = df["单价偏离"].abs()
    df["金额权重"] = df["含税金额"].abs().map(lambda value: math.log1p(value))
    df["风险分"] = df["偏离幅度"] * df["金额权重"]
    return df.sort_values(["风险分", "含税金额"], ascending=[False, False])


def build_daily_summary(factories: list[dict[str, Any]], category_df: pd.DataFrame, sku_df: pd.DataFrame) -> dict[str, Any]:
    low_yield_factory = min(factories, key=factory_yield) if factories else {}
    high_price_factory = max(factories, key=factory_price) if factories else {}
    low_price_factory = min(factories, key=factory_price) if factories else {}
    yield_alert = yield_alert_rows(category_df).head(1)
    price_alert = price_alert_rows(category_df).head(1)
    negative_sku = sku_df[(sku_df.get("含税金额", 0) < 0) | (sku_df.get("产量kg", 0) < 0)] if not sku_df.empty else pd.DataFrame()

    priority: list[str] = []
    if not yield_alert.empty:
        row = yield_alert.iloc[0]
        priority.append(f"产成率：优先看 {row['工厂']} 的 {row['品类']}，产成率 {row['产成率']:.2f}%，金额 {row['含税金额'] / 10000:.1f} 万元。")
    if not price_alert.empty:
        row = price_alert.iloc[0]
        direction = "高于" if row["单价偏离"] >= 0 else "低于"
        priority.append(f"单价：{row['工厂']} 的 {row['品类']} {direction}同品类参考 {abs(row['单价偏离']):.2f} 元/kg。")
    if not negative_sku.empty:
        priority.append(f"明细：Top SKU 中发现 {len(negative_sku)} 条负产量或负金额记录，需核对冲销或录入。")
    if not priority:
        priority.append("今日未发现明显的产成率、单价或负数异常，按常规复盘即可。")

    return {
        "low_yield_factory": low_yield_factory,
        "high_price_factory": high_price_factory,
        "low_price_factory": low_price_factory,
        "yield_alert": yield_alert,
        "price_alert": price_alert,
        "negative_sku": negative_sku,
        "priority": priority,
    }


def render_meta(report: dict[str, Any], factories: list[dict[str, Any]]) -> None:
    report_date = report.get("report_date", "-")
    generated = str(report.get("generated_at", "-")).replace("T", " ")
    factory_names = " / ".join(str(factory.get("factory", "-")) for factory in factories)
    st.markdown(
        f"""
        <div class="report-meta">
          <span class="pill">数据日期：{esc(report_date)}</span>
          <span class="pill">生成时间：{esc(generated)}</span>
          <span class="pill">工厂：{esc(factory_names)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summary_panel(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="summary-panel">
          <div class="summary-kicker">{esc(kicker)}</div>
          <div class="summary-title">{esc(title)}</div>
          <div class="summary-body">{esc(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_daily_summary(report: dict[str, Any], factories: list[dict[str, Any]], category_df: pd.DataFrame, sku_df: pd.DataFrame) -> None:
    summary = build_daily_summary(factories, category_df, sku_df)
    low = summary["low_yield_factory"]
    high_price = summary["high_price_factory"]
    low_price = summary["low_price_factory"]

    cols = st.columns([1, 1, 1.28])
    with cols[0]:
        risk_text = "低于目标，需优先复盘" if factory_yield(low) < TARGET_TOTAL_YIELD else "三厂均在目标附近或以上"
        summary_panel(
            "今日产成率结论",
            f"{low.get('factory', '-')} {pct(factory_yield(low), 2)}",
            f"总产成率目标 {TARGET_TOTAL_YIELD:.0f}%。{risk_text}，先看低产成率高金额品类。",
        )
    with cols[1]:
        summary_panel(
            "今日单价结论",
            f"{fmt(factory_price(low_price), 2)} - {fmt(factory_price(high_price), 2)} 元/kg",
            f"{high_price.get('factory', '-')} 最高，{low_price.get('factory', '-')} 最低；结合品类结构判断是否为结构性拉动。",
        )
    with cols[2]:
        items = "".join(f"<li>{esc(item)}</li>" for item in summary["priority"][:3])
        st.markdown(
            f"""
            <div class="summary-panel">
              <div class="summary-kicker">今日优先关注</div>
              <ul class="priority-list">{items}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def factory_badge(core: dict[str, Any]) -> str:
    total_yield = num(core.get("总产成率"))
    if total_yield < TARGET_TOTAL_YIELD:
        return '<span class="badge hot">产成率低</span>'
    return '<span class="badge good">产成率达标</span>'


def render_factory_cards(factories: list[dict[str, Any]]) -> None:
    cols = st.columns(3)
    for col, factory in zip(cols, factories):
        core = factory.get("daily_core", {})
        with col:
            st.markdown(
                f"""
                <div class="factory-card">
                  <div class="factory-head">
                    <div class="factory-name">{esc(factory.get("factory", "-"))}</div>
                    <div>{factory_badge(core)}</div>
                  </div>
                  <div class="metric-grid">
                    <div class="metric-cell">
                      <div class="metric-label">总产成率</div>
                      <div class="metric-value">{pct(core.get("总产成率"), 2)}</div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">总单价</div>
                      <div class="metric-value">{fmt(core.get("总产值"), 2)} <span class="metric-unit">元/kg</span></div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">主产品产成率</div>
                      <div class="metric-value">{pct(core.get("主产品产成率"), 2)}</div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">主产品单价</div>
                      <div class="metric-value">{fmt(core.get("主产品产值"), 2)} <span class="metric-unit">元/kg</span></div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">副产品产成率</div>
                      <div class="metric-value">{pct(core.get("副产品产成率"), 2)}</div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">副产品单价</div>
                      <div class="metric-value">{fmt(core.get("副产品产值"), 2)} <span class="metric-unit">元/kg</span></div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def core_metric_df(factories: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for factory in factories:
        core = factory.get("daily_core", {})
        rows.append(
            {
                "工厂": factory.get("factory"),
                "总产成率": num(core.get("总产成率")),
                "主产品产成率": num(core.get("主产品产成率")),
                "副产品产成率": num(core.get("副产品产成率")),
                "总单价": num(core.get("总产值")),
                "主产品单价": num(core.get("主产品产值")),
                "副产品单价": num(core.get("副产品产值")),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["工厂"] = pd.Categorical(df["工厂"], FACTORY_ORDER, ordered=True)
    return df


def render_yield_section(factories: list[dict[str, Any]], category_df: pd.DataFrame, trend_df: pd.DataFrame) -> None:
    core_df = core_metric_df(factories)
    if core_df.empty:
        st.info("暂无产成率数据。")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        chart_shell("哪个厂产成率最低？", "总产成率与主/副产品拆分")
        long_df = core_df.melt(id_vars="工厂", value_vars=["总产成率", "主产品产成率", "副产品产成率"], var_name="指标", value_name="产成率")
        fig = px.bar(
            long_df,
            x="工厂",
            y="产成率",
            color="指标",
            barmode="group",
            text=long_df["产成率"].map(lambda value: f"{value:.1f}%"),
            color_discrete_map={"总产成率": "#126c70", "主产品产成率": "#1f5fbf", "副产品产成率": "#d18a1f"},
        )
        fig.add_hline(y=TARGET_TOTAL_YIELD, line_dash="dash", line_color="#a6261b", annotation_text=f"总产成率目标 {TARGET_TOTAL_YIELD:.0f}%")
        fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), yaxis_title="产成率 %", xaxis_title="", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()
    with col2:
        chart_shell("哪些品类拉低产成率？", "按低产成率和金额权重排序")
        risk_df = yield_alert_rows(category_df).head(TOP_N).sort_values("风险分")
        if risk_df.empty:
            st.info("暂无品类产成率数据。")
        else:
            risk_df = risk_df.copy()
            risk_df["金额万元"] = risk_df["含税金额"] / 10000
            fig = px.bar(
                risk_df,
                x="产成率",
                y="品类",
                color="工厂",
                orientation="h",
                text=risk_df["产成率"].map(lambda value: f"{value:.1f}%"),
                color_discrete_map=FACTORY_COLORS,
                hover_data={"金额万元": ":.1f", "含税单价": ":.2f", "产销率": ":.1f"},
            )
            fig.add_vline(x=TARGET_CATEGORY_YIELD, line_dash="dash", line_color="#a6261b", annotation_text=f"参考 {TARGET_CATEGORY_YIELD:.0f}%")
            fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="产成率 %", yaxis_title="", plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()

    factory_names = [factory.get("factory") for factory in factories]
    yield_trend = trend_df[(trend_df["指标"] == "产成率") & (trend_df["品类"] == "总计") & (trend_df["工厂"].astype(str).isin(factory_names))] if not trend_df.empty else pd.DataFrame()
    if not yield_trend.empty:
        chart_shell("本月总产成率走势", "用趋势判断今天是否偏离近期水平")
        fig = px.line(
            yield_trend,
            x="日期",
            y="数值",
            color="工厂",
            markers=True,
            color_discrete_map=FACTORY_COLORS,
        )
        fig.add_hline(y=TARGET_TOTAL_YIELD, line_dash="dash", line_color="#a6261b", annotation_text=f"目标 {TARGET_TOTAL_YIELD:.0f}%")
        fig.update_layout(height=360, margin=dict(l=8, r=8, t=8, b=20), yaxis_title="产成率 %", xaxis_title="", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()


def render_price_section(factories: list[dict[str, Any]], category_df: pd.DataFrame, reference_category_df: pd.DataFrame, trend_df: pd.DataFrame) -> None:
    core_df = core_metric_df(factories)
    if core_df.empty:
        st.info("暂无单价数据。")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        chart_shell("哪个厂总单价最高？", "总单价与主/副产品单价拆分")
        long_df = core_df.melt(id_vars="工厂", value_vars=["总单价", "主产品单价", "副产品单价"], var_name="指标", value_name="单价")
        fig = px.bar(
            long_df,
            x="工厂",
            y="单价",
            color="指标",
            barmode="group",
            text=long_df["单价"].map(lambda value: f"{value:.2f}"),
            color_discrete_map={"总单价": "#126c70", "主产品单价": "#1f5fbf", "副产品单价": "#d18a1f"},
        )
        fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), yaxis_title="元/kg", xaxis_title="", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()
    with col2:
        chart_shell("哪些品类单价偏离最大？", "按同品类三厂参考中位值比较")
        risk_df = price_alert_rows(category_df, reference_category_df).head(TOP_N).sort_values("风险分")
        if risk_df.empty:
            st.info("暂无品类单价数据。")
        else:
            risk_df = risk_df.copy()
            risk_df["偏离方向"] = risk_df["单价偏离"].map(lambda value: "偏高" if value >= 0 else "偏低")
            fig = px.bar(
                risk_df,
                x="单价偏离",
                y="品类",
                color="偏离方向",
                orientation="h",
                text=risk_df["单价偏离"].map(lambda value: f"{value:+.2f}"),
                color_discrete_map={"偏高": "#b65a08", "偏低": "#1f5fbf"},
                hover_data={"工厂": True, "含税单价": ":.2f", "参考单价": ":.2f", "含税金额": ":,.0f"},
            )
            fig.add_vline(x=0, line_color="#64748b")
            fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="较同品类参考偏离（元/kg）", yaxis_title="", plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()

    col3, col4 = st.columns([1, 1])
    with col3:
        chart_shell("品类单价热力图", "颜色越深，单价越高")
        heat_df = category_df.pivot_table(index="工厂", columns="品类", values="含税单价", aggfunc="mean").reindex(FACTORY_ORDER)
        heat_df = heat_df.dropna(axis=0, how="all").dropna(axis=1, how="all")
        if heat_df.empty:
            st.info("暂无热力图数据。")
        else:
            fig = px.imshow(
                heat_df,
                aspect="auto",
                color_continuous_scale=["#f5f8fa", "#c9e2e6", "#63aeba", "#126c70"],
                text_auto=".2f",
            )
            fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), coloraxis_colorbar=dict(title="元/kg"), plot_bgcolor="#ffffff")
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()
    with col4:
        factory_names = [factory.get("factory") for factory in factories]
        price_trend = trend_df[(trend_df["指标"] == "含税单价") & (trend_df["品类"] == "总计") & (trend_df["工厂"].astype(str).isin(factory_names))] if not trend_df.empty else pd.DataFrame()
        chart_shell("本月总单价走势", "看今天单价是否偏离近期水平")
        if price_trend.empty:
            st.info("暂无单价趋势数据。")
        else:
            fig = px.line(
                price_trend,
                x="日期",
                y="数值",
                color="工厂",
                markers=True,
                color_discrete_map=FACTORY_COLORS,
            )
            fig.update_layout(height=420, margin=dict(l=8, r=8, t=8, b=20), yaxis_title="元/kg", xaxis_title="", plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()


def render_quadrant(category_df: pd.DataFrame) -> None:
    if category_df.empty:
        return
    plot_df = category_df[category_df["含税金额"] != 0].copy()
    if plot_df.empty:
        return
    plot_df["金额万元"] = plot_df["含税金额"] / 10000
    price_median = float(plot_df["含税单价"].median())
    chart_shell("产成率 × 单价诊断", "点越大金额越大，优先看低产成率且高金额的点")
    fig = px.scatter(
        plot_df,
        x="产成率",
        y="含税单价",
        size=plot_df["含税金额"].abs(),
        color="工厂",
        text="品类",
        color_discrete_map=FACTORY_COLORS,
        hover_data={"金额万元": ":.1f", "产量kg": ":,.0f", "销量kg": ":,.0f", "产销率": ":.1f"},
    )
    fig.add_vline(x=TARGET_CATEGORY_YIELD, line_dash="dash", line_color="#a6261b", annotation_text=f"产成率参考 {TARGET_CATEGORY_YIELD:.0f}%")
    fig.add_hline(y=price_median, line_dash="dot", line_color="#64748b", annotation_text=f"单价中位 {price_median:.2f}")
    fig.update_traces(textposition="top center", textfont=dict(size=10), marker=dict(line=dict(color="#ffffff", width=1)))
    fig.update_layout(height=480, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="产成率 %", yaxis_title="含税单价 元/kg", plot_bgcolor="#ffffff")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    close_shell()


def render_exception_section(category_df: pd.DataFrame, reference_category_df: pd.DataFrame, sku_df: pd.DataFrame, query: str) -> None:
    yield_risk = yield_alert_rows(category_df).head(TOP_N)
    price_risk = price_alert_rows(category_df, reference_category_df).head(TOP_N)
    filtered_sku = apply_query_to_sku(sku_df, query)
    negative_sku = filtered_sku[(filtered_sku.get("含税金额", 0) < 0) | (filtered_sku.get("产量kg", 0) < 0)] if not filtered_sku.empty else pd.DataFrame()

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("低产成率高金额品类", expanded=True):
            if yield_risk.empty:
                st.info("暂无产成率异常。")
            else:
                table = yield_risk[["工厂", "品类", "产成率", "含税金额", "含税单价", "产销率"]].copy()
                table["含税金额"] = table["含税金额"].round(0)
                st.dataframe(table, use_container_width=True, hide_index=True)
    with col2:
        with st.expander("单价偏离品类", expanded=True):
            if price_risk.empty:
                st.info("暂无单价偏离数据。")
            else:
                table = price_risk[["工厂", "品类", "含税单价", "参考单价", "单价偏离", "含税金额"]].copy()
                st.dataframe(table, use_container_width=True, hide_index=True)

    with st.expander("负产量 / 负金额 SKU", expanded=False):
        if negative_sku.empty:
            st.info("当前 Top SKU 明细中未发现负产量或负金额。")
        else:
            columns = [col for col in ["工厂", "日期", "部位大类", "子类", "物料描述", "产量kg", "含税金额", "含税单价"] if col in negative_sku.columns]
            st.dataframe(negative_sku[columns].sort_values("含税金额"), use_container_width=True, hide_index=True)


def main() -> None:
    st.title("PVM肉品产值日报")

    try:
        index = load_index()
        report = load_latest_report()
    except FileNotFoundError:
        st.error("没有找到日报数据。请先在上传工具中完成分析并同步。")
        return

    latest_date = index.get("latest_date") or report.get("report_date")
    if not latest_date:
        st.warning("暂无日报日期。")
        return

    factories = ordered_factories(report)
    if not factories:
        st.warning("当前日报没有可展示的工厂数据。")
        return

    render_meta(report, factories)

    control_cols = st.columns([1, 1.45])
    factory_labels = ["三厂对比", *[factory.get("factory", "-") for factory in factories]]
    with control_cols[0]:
        factory_label = st.selectbox("查看范围", factory_labels, index=0)
    with control_cols[1]:
        query = st.text_input("聚焦品类/SKU", placeholder="腿类、胸类、鸡爪、物料描述...")

    selected_factories = factories if factory_label == "三厂对比" else [factory for factory in factories if factory.get("factory") == factory_label]
    if not selected_factories:
        selected_factories = factories

    full_category_df = overview_rows(factories)
    selected_category_df = apply_query_to_categories(overview_rows(selected_factories), query)
    sku_df = all_sku_rows(factories)
    trend_df = trend_rows(factories)

    st.markdown("## 日报摘要")
    st.markdown('<div class="section-note">先看今天该优先复盘哪个厂、哪个品类、哪个异常。</div>', unsafe_allow_html=True)
    render_daily_summary(report, factories, full_category_df, sku_df)

    st.markdown("## 三厂核心对比")
    st.markdown('<div class="section-note">只保留产成率和单价相关指标，固定按蚌埠、大连、铁岭展示。</div>', unsafe_allow_html=True)
    render_factory_cards(factories)

    st.markdown("## 产成率专题")
    render_yield_section(selected_factories, selected_category_df, trend_df)

    st.markdown("## 单价专题")
    render_price_section(selected_factories, selected_category_df, full_category_df, trend_df)

    st.markdown("## 诊断图")
    render_quadrant(selected_category_df)

    st.markdown("## 异常明细")
    render_exception_section(selected_category_df, full_category_df, sku_df, query)


if __name__ == "__main__":
    main()
