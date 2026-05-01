"""
app.py
======
XPerformance Validator — Dash web interface.

Tabs:
  1. Overview   — KPI cards + return comparison table (PDF vs Calc)
  2. Assets     — per-asset return table with strategy filter
  3. Allocation — strategy donut + allocation bar chart

Run:
    python app.py
    open http://localhost:8050
"""

import json
import os
from datetime import date

import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ── Colour palette (Nexus dark) ───────────────────────────────────────────────
TEAL   = "#01696f"
RED    = "#a12c7b"
GOLD   = "#d19900"
GREEN  = "#437a22"
BG     = "#171614"
SURFACE= "#1c1b19"
BORDER = "#393836"
TEXT   = "#cdccca"
MUTED  = "#797876"

STRATEGY_COLORS = {
    "Pós Fixado":            TEAL,
    "Inflação":              GOLD,
    "Pré Fixado":            "#5591c7",
    "Multimercado":          "#a86fdf",
    "Renda Variável Brasil": "#6daa45",
    "Renda Variável Global": "#dd6974",
    "Alternativo":           "#fdab43",
    "Fundos Listados":       "#4f98a3",
}

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300..700&display=swap",
    ],
    title="XPerf Validator",
    suppress_callback_exceptions=True,
)
server = app.server

# ── Result cache ──────────────────────────────────────────────────────────────
_cache: dict = {}


def _get_cached(account_id: str):
    if account_id in _cache:
        return _cache[account_id]
    path = os.path.join(os.path.dirname(__file__), "output", f"results_{account_id}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            _cache[account_id] = json.load(f)
        return _cache[account_id]
    return None


def _run(account_id: str) -> dict:
    from calculators.portfolio import run_account_validation
    result = run_account_validation(account_id)
    _cache[account_id] = result
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "output", f"results_{account_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, default=lambda o: o.isoformat() if isinstance(o, date) else str(o),
                  indent=2, ensure_ascii=False)
    return result


# ── Formatting helpers ────────────────────────────────────────────────────────
def _p(v, d=4):
    return f"{v*100:.{d}f}%" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "\u2014"

def _bps(v):
    return f"{v:+.1f}" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "\u2014"

def _cdi(v):
    return f"{v:.2f}%" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "\u2014"

def _delta_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return {}
    return {"color": GREEN if v >= 0 else RED, "fontWeight": "600"}


# ── KPI card ──────────────────────────────────────────────────────────────────
def kpi_card(title, value, sub=None, badge=None):
    badge_el = html.Span() if badge is None else html.Span(
        badge,
        style={"fontSize": "0.72rem",
               "color": GREEN if (isinstance(badge, str) and "+" in badge) else RED,
               "marginLeft": "6px"}
    )
    return dbc.Card(dbc.CardBody([
        html.P(title,  className="text-uppercase text-muted mb-1",
               style={"fontSize": "0.68rem", "letterSpacing": "0.07em"}),
        html.H4([value, badge_el], className="mb-0",
                style={"fontVariantNumeric": "tabular-nums", "color": TEXT}),
        html.Small(sub or "", style={"color": MUTED, "fontSize": "0.75rem"}),
    ]), style={"background": SURFACE, "border": f"1px solid {BORDER}",
               "borderRadius": "8px"})


# ── Return table ──────────────────────────────────────────────────────────────
def return_table(result):
    windows = [("month", "Month"), ("ytd", "YTD"), ("12m", "12 M"), ("24m", "24 M")]
    rows = []
    for w, label in windows:
        pdf_r  = result["pdf_returns"].get(w)
        calc_r = result["calc_returns"].get(w)
        delta  = result["deltas"].get(w)
        pdf_c  = result["pdf_cdi_pct"].get(w)
        calc_c = result["calc_cdi_pct"].get(w)
        kpis   = result.get("kpis", {})
        cdi_acc = kpis.get(f"return_vs_cdi_{w}", {}).get("cdi_acc")
        rows.append(html.Tr([
            html.Td(label, style={"fontWeight": "600", "color": TEXT}),
            html.Td(_p(pdf_r),  style={"fontVariantNumeric": "tabular-nums"}),
            html.Td(_p(calc_r), style={"fontVariantNumeric": "tabular-nums"}),
            html.Td(_bps(delta), style=_delta_color(delta)),
            html.Td(_cdi(pdf_c)),
            html.Td(_cdi(calc_c)),
            html.Td(_p(cdi_acc)),
        ]))
    hdr = html.Thead(html.Tr([
        html.Th(c) for c in ["Window","PDF Return","Calc Return","Δ bps","PDF % CDI","Calc % CDI","CDI (period)"]
    ]), style={"borderBottom": f"2px solid {TEAL}", "color": MUTED,
               "fontSize": "0.72rem", "textTransform": "uppercase",
               "letterSpacing": "0.05em"})
    return dbc.Table([hdr, html.Tbody(rows)], bordered=False, hover=True,
                     size="sm", style={"color": TEXT})


