"""
ui/visualisation.py
Visualisation 3D de la structure avec Plotly
"""
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


def page_visualisation(projet, res=None):
    st.markdown("## 🔷 Visualisation 3D de la structure")

    if projet is None or not projet.noeuds:
        st.warning("Aucun projet ou nœuds définis.")
        return

    if not PLOTLY_OK:
        st.error("Plotly non disponible. Installez plotly avec : pip install plotly")
        return

    from core.topologie import calc_niveaux, calc_barres, calc_dalles
    calc_niveaux(projet); calc_barres(projet); calc_dalles(projet)

    noeud_map = {n.id: n for n in projet.noeuds}

    # ── Options ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        show_poutre  = st.checkbox("Poutres",   True)
        show_poteau  = st.checkbox("Poteaux",   True)
    with col2:
        show_dalles  = st.checkbox("Dalles",    True)
        show_noeuds  = st.checkbox("Nœuds",     False)
    with col3:
        show_resultats = st.checkbox("Colorer par As", res is not None)

    # ── Construction figure ───────────────────────────────────────────────────
    fig = go.Figure()

    # Palette
    COL_POUTRE = "#2E75B6"
    COL_POTEAU = "#D4AF37"
    COL_DALLE  = "rgba(180,220,255,0.25)"
    COL_ALERTE = "#E74C3C"

    # Poutres
    if show_poutre:
        for b in projet.barres:
            if b.type_elem != "poutre":
                continue
            ni = noeud_map.get(b.ni)
            nj = noeud_map.get(b.nj)
            if not ni or not nj:
                continue
            color = COL_POUTRE
            if show_resultats and res:
                r = next((r for r in res.poutres if r.barre_id == b.id), None)
                if r and r.alerte:
                    color = COL_ALERTE
            fig.add_trace(go.Scatter3d(
                x=[ni.x, nj.x], y=[ni.y, nj.y], z=[ni.z, nj.z],
                mode="lines",
                line=dict(color=color, width=5),
                name="Poutre", legendgroup="poutres",
                showlegend=(b.id == next(
                    (b2.id for b2 in projet.barres if b2.type_elem=="poutre"), 0)),
                hovertext=f"P{b.id} ({b.b*100:.0f}×{b.h*100:.0f}cm)<br>ni={b.ni} nj={b.nj}",
                hoverinfo="text"
            ))

    # Poteaux
    if show_poteau:
        for b in projet.barres:
            if b.type_elem != "poteau":
                continue
            ni = noeud_map.get(b.ni)
            nj = noeud_map.get(b.nj)
            if not ni or not nj:
                continue
            color = COL_POTEAU
            if show_resultats and res:
                r = next((r for r in res.poteaux if r.barre_id == b.id), None)
                if r and r.alerte_am:
                    color = COL_ALERTE
            fig.add_trace(go.Scatter3d(
                x=[ni.x, nj.x], y=[ni.y, nj.y], z=[ni.z, nj.z],
                mode="lines",
                line=dict(color=color, width=8),
                name="Poteau", legendgroup="poteaux",
                showlegend=(b.id == next(
                    (b2.id for b2 in projet.barres if b2.type_elem=="poteau"), 0)),
                hovertext=f"C{b.id} ({b.b*100:.0f}×{b.h*100:.0f}cm)<br>ni={b.ni} nj={b.nj}",
                hoverinfo="text"
            ))

    # Dalles (triangulation)
    if show_dalles:
        for d in projet.dalles:
            pts = [noeud_map.get(nid) for nid in d.noeuds if nid in noeud_map]
            if len(pts) < 3:
                continue
            xs = [p.x for p in pts] + [pts[0].x]
            ys = [p.y for p in pts] + [pts[0].y]
            zs = [p.z for p in pts] + [pts[0].z]
            fig.add_trace(go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                line=dict(color="rgba(100,160,220,0.6)", width=2),
                name="Dalle", legendgroup="dalles",
                showlegend=(d.id == projet.dalles[0].id if projet.dalles else False),
                hovertext=f"D{d.id} G={d.G:.1f} Q={d.Q:.1f}",
                hoverinfo="text"
            ))
            # Surface transparente
            if len(pts) >= 4:
                for i in range(1, len(pts)-1):
                    fig.add_trace(go.Mesh3d(
                        x=[pts[0].x, pts[i].x, pts[i+1].x if i+1<len(pts) else pts[0].x],
                        y=[pts[0].y, pts[i].y, pts[i+1].y if i+1<len(pts) else pts[0].y],
                        z=[pts[0].z, pts[i].z, pts[i+1].z if i+1<len(pts) else pts[0].z],
                        color="lightblue", opacity=0.2,
                        showscale=False, hoverinfo="skip",
                        showlegend=False,
                    ))

    # Nœuds
    if show_noeuds:
        xs = [n.x for n in projet.noeuds]
        ys = [n.y for n in projet.noeuds]
        zs = [n.z for n in projet.noeuds]
        ids= [str(n.id) for n in projet.noeuds]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers+text",
            marker=dict(size=4, color="black"),
            text=ids, textposition="top center",
            textfont=dict(size=9),
            name="Nœuds",
        ))

    # Mise en page
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.8)"),
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode="data",
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        paper_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Légende couleurs
    if show_resultats and res:
        st.markdown("""
        <div style='display:flex;gap:20px;font-size:0.85rem;margin-top:8px'>
            <span>🟦 Poutres OK</span>
            <span>🟨 Poteaux OK</span>
            <span>🔴 Éléments à vérifier (REVOIR)</span>
        </div>""", unsafe_allow_html=True)

    # Stats
    st.divider()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Nœuds", len(projet.noeuds))
    c2.metric("Poutres", sum(1 for b in projet.barres if b.type_elem=="poutre"))
    c3.metric("Poteaux", sum(1 for b in projet.barres if b.type_elem=="poteau"))
    c4.metric("Dalles", len(projet.dalles))
