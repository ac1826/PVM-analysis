from __future__ import annotations

import html
import json
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
NEUTRAL = "#475569"
TARGET_TOTAL_YIELD = 93.0
TARGET_CATEGORY_YIELD = 20.0
TOP_N = 8


st.set_page_config(
    page_title="PVM肉品产值分析报表",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f4f7fb; color: #122033; }
    .block-container { padding-top: 1.2rem; max-width: 1540px; }
    h1, h2, h3 { color: #0b1f35; letter-spacing: 0; }
    h1 { font-size: 2.35rem; margin-bottom: .25rem; }
    h2 { margin-top: 1.35rem; }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label { color: #334155; font-weight: 700; }
    div[data-testid="stMetric"] {
      background: #fff;
      border: 1px solid #d9e3ef;
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 8px 22px rgba(15,23,42,.045);
    }
    .section-note {
      color: #64748b;
      font-size: 14px;
      margin: -6px 0 14px;
    }
    .meta-row {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin: 0 0 18px;
    }
    .meta-pill {
      border: 1px solid #d8e2ef;
      background: #fff;
      border-radius: 999px;
      color: #475569;
      padding: 6px 11px;
      font-size: 13px;
      line-height: 1.2;
    }
    .diagnosis-card,
    .factory-card {
      background: #fff;
      border: 1px solid #d9e3ef;
      border-radius: 8px;
      box-shadow: 0 8px 22px rgba(15,23,42,.045);
    }
    .diagnosis-card {
      min-height: 118px;
      padding: 14px 15px;
    }
    .diagnosis-card.risk {
      background: #fff9ed;
      border-color: #efcf8d;
    }
    .diag-label {
      color: #64748b;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .diag-value {
      color: #0b1f35;
      font-size: 22px;
      font-weight: 850;
      line-height: 1.22;
    }
    .diag-detail {
      color: #475569;
      font-size: 13px;
      margin-top: 8px;
      line-height: 1.45;
    }
    .factory-card {
      padding: 16px;
      min-height: 250px;
    }
    .factory-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }
    .factory-name {
      color: #0b1f35;
      font-size: 24px;
      font-weight: 900;
      line-height: 1.1;
    }
    .factory-status {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .badge {
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 750;
      line-height: 1.1;
      white-space: nowrap;
    }
    .badge.good { background: #e9f7ef; color: #136c3a; }
    .badge.warn { background: #fff2d8; color: #9a4f05; }
    .badge.hot { background: #feeceb; color: #a6261b; }
    .metric-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 8px;
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
      font-size: 24px;
      font-weight: 850;
      line-height: 1.15;
    }
    .metric-unit {
      font-size: 16px;
      font-weight: 750;
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
    .chart-title strong {
      color: #0b1f35;
      font-size: 19px;
    }
    .chart-title span {
      color: #64748b;
      font-size: 13px;
    }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    @media (max-width: 900px) {
      h1 { font-size: 1.9rem; }
      .metric-grid { grid-template-columns: 1fr; }
      .factory-name { font-size: 21px; }
      .diag-value { font-size: 20px; }
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


def ordered_factories(report: dict[str, Any]) -> list[dict[str, Any]]:
    factories = report.get("factories", [])
    order = {name: idx for idx, name in enumerate(FACTORY_ORDER)}
    return sorted(factories, key=lambda f: order.get(f.get("factory", ""), 99))


def factory_yield(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产成率"))


def factory_price(factory: dict[str, Any]) -> float:
    return num(factory.get("daily_core", {}).get("总产值"))


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
    if not df.empty:
        df["工厂"] = pd.Categorical(df["工厂"], FACTORY_ORDER, ordered=True)
        df = df.sort_values(["工厂", "含税金额"], ascending=[True, False])
    return df


def sku_rows(factory: dict[str, Any], key: str = "top_amount") -> pd.DataFrame:
    rows = factory.get("sku", {}).get(key, [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    rename_map = {
        "产量(kg)": "产量kg",
        "含税金额": "含税金额",
        "含税单价": "含税单价",
        "部位大类": "部位大类",
        "物料描述": "物料描述",
        "子类": "子类",
        "日期": "日期",
    }
    df = df.rename(columns=rename_map)
    for col in ["产量kg", "含税金额", "含税单价"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["工厂"] = factory.get("factory")
    return df


def all_sku_rows(factories: list[dict[str, Any]]) -> pd.DataFrame:
    frames = []
    for factory in factories:
        frames.extend([sku_rows(factory, "top_amount"), sku_rows(factory, "top_volume")])
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    dedupe_cols = [col for col in ["工厂", "日期", "子类", "物料描述", "产量kg", "含税金额"] if col in df.columns]
    return df.drop_duplicates(subset=dedupe_cols)


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


def diagnosis_card(label: str, value: str, detail: str, risk: bool = False) -> None:
    klass = "diagnosis-card risk" if risk else "diagnosis-card"
    st.markdown(
        f"""
        <div class="{klass}">
          <div class="diag-label">{esc(label)}</div>
          <div class="diag-value">{esc(value)}</div>
          <div class="diag-detail">{esc(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta(report: dict[str, Any], factories: list[dict[str, Any]]) -> None:
    report_date = report.get("report_date", "-")
    generated = str(report.get("generated_at", "-")).replace("T", " ")
    factory_names = " / ".join([str(factory.get("factory", "-")) for factory in factories])
    st.markdown(
        f"""
        <div class="meta-row">
          <span class="meta-pill">数据日期：{esc(report_date)}</span>
          <span class="meta-pill">生成时间：{esc(generated)}</span>
          <span class="meta-pill">工厂：{esc(factory_names)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_diagnosis(factories: list[dict[str, Any]], category_df: pd.DataFrame, sku_df: pd.DataFrame) -> None:
    low_yield_factory = min(factories, key=factory_yield) if factories else {}
    high_price_factory = max(factories, key=factory_price) if factories else {}
    low_price_factory = min(factories, key=factory_price) if factories else {}
    weak_category = category_df.sort_values(["产成率", "含税金额"], ascending=[True, False]).head(1)
    top_category = category_df.sort_values("含税金额", ascending=False).head(1)
    abnormal_sku = sku_df[(sku_df.get("含税金额", 0) < 0) | (sku_df.get("产量kg", 0) < 0)] if not sku_df.empty else pd.DataFrame()

    cols = st.columns(5)
    with cols[0]:
        diagnosis_card(
            "产成率优先看",
            f"{low_yield_factory.get('factory', '-')} {pct(factory_yield(low_yield_factory), 2)}",
            f"目标 {TARGET_TOTAL_YIELD:.0f}%，先看低于目标或最接近目标线的厂。",
            factory_yield(low_yield_factory) < TARGET_TOTAL_YIELD,
        )
    with cols[1]:
        diagnosis_card(
            "总单价区间",
            f"{fmt(factory_price(low_price_factory), 2)} - {fmt(factory_price(high_price_factory), 2)} 元/kg",
            f"{high_price_factory.get('factory', '-')} 最高，{low_price_factory.get('factory', '-')} 最低。",
        )
    with cols[2]:
        if not top_category.empty:
            row = top_category.iloc[0]
            diagnosis_card(
                "金额贡献最大",
                f"{row['工厂']} · {row['品类']}",
                f"含税金额 {fmt(row['含税金额'] / 10000, 1)} 万元，结构变化会影响总单价。",
            )
        else:
            diagnosis_card("金额贡献最大", "-", "暂无品类数据。")
    with cols[3]:
        if not weak_category.empty:
            row = weak_category.iloc[0]
            diagnosis_card(
                "低产成率品类",
                f"{row['工厂']} · {row['品类']}",
                f"产成率 {pct(row['产成率'], 2)}，结合金额判断是否优先复盘。",
                True,
            )
        else:
            diagnosis_card("低产成率品类", "-", "暂无品类数据。", True)
    with cols[4]:
        if not abnormal_sku.empty:
            row = abnormal_sku.sort_values("含税金额").iloc[0]
            diagnosis_card(
                "SKU 异常",
                f"{row.get('工厂', '-')} · {row.get('部位大类', '-')}",
                f"{row.get('物料描述', '-')[:18]}，金额 {fmt(row.get('含税金额'), 0)} 元。",
                True,
            )
        else:
            diagnosis_card("SKU 异常", "未发现负数项", "当前 Top 明细中未看到负金额或负产量。")


def status_badges(core: dict[str, Any], median_price: float) -> str:
    badges = []
    total_yield = num(core.get("总产成率"))
    total_price = num(core.get("总产值"))
    sales_rate = num(core.get("产销率"))
    if total_yield < TARGET_TOTAL_YIELD:
        badges.append(('<span class="badge hot">产成率低</span>'))
    else:
        badges.append(('<span class="badge good">产成率达标</span>'))
    if median_price and abs(total_price - median_price) >= 0.3:
        badges.append(('<span class="badge warn">单价偏离</span>'))
    if sales_rate >= 120 or (sales_rate and sales_rate <= 85):
        badges.append(('<span class="badge warn">产销率异常</span>'))
    return "".join(badges)


def render_factory_cards(factories: list[dict[str, Any]]) -> None:
    prices = [factory_price(factory) for factory in factories if factory_price(factory)]
    median_price = float(pd.Series(prices).median()) if prices else 0.0
    cols = st.columns(3)
    for col, factory in zip(cols, factories):
        core = factory.get("daily_core", {})
        name = factory.get("factory", "-")
        with col:
            st.markdown(
                f"""
                <div class="factory-card">
                  <div class="factory-top">
                    <div class="factory-name">{esc(name)}</div>
                    <div class="factory-status">{status_badges(core, median_price)}</div>
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
                      <div class="metric-label">产销率</div>
                      <div class="metric-value">{pct(core.get("产销率"), 2)}</div>
                    </div>
                    <div class="metric-cell">
                      <div class="metric-label">均重</div>
                      <div class="metric-value">{fmt(core.get("均重"), 2)} <span class="metric-unit">kg</span></div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_factory_comparison(factories: list[dict[str, Any]]) -> None:
    rows = []
    for factory in factories:
        core = factory.get("daily_core", {})
        rows.append(
            {
                "工厂": factory.get("factory"),
                "总产成率": num(core.get("总产成率")),
                "总单价": num(core.get("总产值")),
                "产销率": num(core.get("产销率")),
                "屠宰加工产量吨": num(core.get("屠宰加工产量")),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("暂无三厂核心指标。")
        return

    chart_shell("三厂产成率与总单价", "柱为产成率，线为总单价；虚线为总产成率目标")
    fig = go.Figure()
    fig.add_bar(
        x=df["工厂"],
        y=df["总产成率"],
        name="总产成率",
        marker_color=[FACTORY_COLORS.get(factory, NEUTRAL) for factory in df["工厂"]],
        text=df["总产成率"].map(lambda x: f"{x:.2f}%"),
        textposition="outside",
        hovertemplate="%{x}<br>总产成率 %{y:.2f}%<extra></extra>",
    )
    fig.add_scatter(
        x=df["工厂"],
        y=df["总单价"],
        name="总单价",
        yaxis="y2",
        mode="lines+markers+text",
        line=dict(color="#9a4f05", width=3),
        marker=dict(size=10, color="#9a4f05"),
        text=df["总单价"].map(lambda x: f"{x:.2f}"),
        textposition="top center",
        hovertemplate="%{x}<br>总单价 %{y:.2f} 元/kg<extra></extra>",
    )
    fig.add_hline(
        y=TARGET_TOTAL_YIELD,
        line_dash="dash",
        line_color="#a6261b",
        annotation_text=f"目标 {TARGET_TOTAL_YIELD:.0f}%",
        annotation_position="bottom right",
    )
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=20, t=32, b=18),
        yaxis=dict(title="总产成率 %", range=[max(0, min(df["总产成率"].min() - 2, TARGET_TOTAL_YIELD - 3)), max(df["总产成率"].max() + 2, TARGET_TOTAL_YIELD + 3)]),
        yaxis2=dict(title="总单价 元/kg", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    close_shell()


def render_category_structure(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("暂无品类数据。")
        return

    amount_df = df[df["含税金额"] > 0].copy()
    amount_df["工厂"] = amount_df["工厂"].astype(str)
    amount_df["金额万元"] = amount_df["含税金额"] / 10000

    col1, col2 = st.columns([1.05, 1])
    with col1:
        chart_shell("品类金额结构", "面积代表含税金额贡献")
        fig = px.treemap(
            amount_df,
            path=["工厂", "品类"],
            values="含税金额",
            color="工厂",
            color_discrete_map=FACTORY_COLORS,
            hover_data={"金额万元": ":.1f", "含税单价": ":.2f", "产成率": ":.2f"},
        )
        fig.update_traces(textinfo="label+percent parent", marker=dict(line=dict(color="#ffffff", width=2)))
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=8, b=0), paper_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()
    with col2:
        chart_shell("金额贡献 Top 8", "看哪些品类最影响总单价")
        top_df = amount_df.sort_values("含税金额", ascending=False).head(TOP_N).sort_values("含税金额")
        fig = px.bar(
            top_df,
            x="金额万元",
            y="品类",
            color="工厂",
            orientation="h",
            text=top_df["金额万元"].map(lambda x: f"{x:.1f}"),
            color_discrete_map=FACTORY_COLORS,
            hover_data={"产成率": ":.2f", "含税单价": ":.2f"},
        )
        fig.update_layout(height=520, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="含税金额（万元）", yaxis_title="", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()


def render_yield_price_diagnostics(df: pd.DataFrame) -> None:
    if df.empty:
        return

    plot_df = df[df["含税金额"] != 0].copy()
    if plot_df.empty:
        return
    plot_df["工厂"] = plot_df["工厂"].astype(str)
    plot_df["金额万元"] = plot_df["含税金额"] / 10000
    price_median = float(plot_df["含税单价"].median()) if not plot_df.empty else 0

    col1, col2 = st.columns([1.2, 1])
    with col1:
        chart_shell("产成率 × 单价象限", "点越大代表金额越大，优先看左侧且金额大的点")
        fig = px.scatter(
            plot_df,
            x="产成率",
            y="含税单价",
            size=plot_df["含税金额"].abs(),
            color="工厂",
            text="品类",
            color_discrete_map=FACTORY_COLORS,
            hover_data={
                "品类": True,
                "含税金额": ":,.0f",
                "产量kg": ":,.0f",
                "销量kg": ":,.0f",
                "产销率": ":.2f",
            },
        )
        fig.add_vline(x=TARGET_CATEGORY_YIELD, line_dash="dash", line_color="#a6261b", annotation_text=f"产成率参考 {TARGET_CATEGORY_YIELD:.0f}%")
        fig.add_hline(y=price_median, line_dash="dot", line_color="#64748b", annotation_text=f"单价中位 {price_median:.2f}")
        fig.update_traces(textposition="top center", textfont=dict(size=10), marker=dict(line=dict(color="#ffffff", width=1)))
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=8, b=20), xaxis_title="产成率 %", yaxis_title="含税单价 元/kg", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()
    with col2:
        chart_shell("品类单价热力图", "颜色越深，单价越高")
        heat_df = plot_df.pivot_table(index="工厂", columns="品类", values="含税单价", aggfunc="mean").reindex(FACTORY_ORDER)
        heat_df = heat_df.dropna(axis=0, how="all").dropna(axis=1, how="all")
        fig = px.imshow(
            heat_df,
            aspect="auto",
            color_continuous_scale=["#f1f7f9", "#bddce2", "#5ba6b1", "#0f5f68"],
            text_auto=".2f",
        )
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=8, b=20), coloraxis_colorbar=dict(title="元/kg"), plot_bgcolor="#ffffff")
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        close_shell()


def render_sku_detail(factories: list[dict[str, Any]], factory_label: str, query: str) -> None:
    selected = factories if factory_label == "三厂对比" else [factory for factory in factories if factory.get("factory") == factory_label]
    amount_df = pd.concat([sku_rows(factory, "top_amount") for factory in selected if not sku_rows(factory, "top_amount").empty], ignore_index=True) if selected else pd.DataFrame()
    volume_df = pd.concat([sku_rows(factory, "top_volume") for factory in selected if not sku_rows(factory, "top_volume").empty], ignore_index=True) if selected else pd.DataFrame()
    amount_df = apply_query_to_sku(amount_df, query)
    volume_df = apply_query_to_sku(volume_df, query)

    if amount_df.empty and volume_df.empty:
        st.info("暂无 SKU 明细。")
        return

    col1, col2 = st.columns(2)
    with col1:
        if not amount_df.empty:
            chart_shell("SKU 金额 Top 8", "按含税金额排序")
            top_amount = amount_df.sort_values("含税金额", ascending=False).head(TOP_N).sort_values("含税金额")
            fig = px.bar(
                top_amount,
                x="含税金额",
                y="物料描述",
                color="工厂",
                orientation="h",
                color_discrete_map=FACTORY_COLORS,
                hover_data={"部位大类": True, "含税单价": ":.2f", "产量kg": ":,.0f"},
            )
            fig.update_layout(height=500, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="含税金额（元）", yaxis_title="", yaxis=dict(tickfont=dict(size=11)), plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            close_shell()
    with col2:
        if not volume_df.empty:
            chart_shell("SKU 产量 Top 8", "按产量排序")
            top_volume = volume_df.sort_values("产量kg", ascending=False).head(TOP_N).sort_values("产量kg")
            fig = px.bar(
                top_volume,
                x="产量kg",
                y="物料描述",
                color="工厂",
                orientation="h",
                color_discrete_map=FACTORY_COLORS,
                hover_data={"部位大类": True, "含税单价": ":.2f", "含税金额": ":,.0f"},
            )
            fig.update_layout(height=500, margin=dict(l=8, r=8, t=8, b=20), xaxis_title="产量（kg）", yaxis_title="", yaxis=dict(tickfont=dict(size=11)), plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            close_shell()

    detail_df = all_sku_rows(selected)
    detail_df = apply_query_to_sku(detail_df, query)
    if not detail_df.empty:
        columns = [col for col in ["工厂", "日期", "部位大类", "子类", "物料描述", "产量kg", "含税金额", "含税单价"] if col in detail_df.columns]
        with st.expander("查看 SKU 明细表", expanded=False):
            st.dataframe(
                detail_df[columns].sort_values("含税金额", ascending=False),
                use_container_width=True,
                hide_index=True,
            )


def render_category_detail(df: pd.DataFrame) -> None:
    if df.empty:
        return
    with st.expander("查看品类明细表", expanded=False):
        table = df[["工厂", "品类", "产量kg", "销量kg", "产成率", "含税金额", "含税单价", "产销率"]].copy()
        table = table.sort_values(["工厂", "含税金额"], ascending=[True, False])
        st.dataframe(table, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("PVM肉品产值分析报表")

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

    st.markdown("## 今日诊断")
    st.markdown('<div class="section-note">先判断今天该优先看哪个厂、哪个品类、哪个 SKU。</div>', unsafe_allow_html=True)
    render_diagnosis(factories, full_category_df, sku_df)

    st.markdown("## 三厂核心")
    st.markdown('<div class="section-note">固定按蚌埠、大连、铁岭展示，重点看产成率和单价。</div>', unsafe_allow_html=True)
    render_factory_cards(factories)

    st.markdown("## 三厂对比")
    render_factory_comparison(factories)

    st.markdown("## 品类结构")
    st.markdown('<div class="section-note">选厂或搜索后，下方品类结构会跟随变化。</div>', unsafe_allow_html=True)
    render_category_structure(selected_category_df)

    st.markdown("## 产成率与单价诊断")
    render_yield_price_diagnostics(selected_category_df)

    st.markdown("## SKU 下钻")
    render_sku_detail(factories, factory_label, query)
    render_category_detail(selected_category_df)


if __name__ == "__main__":
    main()