# ── Charts ────────────────────────────────────────────────────────────────────
def donut_chart(result):
    seen = {}
    for a in result["asset_results"]:
        seen.setdefault(a["name"], a)
    df = pd.DataFrame(seen.values())
    grp = df.groupby("strategy")["gross_bal"].sum().reset_index().sort_values("gross_bal", ascending=False)
    fig = go.Figure(go.Pie(
        labels=grp["strategy"], values=grp["gross_bal"],
        hole=0.55,
        marker=dict(colors=[STRATEGY_COLORS.get(s, MUTED) for s in grp["strategy"]],
                    line=dict(color=BG, width=2)),
        textinfo="label+percent", textfont=dict(size=11, color=TEXT),
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=8, r=8, t=8, b=8), height=290,
                      font=dict(color=TEXT, family="DM Sans, sans-serif"))
    return fig


def bar_chart(result):
    seen = {}
    for a in result["asset_results"]:
        seen.setdefault(a["name"], a)
    df = pd.DataFrame(seen.values())
    grp = df.groupby("strategy")["alloc_pct"].sum().reset_index().sort_values("alloc_pct")
    fig = go.Figure(go.Bar(
        x=grp["alloc_pct"], y=grp["strategy"], orientation="h",
        marker_color=[STRATEGY_COLORS.get(s, MUTED) for s in grp["strategy"]],
        text=[f"{v:.1f}%" for v in grp["alloc_pct"]], textposition="outside",
        textfont=dict(size=11, color=TEXT),
        hovertemplate="<b>%{y}</b>: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, color=TEXT, tickfont=dict(size=11)),
        margin=dict(l=8, r=55, t=8, b=8),
        height=max(200, len(grp) * 33),
        font=dict(color=TEXT, family="DM Sans, sans-serif"),
    )
    return fig


def asset_df(result):
    seen = {}
    for a in result["asset_results"]:
        seen.setdefault(a["name"], a)
    rows = []
    for a in seen.values():
        rows.append({
            "Name":      a["name"],
            "Strategy":  a["strategy"],
            "Type":      a["asset_type"],
            "Bal (R$)":  f"{a['gross_bal']:,.0f}",
            "Alloc %":   f"{a['alloc_pct']:.2f}%",
            "M":   _p(a.get("calc_return_month"), 3),
            "YTD": _p(a.get("calc_return_ytd"),   3),
            "12M": _p(a.get("calc_return_12m"),   3),
            "24M": _p(a.get("calc_return_24m"),   3),
            "Status": a.get("status", "\u2014"),
        })
    return pd.DataFrame(rows)


# ── Layout ────────────────────────────────────────────────────────────────────
SIDEBAR = {
    "width": "210px", "minHeight": "100vh",
    "background": SURFACE, "borderRight": f"1px solid {BORDER}",
    "padding": "22px 14px", "flexShrink": "0",
}
MAIN = {
    "flex": "1", "padding": "26px 30px",
    "overflowY": "auto", "minHeight": "100vh", "background": BG,
}

app.layout = html.Div([
    # ── Sidebar ───────────────────────────────────────────────────────────────
    html.Div([
        # Logo
        html.Div([
            html.Svg([
                html.Rect(width="32", height="32", rx="6", **{"fill": TEAL}),
                html.Text("X", x="16", y="22",
                          **{"textAnchor": "middle", "fontSize": "18",
                             "fontWeight": "700", "fill": "white",
                             "fontFamily": "monospace"}),
            ], viewBox="0 0 32 32", width="32", height="32",
               style={"marginRight": "10px", "flexShrink": "0"}),
            html.Div([
                html.Div("XPerf",     style={"fontWeight": "700", "fontSize": "0.95rem",
                                              "color": TEXT, "lineHeight": "1.2"}),
                html.Div("Validator", style={"fontSize": "0.7rem", "color": MUTED}),
            ])
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "26px"}),

        html.P("Account", style={"fontSize": "0.68rem", "color": MUTED,
                                  "textTransform": "uppercase",
                                  "letterSpacing": "0.08em", "marginBottom": "6px"}),
        dcc.RadioItems(
            id="account-radio",
            options=[
                {"label": html.Span("76884",   style={"marginLeft": "6px"}), "value": "76884"},
                {"label": html.Span("5663735", style={"marginLeft": "6px"}), "value": "5663735"},
            ],
            value="76884",
            inputStyle={"accentColor": TEAL},
            labelStyle={"display": "flex", "alignItems": "center",
                        "marginBottom": "8px", "cursor": "pointer",
                        "fontSize": "0.88rem", "color": TEXT},
        ),

        html.Hr(style={"borderColor": BORDER, "margin": "18px 0"}),

        dbc.Button("\u25b6\u2002Run Validation", id="run-btn",
                   size="sm", className="w-100",
                   style={"background": TEAL, "borderColor": TEAL,
                          "fontWeight": "600", "letterSpacing": "0.03em"}),

        html.Div(id="run-status",
                 style={"marginTop": "10px", "fontSize": "0.72rem", "color": MUTED}),

        html.Hr(style={"borderColor": BORDER, "margin": "18px 0"}),

        html.P("View", style={"fontSize": "0.68rem", "color": MUTED,
                               "textTransform": "uppercase",
                               "letterSpacing": "0.08em", "marginBottom": "6px"}),
        dbc.Nav([
            dbc.NavLink("Overview",   href="#", id="nl-overview",
                        style={"color": TEXT, "fontSize": "0.88rem",
                               "padding": "5px 8px", "borderRadius": "6px"}),
            dbc.NavLink("Assets",     href="#", id="nl-assets",
                        style={"color": TEXT, "fontSize": "0.88rem",
                               "padding": "5px 8px", "borderRadius": "6px"}),
            dbc.NavLink("Allocation", href="#", id="nl-alloc",
                        style={"color": TEXT, "fontSize": "0.88rem",
                               "padding": "5px 8px", "borderRadius": "6px"}),
        ], vertical=True, pills=True),
    ], style=SIDEBAR),

    # ── Main ──────────────────────────────────────────────────────────────────
    html.Div([
        # Header row
        html.Div([
            html.Div([
                html.H5(id="pg-title", style={"margin": "0", "color": TEXT, "fontWeight": "600"}),
                html.Small(id="pg-sub",   style={"color": MUTED}),
            ]),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "marginBottom": "22px",
                  "paddingBottom": "14px", "borderBottom": f"1px solid {BORDER}"}),

        dbc.Tabs([
            dbc.Tab(label="Overview",   tab_id="tab-ov"),
            dbc.Tab(label="Assets",     tab_id="tab-as"),
            dbc.Tab(label="Allocation", tab_id="tab-al"),
        ], id="tabs", active_tab="tab-ov", className="border-0 mb-4"),

        html.Div(id="tab-content"),

    ], style=MAIN),

    dcc.Store(id="result-store"),

], style={"display": "flex",
          "fontFamily": "'DM Sans', 'Segoe UI', sans-serif",
          "background": BG, "color": TEXT})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("result-store", "data"),
    Output("run-status",   "children"),
    Input("run-btn",       "n_clicks"),
    State("account-radio", "value"),
    prevent_initial_call=False,
)
def load_or_run(n_clicks, account_id):
    existing = _get_cached(account_id)
    if existing and not n_clicks:
        return existing, "\u2713 Cached result loaded"
    if n_clicks:
        try:
            result = _run(account_id)
            return result, f"\u2713 Validated {account_id}"
        except Exception as e:
            return dash.no_update, f"\u2717 {str(e)[:55]}"
    return None, "Select account \u2192 Run Validation"


