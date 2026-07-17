import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import re

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IKXO — Suivi Comptes Stratégiques",
    page_icon="👩‍🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
DATABASE_ID = "38aa848e427480b5bf7dc905f72ada04"

PIPELINE_STAGES = ['A qualifier','Prospection lancée','1 rdv','Plusieurs rdv','Besoin','Soutenance','Client']
SIDE_STAGES     = ['Réponses négatives','Freeze']

ETAT_CFG = {
    'A qualifier':        {'color':'#9CA3AF','bg':'#F9FAFB'},
    'Prospection lancée': {'color':'#3B82F6','bg':'#EFF6FF'},
    '1 rdv':              {'color':'#F97316','bg':'#FFF7ED'},
    'Plusieurs rdv':      {'color':'#8B5CF6','bg':'#F5F3FF'},
    'Besoin':             {'color':'#CA8A04','bg':'#FEFCE8'},
    'Soutenance':         {'color':'#16A34A','bg':'#F0FDF4'},
    'Client':             {'color':'#059669','bg':'#ECFDF5'},
    'Réponses négatives': {'color':'#EF4444','bg':'#FEF2F2'},
    'Freeze':             {'color':'#94A3B8','bg':'#F8FAFC'},
}

RC_COLORS = {'Alex':'#3B82F6','Clarisse':'#EC4899','Auré':'#10B981','Jerem':'#8B5CF6'}
MONTHS    = ['Juin 26','Juillet 26','Août 26','Septembre 26','Octobre 26']

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f4f8; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1rem !important; }

.badge {
    display:inline-block; padding:2px 8px; border-radius:9999px;
    font-size:11px; font-weight:600; white-space:nowrap;
}
.account-card {
    background:white; border:1px solid #e8eef8; border-radius:8px;
    padding:9px 10px; margin-bottom:5px; font-size:12px;
    transition: box-shadow .15s;
}
.account-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.08); }

div[data-testid="metric-container"] {
    background:white; border:1px solid #e5e7eb; border-radius:12px;
    padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.05);
}

.stTabs [data-baseweb="tab-list"] {
    gap:0; background:#1D3461;
    padding:0 8px; border-radius:10px 10px 0 0;
}
.stTabs [data-baseweb="tab"] {
    background:transparent; color:rgba(255,255,255,.65);
    border-radius:0; padding:10px 18px; font-size:13px;
    border-bottom:2px solid transparent;
}
.stTabs [aria-selected="true"] {
    background:transparent !important; color:white !important;
    font-weight:700; border-bottom:2px solid white !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background:white; border-radius:0 0 10px 10px;
    padding:20px; box-shadow:0 2px 10px rgba(0,0,0,.06);
}

