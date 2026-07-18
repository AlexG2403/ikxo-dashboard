import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import plotly.graph_objects as go
import json as _json
import re
from html import escape as he

st.set_page_config(page_title="IKXO — Suivi Comptes Stratégiques", layout="wide", initial_sidebar_state="collapsed")

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
[data-testid="stAppViewContainer"] { background:#f0f4f8; }
[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1rem !important; }

.stTabs [data-baseweb="tab-list"],
.stTabs [role="tablist"] {
    background:#1D3461 !important;
    border-radius:10px 10px 0 0;
    padding:4px 8px 0 8px !important;
    gap:4px !important;
    display:flex !important;
    flex-direction:row !important;
    align-items:flex-end !important;
}
.stTabs [data-baseweb="tab"],
.stTabs button[role="tab"] {
    background:transparent !important;
    color:rgba(255,255,255,.75) !important;
    border-radius:8px 8px 0 0 !important;
    padding:9px 16px !important;
    font-size:13px !important;
    font-weight:600 !important;
    border:none !important;
    border-bottom:3px solid transparent !important;
    transition:all .15s !important;
    white-space:nowrap !important;
    min-width:fit-content !important;
    flex-shrink:0 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"],
.stTabs button[role="tab"][aria-selected="true"] {
    background:rgba(255,255,255,.22) !important;
    color:#ffffff !important;
    font-weight:800 !important;
    border-bottom:3px solid #ffffff !important;
    text-shadow:0 0 12px rgba(255,255,255,.4) !important;
}
.stTabs [data-baseweb="tab"] *,
.stTabs button[role="tab"] * {
    color:inherit !important;
    font-size:inherit !important;
    font-weight:inherit !important;
}
.stTabs [data-baseweb="tab-panel"],
.stTabs [role="tabpanel"] {
    background:white;
    border-radius:0 0 10px 10px;
    padding:20px;
    box-shadow:0 2px 10px rgba(0,0,0,.06);
}
.badge { display:inline-block;padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;white-space:nowrap; }
div[data-testid="stExpander"] { border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

# ── MODAL SNIPPETS (reused across components) ─────────────────────────────────
_MODAL_CSS = (
    "body{margin:0;font-family:Inter,system-ui,sans-serif;}"
    "#acc-modal{display:none;position:fixed;inset:0;z-index:10001;"
    "background:rgba(15,23,42,.55);backdrop-filter:blur(4px);"
    "align-items:center;justify-content:center;}"
    "#list-modal{display:none;position:fixed;inset:0;z-index:10000;"
    "background:rgba(15,23,42,.55);backdrop-filter:blur(4px);"
    "align-items:center;justify-content:center;}"
    ".mbox{background:white;border-radius:16px;padding:24px 28px;"
    "width:90%;max-width:460px;max-height:85vh;overflow-y:auto;"
    "box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative;animation:mi .18s ease;}"
    ".lbox{background:white;border-radius:16px;padding:24px 28px;"
    "width:90%;max-width:500px;max-height:80vh;overflow-y:auto;"
    "box-shadow:0 20px 60px rgba(0,0,0,.3);position:relative;}"
    "@keyframes mi{from{opacity:0;transform:scale(.93) translateY(10px)}to{opacity:1;transform:scale(1) translateY(0)}}"
    ".mclose{position:absolute;top:14px;right:18px;background:none;border:none;"
    "font-size:20px;cursor:pointer;color:#9ca3af;line-height:1;}"
    ".mclose:hover{color:#1D3461;}"
    ".badge{display:inline-block;padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;}"
    ".list-item{padding:9px 4px;border-bottom:1px solid #f0f0f0;cursor:pointer;border-radius:4px;}"
    ".list-item:hover{background:#f8fafc;}"
    ".pipe-card{background:white;border:1px solid #e8eef8;border-radius:8px;"
    "padding:9px 10px;margin-bottom:5px;font-size:12px;cursor:pointer;user-select:none;"
    "transition:transform .15s,box-shadow .15s,border-color .15s;}"
    ".pipe-card:hover{transform:translateY(-3px) scale(1.015);"
    "box-shadow:0 6px 16px rgba(29,52,97,.14);border-color:#a8c2d8;}"
    ".pipe-card:active{transform:translateY(-1px) scale(1.005);}"
    ".plan-row{display:flex;align-items:center;justify-content:space-between;"
    "padding:8px 6px;border-bottom:1px solid #f0f0f0;cursor:pointer;"
    "border-radius:4px;transition:background .12s;}"
    ".plan-row:hover{background:#f8fafc;}"
    ".acc-row:hover{background:#f8fafc;}"
    ".acc-name{font-weight:600;color:#1D3461;cursor:pointer;}"
    ".acc-name:hover{text-decoration:underline;}"
)

_ACC_MODAL_HTML = (
    '<div id="acc-modal" onclick="if(event.target.id===\'acc-modal\')closeModal()">'
    '<div class="mbox">'
    '<button class="mclose" onclick="closeModal()">&#x2715;</button>'
    '<div id="m-badge" style="margin-bottom:8px"></div>'
    '<h3 id="m-nom" style="margin:0 0 3px;color:#1D3461;font-size:19px;padding-right:24px"></h3>'
    '<div id="m-rc" style="font-size:12px;color:#6b7280;margin-bottom:16px"></div>'
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px">'
    '<div style="background:#f8fafc;border-radius:8px;padding:10px">'
    '<div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Secteur</div>'
    '<div id="m-sec" style="font-size:13px;font-weight:600;color:#1e293b"></div></div>'
    '<div style="background:#f8fafc;border-radius:8px;padding:10px">'
    '<div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Date d\'attaque</div>'
    '<div id="m-date" style="font-size:13px;font-weight:600;color:#1e293b"></div></div>'
    '<div style="background:#f8fafc;border-radius:8px;padding:10px">'
    '<div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Potentiel</div>'
    '<div id="m-pot" style="font-size:13px;font-weight:600;color:#1D3461"></div></div>'
    '<div style="background:#f8fafc;border-radius:8px;padding:10px">'
    '<div style="font-size:9px;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Accessibilit&#233;</div>'
    '<div id="m-acc" style="font-size:13px;font-weight:600;color:#1D3461"></div></div>'
    '</div>'
    '<a id="m-url" href="#" target="_blank"'
    ' style="display:block;text-align:center;background:#1D3461;color:white;text-decoration:none;'
    'border-radius:8px;padding:10px;font-weight:600;font-size:13px">&#8599; Voir sur Notion</a>'
    '</div></div>'
)

_LIST_MODAL_HTML = (
    '<div id="list-modal" onclick="if(event.target.id===\'list-modal\')closeListModal()">'
    '<div class="lbox">'
    '<button class="mclose" onclick="closeListModal()">&#x2715;</button>'
    '<h3 id="lm-title" style="margin:0 0 14px;color:#1D3461;font-size:17px;padding-right:24px"></h3>'
    '<div id="lm-body" style="overflow-y:auto;max-height:55vh"></div>'
    '</div></div>'
)

_OPEN_MODAL_JS = (
    "function openModal(el){"
    "var cfg=JSON.parse(el.dataset.cfg||'{}');"
    "document.getElementById('m-nom').textContent=el.dataset.nom||'';"
    "document.getElementById('m-rc').textContent=el.dataset.rc?'RC : '+el.dataset.rc:'';"
    "document.getElementById('m-sec').textContent=el.dataset.sec||'';"
    "document.getElementById('m-date').textContent=el.dataset.date||'—';"
    "document.getElementById('m-pot').textContent=el.dataset.pot?el.dataset.pot+'/5':'—';"
    "document.getElementById('m-acc').textContent=el.dataset.acc?el.dataset.acc+'/5':'—';"
    "document.getElementById('m-url').href=el.dataset.url||'#';"
    "document.getElementById('m-badge').innerHTML='<span class=\"badge\" style=\"background:'+cfg.bg+';color:'+cfg.color+'\">'+(el.dataset.etat||'')+'</span>';"
    "document.getElementById('acc-modal').style.display='flex';}"
    "function closeModal(){document.getElementById('acc-modal').style.display='none';_shrinkFrame();}"
    "function closeListModal(){document.getElementById('list-modal').style.display='none';_shrinkFrame();}"
    "function _expandFrame(){try{var f=window.frameElement;if(f){f._sh=f.style.height;f.style.height='100vh';f.style.position='fixed';f.style.top='0';f.style.left='0';f.style.width='100vw';f.style.zIndex='99999';}}catch(e){}}"
    "function _shrinkFrame(){try{var f=window.frameElement;if(f&&f._sh!==undefined){f.style.height=f._sh;f.style.position='';f.style.top='';f.style.left='';f.style.width='';f.style.zIndex='';}}catch(e){}}"
)

def component_wrap(body_html, extra_css="", extra_js=""):
    return (
        "<!DOCTYPE html><html><head><style>"
        + _MODAL_CSS + extra_css +
        "</style></head><body>"
        + _ACC_MODAL_HTML
        + body_html
        + "<script>" + _OPEN_MODAL_JS + extra_js + "</script>"
        + "</body></html>"
    )

def component_wrap_dual(body_html, extra_css="", extra_js=""):
    """With both account + list modals."""
    return (
        "<!DOCTYPE html><html><head><style>"
        + _MODAL_CSS + extra_css +
        "</style></head><body>"
        + _ACC_MODAL_HTML
        + _LIST_MODAL_HTML
        + body_html
        + "<script>" + _OPEN_MODAL_JS + extra_js + "</script>"
        + "</body></html>"
    )

# ── NOTION DATA ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Chargement depuis Notion...")
def fetch_accounts():
    if "NOTION_API_KEY" not in st.secrets:
        st.error("NOTION_API_KEY manquante")
        st.stop()
    key = st.secrets["NOTION_API_KEY"]
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            "https://api.notion.com/v1/databases/" + DATABASE_ID + "/query",
            headers={"Authorization": "Bearer " + key,
                     "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
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
    return '<span class="badge" style="background:' + c["bg"] + ';color:' + c["color"] + '">' + he(etat) + '</span>'

def render_html(html):
    st.markdown(re.sub(r'\n[ \t]+', '\n', html).strip(), unsafe_allow_html=True)

def acc_data_attrs(acc):
    cfg  = ETAT_CFG.get(acc.etat, {"color":"#6B7280","bg":"#F3F4F6"})
    pot  = str(int(acc.potentiel))     if pd.notna(acc.potentiel)     else ""
    ac_v = str(int(acc.accessibilite)) if pd.notna(acc.accessibilite) else ""
    return (
        ' data-nom="'  + he(acc.nom,          quote=True) + '"'
        ' data-rc="'   + he(acc.rc,            quote=True) + '"'
        ' data-sec="'  + he(acc.secteur,       quote=True) + '"'
        ' data-date="' + he(acc.date_attaque or "", quote=True) + '"'
        ' data-pot="'  + pot  + '"'
        ' data-acc="'  + ac_v + '"'
        ' data-url="'  + he(acc.url,           quote=True) + '"'
        ' data-etat="' + he(acc.etat,          quote=True) + '"'
        " data-cfg='"  + _json.dumps(cfg).replace("'", "\\'") + "'"
    )

def build_accounts_js(source_df):
    """Return JS snippet declaring ALL_ACCOUNTS and openListModal."""
    rows = []
    for _, r in source_df.iterrows():
        rows.append({
            'nom':     r.nom,
            'rc':      r.rc or '',
            'secteur': r.secteur,
            'etat':    r.etat,
            'url':     r.url,
            'typ':     r.typologie or '',
            'date':    r.date_attaque or '',
            'pot':     str(int(r.potentiel))     if pd.notna(r.potentiel)     else '',
            'acc':     str(int(r.accessibilite)) if pd.notna(r.accessibilite) else '',
        })
    all_json    = _json.dumps(rows)
    etat_json   = _json.dumps(ETAT_CFG)
    rc_json     = _json.dumps(RC_COLORS)
    return (
        "var ALL=" + all_json + ";"
        "var EC=" + etat_json + ";"
        "var RCC=" + rc_json + ";"
        "var G={"
        "total:ALL,"
        "strat:ALL.filter(function(a){return a.typ==='Stratégique';}),"
        "closing:ALL.filter(function(a){return['1 rdv','Plusieurs rdv','Besoin','Soutenance'].indexOf(a.etat)>=0;}),"
        "clients:ALL.filter(function(a){return a.etat==='Client';}),"
        "};"
        "function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');}"
        "function _expandFrame(){"
        "try{"
        "var f=window.frameElement;"
        "if(f){f._sh=f.style.height;f.style.height='100vh';f.style.position='fixed';"
        "f.style.top='0';f.style.left='0';f.style.width='100vw';f.style.zIndex='99999';}"
        "}catch(e){}}"
        "function _shrinkFrame(){"
        "try{"
        "var f=window.frameElement;"
        "if(f&&f._sh!==undefined){"
        "f.style.height=f._sh;f.style.position='';f.style.top='';"
        "f.style.left='';f.style.width='';f.style.zIndex='';}"
        "}catch(e){}}"
        "function _buildListItem(a){"
        "var cfg=EC[a.etat]||{color:'#6B7280',bg:'#F3F4F6'};"
        "var rc_c=RCC[a.rc]||'#9CA3AF';"
        "return '<div class=\"list-item\"'"
        "+'data-nom=\"'+esc(a.nom)+'\"'"
        "+'data-rc=\"'+esc(a.rc)+'\"'"
        "+'data-sec=\"'+esc(a.secteur)+'\"'"
        "+'data-date=\"'+esc(a.date)+'\"'"
        "+'data-pot=\"'+a.pot+'\"'"
        "+'data-acc=\"'+a.acc+'\"'"
        "+'data-url=\"'+esc(a.url)+'\"'"
        "+'data-etat=\"'+esc(a.etat)+'\"'"
        "+\"data-cfg='\"+JSON.stringify(cfg)+\"'\""
        "+'onclick=\"closeListModal();openModal(this)\">'"
        "+'<div style=\"font-weight:600;color:#1e293b;font-size:13px\">'+esc(a.nom)+'</div>'"
        "+'<div style=\"display:flex;gap:6px;align-items:center;margin-top:3px\">'"
        "+(a.rc?'<span style=\"color:'+rc_c+';font-weight:700;font-size:11px\">'+esc(a.rc)+'</span>':'')"
        "+'<span style=\"background:'+cfg.bg+';color:'+cfg.color+';padding:1px 7px;border-radius:9999px;font-size:11px;font-weight:600\">'+esc(a.etat)+'</span>'"
        "+'</div></div>';}"
        "function _showList(accs,title){"
        "_expandFrame();"
        "document.getElementById('lm-body').innerHTML=accs.map(_buildListItem).join('');"
        "document.getElementById('lm-title').textContent=title;"
        "document.getElementById('list-modal').style.display='flex';}"
        "function openListModal(group,title){_showList(G[group]||[],title);}"
        "function openListByFilter(field,value,title){"
        "_showList(ALL.filter(function(a){return a[field]===value;}),title);}"
        "function closeListModal(){"
        "document.getElementById('list-modal').style.display='none';"
        "_shrinkFrame();}"
    )

# ── HEADER ────────────────────────────────────────────────────────────────────
h1, h2, h3 = st.columns([2, 6, 1])
with h1:
    st.markdown(
        '<div style="font-size:30px;font-weight:900;letter-spacing:-1px;'
        'font-family:Inter,system-ui,sans-serif;padding-top:8px">'
        '<span style="color:#1D3461">I</span>'
        '<span style="color:#6BA58A">K</span>'
        '<span style="color:#1D3461">XO</span>'
        '</div>',
        unsafe_allow_html=True
    )
with h2:
    st.markdown("## Suivi Comptes Stratégiques")
with h3:
    st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
    if st.button("Rafraîchir"):
        st.cache_data.clear()
        st.rerun()

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
try:
    df = fetch_accounts()
except Exception as e:
    st.error("Erreur Notion API : " + str(e))
    st.stop()

if df.empty:
    st.warning("Aucun compte chargé.")
    st.stop()

st.caption("**" + str(len(df)) + " comptes** chargés · " + pd.Timestamp.now().strftime('%H:%M'))

# ── TABS (no emojis, bigger font) ─────────────────────────────────────────────
tab_ov, tab_pipe, tab_plan, tab_mat, tab_all = st.tabs([
    "Vue générale", "Pipeline", "Planning", "Matrice", "Tous les comptes"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VUE GÉNÉRALE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ov:
    total    = len(df)
    clients  = int((df.etat == 'Client').sum())
    en_cours = int(df.etat.isin(['1 rdv','Plusieurs rdv','Besoin','Soutenance']).sum())
    strat    = int((df.typologie == 'Stratégique').sum())

    accs_js = build_accounts_js(df)

    def js_str(s):
        return str(s).replace("\\", "\\\\").replace("'", "\\'")

    # ── Metric cards ────────────────────────────────────────────────
    metrics_html = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;padding:4px 2px;margin-bottom:22px">'
        '<div class="mc" onclick="openListModal(\'total\',\'Tous les comptes (' + str(total) + ')\')">'
        '<div class="mc-label">Total comptes</div><div class="mc-val">' + str(total) + '</div></div>'
        '<div class="mc" onclick="openListModal(\'strat\',\'Comptes Strat\\u00e9giques (' + str(strat) + ')\')">'
        '<div class="mc-label">Strat&#233;giques</div><div class="mc-val">' + str(strat) + '</div></div>'
        '<div class="mc" onclick="openListModal(\'closing\',\'En closing (' + str(en_cours) + ')\')">'
        '<div class="mc-label">En closing</div><div class="mc-val">' + str(en_cours) + '</div></div>'
        '<div class="mc" onclick="openListModal(\'clients\',\'Clients (' + str(clients) + ')\')">'
        '<div class="mc-label">Clients</div><div class="mc-val">' + str(clients) + '</div></div>'
        '</div>'
    )

    # ── Étape bars ──────────────────────────────────────────────────
    all_stages = PIPELINE_STAGES + SIDE_STAGES
    counts_s   = {s: int((df.etat == s).sum()) for s in all_stages}
    max_s      = max(counts_s.values(), default=1)
    stage_bars = ''
    for s in all_stages:
        n   = counts_s[s]
        pct = int(n / max_s * 100) if max_s else 0
        cfg = ETAT_CFG.get(s, {"color":"#9CA3AF"})
        stage_bars += (
            '<div class="bar-row" onclick="openListByFilter(\'etat\',\'' + js_str(s) + '\',\'' + js_str(s) + ' (' + str(n) + ' comptes)\')">'
            '<div class="bar-label">' + he(s) + '</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:' + str(pct) + '%;background:' + cfg["color"] + '"></div></div>'
            '<div class="bar-count">' + str(n) + '</div>'
            '</div>'
        )

    # ── RC bars ─────────────────────────────────────────────────────
    rc_bars = ''
    for rc, color in RC_COLORS.items():
        rc_df = df[df.rc == rc]
        if rc_df.empty:
            continue
        n   = len(rc_df)
        pct = int(n / total * 100) if total else 0
        rc_bars += (
            '<div class="bar-row" onclick="openListByFilter(\'rc\',\'' + js_str(rc) + '\',\'' + js_str(rc) + ' (' + str(n) + ' comptes)\')">'
            '<div class="bar-label" style="color:' + color + ';font-weight:700">' + he(rc) + '</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:' + str(pct) + '%;background:' + color + '"></div></div>'
            '<div class="bar-count">' + str(n) + '</div>'
            '</div>'
        )

    # ── Secteur bars ─────────────────────────────────────────────────
    top_s   = (df.groupby('secteur').size().reset_index(name='n')
                 .sort_values('n', ascending=False).head(8))
    max_sec = int(top_s['n'].max()) if not top_s.empty else 1
    sec_bars = ''
    for _, row in top_s.iterrows():
        n   = int(row['n'])
        pct = int(n / max_sec * 100) if max_sec else 0
        sec_bars += (
            '<div class="bar-row" onclick="openListByFilter(\'secteur\',\'' + js_str(row['secteur']) + '\',\'' + js_str(row['secteur']) + ' (' + str(n) + ' comptes)\')">'
            '<div class="bar-label">' + he(row['secteur']) + '</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:' + str(pct) + '%;background:#1D3461"></div></div>'
            '<div class="bar-count">' + str(n) + '</div>'
            '</div>'
        )

    ov_css = (
        ".mc{background:white;border:1px solid #e5e7eb;border-radius:12px;"
        "padding:18px 12px;text-align:center;cursor:pointer;"
        "transition:transform .12s,box-shadow .12s,border-color .12s;"
        "box-shadow:0 1px 3px rgba(0,0,0,.05);}"
        ".mc:hover{transform:translateY(-2px);box-shadow:0 6px 16px rgba(29,52,97,.10);border-color:#a8c2d8;}"
        ".mc:active{transform:translateY(0);}"
        ".mc-label{font-size:12px;color:#6b7280;margin-bottom:6px;font-weight:500;}"
        ".mc-val{font-size:34px;font-weight:800;color:#1D3461;line-height:1;}"
        ".sec-title{font-size:12px;font-weight:700;color:#374151;margin:0 0 10px;text-transform:uppercase;letter-spacing:.5px}"
        ".cols{display:grid;grid-template-columns:1fr 1fr;gap:24px}"
        ".bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px;"
        "cursor:pointer;border-radius:6px;padding:3px 4px;"
        "transition:background .12s;}"
        ".bar-row:hover{background:#f0f4f8;}"
        ".bar-label{width:120px;font-size:11px;color:#6b7280;text-align:right;"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}"
        ".bar-track{flex:1;background:#e5e7eb;border-radius:3px;height:7px}"
        ".bar-fill{height:7px;border-radius:3px}"
        ".bar-count{width:22px;font-size:11px;font-weight:700;color:#374151;text-align:right;flex-shrink:0}"
        ".sub-col{margin-bottom:18px}"
    )

    ov_body = (
        metrics_html
        + '<div class="cols">'
        + '<div><p class="sec-title">R&#233;partition par &#233;tape</p>' + stage_bars + '</div>'
        + '<div>'
        + '<div class="sub-col"><p class="sec-title">Responsables commerciaux</p>' + rc_bars + '</div>'
        + '<div class="sub-col"><p class="sec-title">Top secteurs</p>' + sec_bars + '</div>'
        + '</div>'
        + '</div>'
    )

    components.html(component_wrap_dual(ov_body, ov_css, accs_js), height=740)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_pipe:
    st.markdown("**Pipeline** — cliquez sur une carte pour le détail")

    board_parts = []
    for stage in PIPELINE_STAGES:
        stage_df = df[df.etat == stage].sort_values('nom')
        cfg = ETAT_CFG.get(stage, {"color":"#9CA3AF","bg":"#F9FAFB"})
        n   = len(stage_df)
        cards = []
        for _, acc in stage_df.iterrows():
            rc_c  = RC_COLORS.get(acc.rc, '#9CA3AF')
            rc_part  = ('<span style="float:right;color:' + rc_c + ';font-weight:700;font-size:11px">' + he(acc.rc) + '</span>' if acc.rc else '')
            date_part = ('<div style="color:#a8c2d8;font-size:10px;margin-top:2px">' + he(acc.date_attaque) + '</div>' if acc.date_attaque else '')
            cards.append(
                '<div class="pipe-card"' + acc_data_attrs(acc) + ' onclick="openModal(this)">'
                + rc_part
                + '<div style="color:#1D3461;font-weight:600;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + he(acc.nom) + '</div>'
                + '<div style="clear:both;color:#9ca3af;font-size:10px;margin-top:1px">' + he(acc.secteur) + '</div>'
                + date_part + '</div>'
            )
        cards_inner = ''.join(cards) or '<p style="text-align:center;color:#d1d5db;font-size:12px;padding:16px 0">—</p>'
        board_parts.append(
            '<div style="flex:0 0 160px;min-width:160px">'
            '<div style="border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.07)">'
            '<div style="background:' + cfg["bg"] + ';padding:8px 10px;border-bottom:2px solid ' + cfg["color"] + '">'
            '<div style="font-weight:700;font-size:12px;color:' + cfg["color"] + '">' + he(stage) + '</div>'
            '<div style="font-size:10px;color:#9ca3af">' + str(n) + ' compte' + ('s' if n!=1 else '') + '</div>'
            '</div>'
            '<div style="max-height:400px;overflow-y:auto;padding:6px;background:white">' + cards_inner + '</div>'
            '</div></div>'
        )

    board_html = '<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px">' + ''.join(board_parts) + '</div>'
    components.html(component_wrap(board_html), height=540, scrolling=True)

    st.markdown("---")
    sc1, sc2 = st.columns(2)
    for col, stage in zip([sc1, sc2], SIDE_STAGES):
        side_df = df[df.etat == stage]
        with col:
            with st.expander(stage + " (" + str(len(side_df)) + ")", expanded=False):
                tags = ''.join([
                    '<a href="' + r.url + '" target="_blank" style="display:inline-block;background:#f9fafb;'
                    'border:1px solid #e5e7eb;border-radius:6px;padding:3px 8px;font-size:12px;'
                    'color:#6b7280;text-decoration:none;margin:2px">' + he(r.nom) + '</a>'
                    for _, r in side_df.iterrows()
                ])
                st.markdown(tags or "Aucun compte", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PLANNING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_plan:
    st.markdown("**Planning d'attaque** — cliquez sur une ligne pour le détail")

    for month in MONTHS:
        mdf = df[df.date_attaque == month].sort_values('potentiel', ascending=False, na_position='last')
        if mdf.empty:
            continue
        etat_summary = " ".join([etat_badge(e) for e in mdf.etat.value_counts().index[:4]])
        with st.expander("**" + month + "** — " + str(len(mdf)) + " compte" + ("s" if len(mdf)!=1 else ""), expanded=True):
            render_html(etat_summary)
            rows = []
            for _, acc in mdf.iterrows():
                rc_c    = RC_COLORS.get(acc.rc, '#9CA3AF')
                pot     = ("Pot." + str(int(acc.potentiel)) + "/5") if pd.notna(acc.potentiel) else ""
                rc_tag  = ('<span style="color:' + rc_c + ';font-weight:700;font-size:12px">' + he(acc.rc) + '</span>') if acc.rc else ''
                pot_tag = ('<span style="font-size:11px;color:#9ca3af">' + pot + '</span>') if pot else ''
                rows.append(
                    '<div class="plan-row"' + acc_data_attrs(acc) + ' onclick="openModal(this)">'
                    '<div>'
                    '<span style="font-weight:600;color:#1e293b;font-size:13px">' + he(acc.nom) + '</span>'
                    '<span style="font-size:11px;color:#9ca3af;margin-left:8px">' + he(acc.secteur) + '</span>'
                    '</div>'
                    '<div style="display:flex;align-items:center;gap:8px;flex-shrink:0">'
                    + etat_badge(acc.etat) + rc_tag + pot_tag +
                    '</div></div>'
                )
            components.html(component_wrap(''.join(rows)), height=max(100, len(mdf)*42+60), scrolling=False)

    no_date = df[df.date_attaque == '']
    if not no_date.empty:
        with st.expander("Sans date d'attaque (" + str(len(no_date)) + ")", expanded=False):
            tags = ''.join([
                '<a href="' + r.url + '" target="_blank" style="display:inline-block;background:#f3f4f6;'
                'border:1px solid #e5e7eb;border-radius:6px;padding:3px 8px;font-size:12px;'
                'color:#6b7280;text-decoration:none;margin:2px">' + he(r.nom) + '</a>'
                for _, r in no_date.iterrows()
            ])
            st.markdown(tags, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MATRICE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_mat:
    mat_df   = df.dropna(subset=['potentiel','accessibilite']).copy()
    no_score = df[df.potentiel.isna() | df.accessibilite.isna()]

    st.markdown("**Matrice Potentiel × Accessibilité** · " + str(len(mat_df)) + " scorés, " + str(len(no_score)) + " sans score")
    st.caption("Couleur = RC · Survolez un point pour le détail")

    if not mat_df.empty:
        fig = go.Figure()
        for x0,y0,x1,y1,c in [(3,3,5.5,5.5,"rgba(134,239,172,0.15)"),(0.5,3,3,5.5,"rgba(253,186,116,0.15)"),
                                (3,0.5,5.5,3,"rgba(147,197,253,0.15)"),(0.5,0.5,3,3,"rgba(156,163,175,0.10)")]:
            fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,fillcolor=c,line_width=0,layer="below")
        fig.add_shape(type="line",x0=3,y0=0.5,x1=3,y1=5.5,line=dict(color="#d1d5db",width=1.5,dash="dash"))
        fig.add_shape(type="line",x0=0.5,y0=3,x1=5.5,y1=3,line=dict(color="#d1d5db",width=1.5,dash="dash"))
        for txt,x,y,c in [("<b>Priorité 1</b>",4.2,5.25,"#059669"),("<b>Priorité 2</b>",1.5,5.25,"#EA580C"),
                           ("<b>A explorer</b>",4.2,0.75,"#3B82F6"),("<b>Faible prio</b>",1.2,0.75,"#9CA3AF")]:
            fig.add_annotation(x=x,y=y,text=txt,showarrow=False,font=dict(size=11,color=c),
                               bgcolor="rgba(255,255,255,0.75)",borderpad=3)
        for rc, color in RC_COLORS.items():
            rdf = mat_df[mat_df.rc == rc]
            if rdf.empty: continue
            fig.add_trace(go.Scatter(
                x=rdf.accessibilite, y=rdf.potentiel, mode='markers', name=rc,
                marker=dict(color=color,size=14,line=dict(color='white',width=2),opacity=0.88),
                text=rdf.nom,
                customdata=list(zip(rdf.etat,rdf.secteur,rdf.rc)),
                hovertemplate="<b>%{text}</b><br>Acc:%{x}/5 · Pot:%{y}/5<br>%{customdata[0]}<extra></extra>",
            ))
        others = mat_df[~mat_df.rc.isin(RC_COLORS)]
        if not others.empty:
            fig.add_trace(go.Scatter(x=others.accessibilite,y=others.potentiel,mode='markers',name='Autre',
                marker=dict(color='#9CA3AF',size=14,line=dict(color='white',width=2),opacity=0.88),
                text=others.nom,hovertemplate="<b>%{text}</b><br>Acc:%{x}/5 · Pot:%{y}/5<extra></extra>"))
        fig.update_layout(
            xaxis=dict(title="Accessibilité",range=[0.5,5.5],tickvals=[1,2,3,4,5],showgrid=True,gridcolor='#f3f4f6'),
            yaxis=dict(title="Potentiel",range=[0.5,5.5],tickvals=[1,2,3,4,5],showgrid=True,gridcolor='#f3f4f6'),
            legend=dict(orientation='h',y=1.08),
            margin=dict(l=40,r=20,t=50,b=40), height=480,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    p1 = mat_df[(mat_df.potentiel>=3)&(mat_df.accessibilite>=3)].sort_values(['potentiel','accessibilite'],ascending=False)
    p2 = mat_df[(mat_df.potentiel>=3)&(mat_df.accessibilite<3)].sort_values('potentiel',ascending=False)
    p3 = mat_df[(mat_df.potentiel<3)&(mat_df.accessibilite>=3)].sort_values('accessibilite',ascending=False)
    p4 = mat_df[(mat_df.potentiel<3)&(mat_df.accessibilite<3)]

    def quadrant_list(qdf, label, color, border, limit=8):
        rows = []
        for _, acc in qdf.head(limit).iterrows():
            rc_c = RC_COLORS.get(acc.rc,'#9CA3AF')
            rows.append(
                '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 4px;border-bottom:1px solid #f5f5f5;font-size:13px">'
                '<div><a href="' + acc.url + '" target="_blank" style="font-weight:600;color:#1e293b;text-decoration:none">' + he(acc.nom) + '</a>'
                '<span style="font-size:11px;color:#9ca3af;margin-left:6px">' + he(acc.secteur) + '</span></div>'
                '<div style="display:flex;gap:6px;align-items:center;flex-shrink:0;margin-left:8px">'
                + (('<span style="color:' + rc_c + ';font-weight:700;font-size:12px">' + he(acc.rc) + '</span>') if acc.rc else '')
                + '<span style="font-size:11px;color:#9ca3af">' + str(int(acc.potentiel)) + '/' + str(int(acc.accessibilite)) + '</span>'
                + etat_badge(acc.etat)
                + '</div></div>'
            )
        items = ''.join(rows)
        if len(qdf) > limit:
            items += '<div style="text-align:center;font-size:11px;color:#9ca3af;padding:6px">+ ' + str(len(qdf)-limit) + ' autres</div>'
        if not items:
            items = '<div style="text-align:center;font-size:12px;color:#d1d5db;padding:12px">Aucun compte</div>'
        return (
            '<div style="border-left:4px solid ' + border + ';padding-left:12px;margin-bottom:8px">'
            '<span style="font-weight:700;color:' + color + '">' + label + '</span>'
            ' <span style="color:#9ca3af">(' + str(len(qdf)) + ')</span></div>'
            '<div style="background:white;border:1px solid ' + border + ';border-radius:8px;overflow:hidden">' + items + '</div>'
        )

    q1, q2 = st.columns(2)
    with q1: st.markdown(quadrant_list(p1,"Priorité 1","#059669","#86EFAC"), unsafe_allow_html=True)
    with q2: st.markdown(quadrant_list(p2,"Priorité 2","#EA580C","#FED7AA"), unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    q3, q4 = st.columns(2)
    with q3: st.markdown(quadrant_list(p3,"A explorer","#3B82F6","#BFDBFE",6), unsafe_allow_html=True)
    with q4: st.markdown(quadrant_list(p4,"Faible priorité","#9CA3AF","#E5E7EB",6), unsafe_allow_html=True)

    if not no_score.empty:
        st.warning("**" + str(len(no_score)) + " compte(s) sans score** : "
                   + ", ".join(no_score.nom.tolist()[:10])
                   + ((" (+" + str(len(no_score)-10) + ")") if len(no_score)>10 else ""))

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TOUS LES COMPTES (clickable names → popup)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_all:
    st.markdown("**Tous les comptes (" + str(len(df)) + ")** — cliquez sur un nom pour le détail")

    col_s, col_rc, col_et = st.columns([3,1,2])
    search    = col_s.text_input("Rechercher", placeholder="Nom ou secteur...", label_visibility="collapsed")
    rc_filter = col_rc.selectbox("RC", ["Tous"] + sorted(df.rc[df.rc!=''].unique().tolist()), label_visibility="collapsed")
    et_filter = col_et.selectbox("État", ["Tous les états"] + PIPELINE_STAGES + SIDE_STAGES, label_visibility="collapsed")

    filt = df.copy()
    if search:
        filt = filt[filt.nom.str.contains(search, case=False, na=False) |
                    filt.secteur.str.contains(search, case=False, na=False)]
    if rc_filter != "Tous":
        filt = filt[filt.rc == rc_filter]
    if et_filter != "Tous les états":
        filt = filt[filt.etat == et_filter]

    st.caption(str(len(filt)) + " compte(s) affichés sur " + str(len(df)))

    # Build HTML table with clickable account names
    thead = (
        '<thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Compte</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Secteur</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">RC</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">État</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Pot.</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Accès</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Date</th>'
        '<th style="text-align:left;padding:9px 12px;font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px">Notion</th>'
        '</tr></thead>'
    )

    tbody_rows = []
    for _, acc in filt.iterrows():
        rc_c    = RC_COLORS.get(acc.rc, '#9CA3AF')
        cfg     = ETAT_CFG.get(acc.etat, {"color":"#6B7280","bg":"#F3F4F6"})
        pot_val = int(acc.potentiel)     if pd.notna(acc.potentiel)     else None
        acc_val = int(acc.accessibilite) if pd.notna(acc.accessibilite) else None

        pot_bar = (
            '<div style="display:flex;align-items:center;gap:3px">'
            '<div style="width:38px;background:#e5e7eb;border-radius:2px;height:5px">'
            '<div style="width:' + str(pot_val*20) + '%;background:#1D3461;height:5px;border-radius:2px"></div>'
            '</div><span style="font-size:10px;color:#9ca3af">' + str(pot_val) + '</span></div>'
        ) if pot_val else '<span style="color:#d1d5db">—</span>'

        acc_bar = (
            '<div style="display:flex;align-items:center;gap:3px">'
            '<div style="width:38px;background:#e5e7eb;border-radius:2px;height:5px">'
            '<div style="width:' + str(acc_val*20) + '%;background:#6BA58A;height:5px;border-radius:2px"></div>'
            '</div><span style="font-size:10px;color:#9ca3af">' + str(acc_val) + '</span></div>'
        ) if acc_val else '<span style="color:#d1d5db">—</span>'

        tbody_rows.append(
            '<tr class="acc-row">'
            '<td style="padding:8px 12px">'
            '<span class="acc-name"' + acc_data_attrs(acc) + ' onclick="openModal(this)">'
            + he(acc.nom) + '</span></td>'
            '<td style="padding:8px 12px;color:#6b7280;font-size:12px">' + he(acc.secteur) + '</td>'
            '<td style="padding:8px 12px"><span style="color:' + rc_c + ';font-weight:700;font-size:12px">' + (he(acc.rc) if acc.rc else '—') + '</span></td>'
            '<td style="padding:8px 12px"><span style="background:' + cfg['bg'] + ';color:' + cfg['color'] + ';padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600">' + he(acc.etat) + '</span></td>'
            '<td style="padding:8px 12px">' + pot_bar + '</td>'
            '<td style="padding:8px 12px">' + acc_bar + '</td>'
            '<td style="padding:8px 12px;color:#9ca3af;font-size:11px">' + he(acc.date_attaque or '—') + '</td>'
            '<td style="padding:8px 12px"><a href="' + he(acc.url) + '" target="_blank" style="color:#1D3461;font-size:14px;text-decoration:none">↗</a></td>'
            '</tr>'
        )

    table_html = (
        '<div style="overflow-x:auto">'
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        + thead + '<tbody>' + ''.join(tbody_rows) + '</tbody></table></div>'
    )

    n_rows = len(filt)
    components.html(component_wrap(table_html), height=min(max(200, n_rows*42+60), 700), scrolling=True)