@app.callback(
    Output("pg-title", "children"),
    Output("pg-sub",   "children"),
    Input("account-radio", "value"),
    Input("result-store",  "data"),
)
def update_header(account_id, result):
    from config.assets import ACCOUNTS
    acc = ACCOUNTS.get(account_id, {})
    return (
        f"Account {account_id}",
        f"Ref: {acc.get('ref_date','')} | Patrimony: R$ {acc.get('total_patrimony',0):,.2f}",
    )


@app.callback(
    Output("tab-content", "children"),
    Input("tabs",          "active_tab"),
    Input("result-store",  "data"),
    State("account-radio", "value"),
)
def render_tab(tab, result, account_id):
    if result is None:
        return dbc.Alert(
            [html.Strong("No data. "), "Select an account and click \u25b6 Run Validation."],
            color="secondary",
            style={"background": SURFACE, "color": MUTED, "border": f"1px solid {BORDER}"},
        )
    if tab == "tab-ov":  return _overview(result)
    if tab == "tab-as":  return _assets(result)
    if tab == "tab-al":  return _allocation(result)
    return html.Div()


def _overview(result):
    kpis  = result.get("kpis", {})
    p     = result.get("total_patrimony", 0)
    c12   = result.get("calc_returns",  {}).get("12m")
    pdf12 = result.get("pdf_returns",   {}).get("12m")
    cdi12 = result.get("calc_cdi_pct",  {}).get("12m")
    d12   = result.get("deltas",        {}).get("12m")
    sh    = kpis.get("sharpe_12m",      float("nan"))
    dd12  = kpis.get("max_drawdown_12m",float("nan"))
    dd24  = kpis.get("max_drawdown_24m",float("nan"))

    d_str = (_bps(d12) + " bps") if d12 is not None else "\u2014"

    kpi_row = dbc.Row([
        dbc.Col(kpi_card("Patrimony",    f"R$ {p:,.0f}",   "Total gross balance"),    md=3),
        dbc.Col(kpi_card("Return 12M",   _p(c12, 2),      f"PDF: {_p(pdf12,2)}",   d_str), md=3),
        dbc.Col(kpi_card("% CDI 12M",    _cdi(cdi12),     "vs CDI accumulation"),   md=3),
        dbc.Col(kpi_card("Sharpe 12M",
                         f"{sh:.3f}" if not np.isnan(sh) else "\u2014",
                         "B3-listed assets"), md=3),
    ], className="mb-4 g-3")

    def dd_block(label, val):
        return html.Div([
            html.Div(label, style={"fontSize": "0.68rem", "color": MUTED,
                                   "textTransform": "uppercase",
                                   "letterSpacing": "0.06em"}),
            html.Div(
                f"{val*100:.2f}%" if not np.isnan(val) else "\u2014",
                style={"fontSize": "1.5rem", "fontWeight": "700",
                       "color": RED if not np.isnan(val) else MUTED,
                       "fontVariantNumeric": "tabular-nums", "marginBottom": "14px"}
            ),
        ])

    return html.Div([
        kpi_row,
        dbc.Row([
            dbc.Col([
                html.P("Return vs PDF by Period",
                       className="text-uppercase text-muted mb-2",
                       style={"fontSize": "0.68rem", "letterSpacing": "0.06em"}),
                return_table(result),
            ], md=8),
            dbc.Col([
                html.P("Max Drawdown",
                       className="text-uppercase text-muted mb-2",
                       style={"fontSize": "0.68rem", "letterSpacing": "0.06em"}),
                dbc.Card(dbc.CardBody([
                    dd_block("12 M", dd12),
                    dd_block("24 M", dd24),
                    html.Hr(style={"borderColor": BORDER}),
                    html.Small("Based on B3-listed assets only",
                               style={"color": MUTED, "fontSize": "0.7rem"}),
                ]), style={"background": SURFACE, "border": f"1px solid {BORDER}",
                           "borderRadius": "8px"}),
            ], md=4),
        ], className="g-3"),
    ])