div[data-testid="stExpander"] {
    border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; margin-bottom:8px;
}
</style>
""", unsafe_allow_html=True)

# ── NOTION DATA ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Chargement depuis Notion...")
def fetch_accounts():
    if "NOTION_API_KEY" not in st.secrets:
        st.error("🔑 NOTION_API_KEY manquante — configure-la dans les secrets Streamlit.")
        st.stop()
    api_key = st.secrets["NOTION_API_KEY"]

    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json=body, timeout=20
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    rows = []
    for page in results:
        p = page["properties"]
        titles = p.get("Comptes", {}).get("title", [])
        nom = titles[0].get("plain_text", "") if titles else ""
        if not nom:
            continue
        rows.append({
            "id":           page["id"],
            "url":          page["url"],
            "nom":          nom,
            "rc":           (p.get("RC",{}).get("select") or {}).get("name","") or "",
            "secteur":      (p.get("Secteur",{}).get("select") or {}).get("name","") or "Non défini",
            "etat":         (p.get("Etat",{}).get("select") or {}).get("name","") or "A qualifier",
            "typologie":    (p.get("Typologie",{}).get("select") or {}).get("name","") or "",
            "date_attaque": (p.get("Date d'attaque ",{}).get("select") or {}).get("name","") or "",
            "potentiel":    p.get("Potentiel business",{}).get("number"),
            "accessibilite":p.get("Accessibilité",{}).get("number"),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def etat_badge(etat):
    c = ETAT_CFG.get(etat, {"color":"#6B7280","bg":"#F3F4F6"})
    return f'<span class="badge" style="background:{c["bg"]};color:{c["color"]}">{etat}</span>'

def rc_span(rc):
    color = RC_COLORS.get(rc, '#9CA3AF')
    return f'<span style="color:{color};font-weight:700;font-size:12px">{rc}</span>'

def pot_bar_html(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    pct = int((val / 5) * 100)
    return (f'<div style="display:flex;align-items:center;gap:5px">'
            f'<div style="width:52px;height:5px;background:#e5e7eb;border-radius:3px">'
            f'<div style="width:{pct}%;height:5px;background:#1D3461;border-radius:3px"></div>'
            f'</div><span style="font-size:10px;color:#9ca3af">{int(val)}/5</span></div>')

def render_html(html):
    """Render HTML safely — strips leading whitespace per line to avoid Markdown code-block treatment."""
    st.markdown(re.sub(r'\n[ \t]+', '\n', html).strip(), unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
h1, h2, h3 = st.columns([1, 7, 1])
with h1:
    st.markdown(
        '<div style="padding-top:8px">'
        '<span style="font-size:24px;font-weight:900;color:#1D3461;letter-spacing:-1px">'
        'IK<span style="color:#3B82F6">X</span>O'
        '</span></div>',
        unsafe_allow_html=True
    )
with h2:
    st.markdown("## 👩‍🚀 Suivi Comptes Stratégiques")
with h3:
    st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
try:
    df = fetch_accounts()
except Exception as e:
    st.error(f"Erreur Notion API : {e}")
    st.stop()

if df.empty:
    st.warning("Aucun compte chargé. Vérifiez la connexion de l'intégration Notion.")
    st.stop()

st.caption(f"✅ **{len(df)} comptes** chargés · mis à jour à {pd.Timestamp.now().strftime('%H:%M')}")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_ov, tab_pipe, tab_plan, tab_mat, tab_all = st.tabs([
    "📊 Vue générale",
    "🔄 Pipeline",
    "📅 Planning",
    "🎯 Matrice",
    "📋 Tous les comptes"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VUE GÉNÉRALE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ov:
    total   = len(df)
    clients = (df.etat == 'Client').sum()
    en_cours= df.etat.isin(['1 rdv','Plusieurs rdv','Besoin','Soutenance']).sum()
    strat   = (df.typologie == 'Stratégique').sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏢 Total comptes", int(total))
    c2.metric("⭐ Stratégiques",  int(strat))
    c3.metric("🔥 En closing",    int(en_cours))
    c4.metric("✅ Clients",        int(clients))

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**🔄 Répartition par étape**")
        stage_data = [
            {"Étape": s, "n": int((df.etat == s).sum()),
             "color": ETAT_CFG.get(s, {}).get("color","#9CA3AF")}
            for s in PIPELINE_STAGES + SIDE_STAGES
        ]
        sdf = pd.DataFrame(stage_data)
        fig_s = go.Figure(go.Bar(
            x=sdf["n"], y=sdf["Étape"], orientation='h',
            marker_color=sdf["color"],
            text=sdf["n"], textposition='outside',
        ))
        fig_s.update_layout(
            margin=dict(l=0,r=40,t=10,b=10), height=310,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False,showticklabels=False),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_s, use_container_width=True)

    with col_r:
        st.markdown("**👤 Par responsable commercial**")
        for rc, color in RC_COLORS.items():
            rc_df = df[df.rc == rc]
            if rc_df.empty:
                continue
            n      = len(rc_df)
            en_c   = rc_df.etat.isin(['1 rdv','Plusieurs rdv','Besoin','Soutenance']).sum()
            cli    = (rc_df.etat=='Client').sum()
            pct    = int(n/total*100)
            st.markdown(f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                <span style="font-weight:700;color:{color}">{rc}</span>
                <span style="font-size:11px;color:#9ca3af">{n} comptes · {en_c} en cours · {cli} clients</span>
              </div>
              <div style="background:#e5e7eb;border-radius:4px;height:8px">
                <div style="width:{pct}%;background:{color};height:8px;border-radius:4px"></div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("**🏭 Top secteurs**")
        top_s = (df.groupby('secteur').size()
                   .reset_index(name='n')
                   .sort_values('n', ascending=False)
                   .head(8))
        for _, row in top_s.iterrows():
            pct = int(row['n']/total*100)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
              <div style="width:110px;font-size:11px;color:#6b7280;text-align:right;
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{row['secteur']}</div>
              <div style="flex:1;background:#e5e7eb;border-radius:3px;height:6px">
                <div style="width:{pct}%;background:#1D3461;height:6px;border-radius:3px"></div>
              </div>
              <div style="width:18px;font-size:11px;font-weight:700;color:#374151">{row['n']}</div>
            </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_pipe:
    st.markdown("**🔄 Pipeline de prospection**")

    # Single st.markdown() for entire board — avoids st.columns+HTML rendering issues
    board_parts = []
    for stage in PIPELINE_STAGES:
        stage_df = df[df.etat == stage].sort_values('nom')
        cfg = ETAT_CFG.get(stage, {"color":"#9CA3AF","bg":"#F9FAFB"})
        n = len(stage_df)

        cards = []
        for _, acc in stage_df.iterrows():
            rc_c = RC_COLORS.get(acc.rc, '#9CA3AF')
            rc_part = (f'<span style="float:right;color:{rc_c};font-weight:700;font-size:11px">{acc.rc}</span>' if acc.rc else '')
            date_part = (f'<div style="color:#a8c2d8;font-size:10px;margin-top:2px">{acc.date_attaque}</div>' if acc.date_attaque else '')
            cards.append(
                f'<div style="background:white;border:1px solid #e8eef8;border-radius:8px;padding:9px 10px;margin-bottom:5px;font-size:12px">'
                f'<a href="{acc.url}" target="_blank" style="color:#1D3461;font-weight:600;font-size:11px;text-decoration:none">{acc.nom}</a>'
                f'{rc_part}'
                f'<div style="clear:both;color:#9ca3af;font-size:10px;margin-top:1px">{acc.secteur}</div>'
                f'{date_part}'
                f'</div>'
            )

        cards_inner = ''.join(cards) or '<p style="text-align:center;color:#d1d5db;font-size:12px;padding:16px 0">—</p>'
        board_parts.append(
            f'<div style="flex:0 0 155px;min-width:155px">'
            f'<div style="border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07)">'
            f'<div style="background:{cfg["bg"]};padding:8px 10px;border-bottom:2px solid {cfg["color"]}">'
            f'<div style="font-weight:700;font-size:12px;color:{cfg["color"]}">{stage}</div>'
            f'<div style="font-size:10px;color:#9ca3af">{n} compte{"s" if n!=1 else ""}</div>'
            f'</div>'
            f'<div style="max-height:420px;overflow-y:auto;padding:6px;background:white">'
            f'{cards_inner}'
            f'</div></div></div>'
        )

    board_html = '<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px">' + ''.join(board_parts) + '</div>'
    st.markdown(board_html, unsafe_allow_html=True)

    st.markdown("---")
    sc1, sc2 = st.columns(2)
    for col, stage in zip([sc1, sc2], SIDE_STAGES):
        side_df = df[df.etat == stage]
        with col:
            with st.expander(f"{stage} ({len(side_df)})", expanded=False):
                tags = ''.join([
                    f'<a href="{r.url}" target="_blank" style="display:inline-block;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:3px 8px;font-size:12px;color:#6b7280;text-decoration:none;margin:2px">{r.nom}</a>'
                    for _, r in side_df.iterrows()
                ])
                st.markdown(tags or "Aucun compte", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PLANNING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_plan:
    st.markdown("**📅 Planning d'attaque** — cliquez sur un mois pour le déplier")

    for month in MONTHS:
        mdf = df[df.date_attaque == month].sort_values('potentiel', ascending=False, na_position='last')
        if mdf.empty:
            continue

        etat_summary = " ".join([etat_badge(e) for e in mdf.etat.value_counts().index[:4]])
        label = f"📅 **{month}** — {len(mdf)} compte{'s' if len(mdf)!=1 else ''}"

        with st.expander(label, expanded=True):
            render_html(etat_summary)
            rows_parts = []
            for _, acc in mdf.iterrows():
                rc_c = RC_COLORS.get(acc.rc,'#9CA3AF')
                pot  = f"Pot.{int(acc.potentiel)}/5" if pd.notna(acc.potentiel) else ""
                rows_parts.append(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 4px;border-bottom:1px solid #f0f0f0">'
                    f'<div><a href="{acc.url}" target="_blank" style="font-weight:600;color:#1e293b;text-decoration:none">{acc.nom}</a>'
                    f'<span style="font-size:11px;color:#9ca3af;margin-left:8px">{acc.secteur}</span></div>'
                    f'<div style="display:flex;align-items:center;gap:8px;flex-shrink:0">'
                    f'{etat_badge(acc.etat)}'
                    f'{"<span style='font-size:12px;font-weight:700;color:"+rc_c+"'>"+acc.rc+"</span>" if acc.rc else ""}'
                    f'{"<span style='font-size:11px;color:#9ca3af'>"+pot+"</span>" if pot else ""}'
                    f'</div></div>'
                )
            st.markdown(''.join(rows_parts), unsafe_allow_html=True)

    no_date = df[df.date_attaque == '']
    if not no_date.empty:
        with st.expander(f"Sans date d'attaque ({len(no_date)})", expanded=False):
            tags = ''.join([
                f'<a href="{r.url}" target="_blank" style="display:inline-block;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;padding:3px 8px;font-size:12px;color:#6b7280;text-decoration:none;margin:2px">{r.nom}</a>'
                for _, r in no_date.iterrows()
            ])
            st.markdown(tags, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MATRICE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_mat:
    mat_df   = df.dropna(subset=['potentiel','accessibilite']).copy()
    no_score = df[df.potentiel.isna() | df.accessibilite.isna()]

    st.markdown(f"**🎯 Matrice Potentiel × Accessibilité** · "
                f"{len(mat_df)} comptes scorés, {len(no_score)} sans score")
    st.caption("Couleur = Responsable commercial · Survolez un point pour le détail")

    if not mat_df.empty:
        fig = go.Figure()

        # Quadrant backgrounds
        for x0, y0, x1, y1, color in [
            (3, 3, 5.5, 5.5, "rgba(134,239,172,0.15)"),
            (0.5, 3, 3, 5.5, "rgba(253,186,116,0.15)"),
            (3, 0.5, 5.5, 3, "rgba(147,197,253,0.15)"),
            (0.5, 0.5, 3, 3, "rgba(156,163,175,0.10)"),
        ]:
            fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                          fillcolor=color, line_width=0, layer="below")

        # Dividers
        fig.add_shape(type="line", x0=3, y0=0.5, x1=3, y1=5.5,
                      line=dict(color="#d1d5db", width=1.5, dash="dash"))
        fig.add_shape(type="line", x0=0.5, y0=3, x1=5.5, y1=3,
                      line=dict(color="#d1d5db", width=1.5, dash="dash"))

        # Quadrant labels
        for text, x, y, color in [
            ("<b>⭐ Priorité 1</b>", 4.2, 5.25, "#059669"),
            ("<b>🎯 Priorité 2</b>", 1.5, 5.25, "#EA580C"),
            ("<b>🌱 À explorer</b>", 4.2, 0.75, "#3B82F6"),
            ("<b>⏸ Faible prio</b>", 1.2, 0.75, "#9CA3AF"),
        ]:
            fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                               font=dict(size=11, color=color),
                               bgcolor="rgba(255,255,255,0.75)", borderpad=3)

        # Points by RC
        for rc, color in RC_COLORS.items():
            rdf = mat_df[mat_df.rc == rc]
            if rdf.empty:
                continue
            fig.add_trace(go.Scatter(
                x=rdf.accessibilite, y=rdf.potentiel,
                mode='markers', name=rc,
                marker=dict(color=color, size=14,
                            line=dict(color='white', width=2), opacity=0.88),
                text=rdf.nom,
                customdata=list(zip(rdf.etat, rdf.secteur, rdf.rc)),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Accessibilité: %{x}/5 · Potentiel: %{y}/5<br>"
                    "État: %{customdata[0]} · RC: %{customdata[2]}<extra></extra>"
                ),
            ))

        others = mat_df[~mat_df.rc.isin(RC_COLORS)]
        if not others.empty:
            fig.add_trace(go.Scatter(
                x=others.accessibilite, y=others.potentiel,
                mode='markers', name='Autre',
                marker=dict(color='#9CA3AF', size=14,
                            line=dict(color='white', width=2), opacity=0.88),
                text=others.nom,
                hovertemplate="<b>%{text}</b><br>Accessibilité: %{x}/5 · Potentiel: %{y}/5<extra></extra>",
            ))

        fig.update_layout(
            xaxis=dict(title="← Difficile · Accessibilité · Facile →",
                       range=[0.5,5.5], tickvals=[1,2,3,4,5],
                       showgrid=True, gridcolor='#f3f4f6'),
            yaxis=dict(title="Potentiel business ↑",
                       range=[0.5,5.5], tickvals=[1,2,3,4,5],
                       showgrid=True, gridcolor='#f3f4f6'),
            legend=dict(orientation='h', y=1.08),
            margin=dict(l=40,r=20,t=50,b=40),
            height=480,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, use_container_width=True)

    # 4 quadrant lists
    st.markdown("---")
    p1 = mat_df[(mat_df.potentiel>=3)&(mat_df.accessibilite>=3)].sort_values(['potentiel','accessibilite'],ascending=False)
    p2 = mat_df[(mat_df.potentiel>=3)&(mat_df.accessibilite<3)].sort_values('potentiel',ascending=False)
    p3 = mat_df[(mat_df.potentiel<3)&(mat_df.accessibilite>=3)].sort_values('accessibilite',ascending=False)
    p4 = mat_df[(mat_df.potentiel<3)&(mat_df.accessibilite<3)]

    def quadrant_list(qdf, label, color, border, limit=8):
        item_parts = []
        for _, acc in qdf.head(limit).iterrows():
            rc_c = RC_COLORS.get(acc.rc,'#9CA3AF')
            item_parts.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 4px;border-bottom:1px solid #f5f5f5;font-size:13px">'
                f'<div style="flex:1;min-width:0">'
                f'<a href="{acc.url}" target="_blank" style="font-weight:600;color:#1e293b;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block">{acc.nom}</a>'
                f'<span style="font-size:11px;color:#9ca3af">{acc.secteur}</span>'
                f'</div>'
                f'<div style="display:flex;gap:6px;align-items:center;flex-shrink:0;margin-left:8px">'
                f'{"<span style='color:"+rc_c+";font-weight:700;font-size:12px'>"+acc.rc+"</span>" if acc.rc else ""}'
                f'<span style="font-size:11px;color:#9ca3af">{int(acc.potentiel)}/{int(acc.accessibilite)}</span>'
                f'{etat_badge(acc.etat)}'
                f'</div></div>'
            )
        items = ''.join(item_parts)
        if len(qdf) > limit:
            items += f'<div style="text-align:center;font-size:11px;color:#9ca3af;padding:6px">+ {len(qdf)-limit} autres</div>'
        if not items:
            items = '<div style="text-align:center;font-size:12px;color:#d1d5db;padding:12px">Aucun compte</div>'

        return (
            f'<div style="border-left:4px solid {border};padding-left:12px;margin-bottom:8px">'
            f'<span style="font-weight:700;color:{color}">{label}</span>'
            f'<span style="color:#9ca3af"> ({len(qdf)})</span>'
            f'</div>'
            f'<div style="background:white;border:1px solid {border};border-radius:8px;overflow:hidden">'
            f'{items}'
            f'</div>'
        )

    q1, q2 = st.columns(2)
    with q1:
        st.markdown(quadrant_list(p1,"⭐ Priorité 1 — Pot ≥ 3 & Acc ≥ 3","#059669","#86EFAC"), unsafe_allow_html=True)
    with q2:
        st.markdown(quadrant_list(p2,"🎯 Priorité 2 — Potentiel fort, accès difficile","#EA580C","#FED7AA"), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    q3, q4 = st.columns(2)
    with q3:
        st.markdown(quadrant_list(p3,"🌱 À explorer — Accessible, potentiel modéré","#3B82F6","#BFDBFE",6), unsafe_allow_html=True)
    with q4:
        st.markdown(quadrant_list(p4,"⏸ Faible priorité","#9CA3AF","#E5E7EB",6), unsafe_allow_html=True)

    if not no_score.empty:
        st.warning(f"⚠️ **{len(no_score)} compte(s) sans score** — non affichés dans la matrice : "
                   + ", ".join(no_score.nom.tolist()[:10])
                   + (f" (+{len(no_score)-10})" if len(no_score)>10 else ""))

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TOUS LES COMPTES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_all:
    st.markdown(f"**📋 Tous les comptes ({len(df)})**")

    col_s, col_rc, col_et = st.columns([3,1,2])
    search     = col_s.text_input("Rechercher", placeholder="🔍 Nom ou secteur...", label_visibility="collapsed")
    rc_filter  = col_rc.selectbox("RC", ["Tous"] + sorted(df.rc[df.rc!=''].unique().tolist()), label_visibility="collapsed")
    et_filter  = col_et.selectbox("État", ["Tous les états"] + PIPELINE_STAGES + SIDE_STAGES, label_visibility="collapsed")

    filt = df.copy()
    if search:
        filt = filt[filt.nom.str.contains(search, case=False, na=False) |
                    filt.secteur.str.contains(search, case=False, na=False)]
    if rc_filter != "Tous":
        filt = filt[filt.rc == rc_filter]
    if et_filter != "Tous les états":
        filt = filt[filt.etat == et_filter]

    st.caption(f"{len(filt)} compte(s) affichés sur {len(df)}")

    display = filt[["nom","secteur","rc","etat","typologie","date_attaque","potentiel","accessibilite","url"]].copy()
    display.columns = ["Compte","Secteur","RC","État","Typologie","Date d'attaque","Potentiel","Accessibilité","↗ Notion"]
    display["Potentiel"]    = pd.to_numeric(display["Potentiel"],    errors='coerce')
    display["Accessibilité"]= pd.to_numeric(display["Accessibilité"], errors='coerce')

    st.dataframe(
        display,
        column_config={
            "Compte":        st.column_config.TextColumn("Compte", width="large"),
            "↗ Notion":      st.column_config.LinkColumn("↗ Notion", display_text="Ouvrir"),
            "Potentiel":     st.column_config.ProgressColumn("Potentiel",    min_value=0, max_value=5, format="%.0f/5"),
            "Accessibilité": st.column_config.ProgressColumn("Accessibilité",min_value=0, max_value=5, format="%.0f/5"),
        },
        hide_index=True,
        use_container_width=True,
        height=520,
    )