def _assets(result):
    df = asset_df(result)
    if df.empty:
        return dbc.Alert("No asset data.", color="secondary")

    strategies = [{"label": "All strategies", "value": "all"}] + [
        {"label": s, "value": s} for s in sorted(df["Strategy"].unique())
    ]

    return html.Div([
        dbc.Row([dbc.Col(
            dcc.Dropdown(
                id="strat-filter",
                options=strategies, value="all", clearable=False,
                style={"fontSize": "0.875rem"},
            ), md=4
        )], className="mb-3"),
        dash_table.DataTable(
            id="asset-tbl",
            data=df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
            page_size=25,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": SURFACE, "color": MUTED,
                "fontWeight": "600", "fontSize": "0.7rem",
                "textTransform": "uppercase", "letterSpacing": "0.05em",
                "border": f"1px solid {BORDER}",
            },
            style_cell={
                "backgroundColor": BG, "color": TEXT,
                "border": f"1px solid {BORDER}",
                "fontSize": "0.84rem", "padding": "7px 10px",
                "fontFamily": "DM Sans, sans-serif",
                "fontVariantNumeric": "tabular-nums",
                "maxWidth": "250px", "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            style_data_conditional=[
                {"if": {"column_id": "Status", "filter_query": '{Status} = "ok"'},
                 "color": GREEN},
                {"if": {"column_id": "Status", "filter_query": '{Status} = "unavailable"'},
                 "color": RED},
            ],
        ),
    ])


@app.callback(
    Output("asset-tbl", "data"),
    Input("strat-filter",  "value"),
    State("result-store",  "data"),
    prevent_initial_call=True,
)
def filter_assets(strat, result):
    if not result:
        return []
    df = asset_df(result)
    if strat and strat != "all":
        df = df[df["Strategy"] == strat]
    return df.to_dict("records")


def _allocation(result):
    return html.Div(dbc.Row([
        dbc.Col([
            html.P("Allocation by Strategy",
                   className="text-uppercase text-muted mb-2",
                   style={"fontSize": "0.68rem", "letterSpacing": "0.06em"}),
            dcc.Graph(figure=donut_chart(result),
                      config={"displayModeBar": False}),
        ], md=5),
        dbc.Col([
            html.P("Allocation % by Strategy",
                   className="text-uppercase text-muted mb-2",
                   style={"fontSize": "0.68rem", "letterSpacing": "0.06em"}),
            dcc.Graph(figure=bar_chart(result),
                      config={"displayModeBar": False}),
        ], md=7),
    ], className="g-3"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
