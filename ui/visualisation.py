"""
ui/visualisation.py
Visualisation 3D de la structure avec Plotly
v2 : Option B (survol enrichi) + Option D (labels optionnels)
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

    # ── Options ────────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_poutre = st.checkbox("Poutres",  True)
        show_poteau = st.checkbox("Poteaux",  True)
    with col2:
        show_dalles = st.checkbox("Dalles",   True)
        show_noeuds = st.checkbox("Nœuds",    False)
    with col3:
        show_resultats = st.checkbox("Colorer par As", res is not None)
        # Option D — labels optionnels
        show_labels = st.checkbox("Afficher les étiquettes", False)
    with col4:
        if show_labels:
            label_type = st.selectbox(
                "Étiqueter",
                ["Poutres + Poteaux", "Poutres", "Poteaux", "Dalles", "Tout"],
                key="label_type"
            )
        else:
            label_type = "Poutres + Poteaux"

    # ── Palette ────────────────────────────────────────────────────────────────
    COL_POUTRE = "#2E75B6"
    COL_POTEAU = "#D4AF37"
    COL_ALERTE = "#E74C3C"
    COL_LABEL  = "#1F3864"

    fig = go.Figure()

    # ── Poutres ────────────────────────────────────────────────────────────────
    if show_poutre:
        first_p = True
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

            # Option B — survol enrichi
            hover = (f"<b>P{b.id} — {b.nom}</b><br>"
                     f"Section : {b.b*100:.0f}×{b.h*100:.0f} cm<br>"
                     f"Niveau : {b.niveau}<br>"
                     f"Nœuds : {b.ni} → {b.nj}<br>"
                     f"Longueur : {b.longueur:.2f} m<br>"
                     f"G_add : {b.G_add:.1f} kN/m")
            if show_resultats and res:
                r = next((r for r in res.poutres if r.barre_id == b.id), None)
                if r:
                    hover += (f"<br>─────────────<br>"
                              f"Mu : {r.Mu:.2f} kN.m<br>"
                              f"As long. : {r.As_long:.2f} cm²<br>"
                              f"At/st : {r.At_st:.2f} cm²/m<br>"
                              f"{'⚠ REVOIR' if r.alerte else '✓ OK'}")

            # Milieu de la poutre pour le label
            mx = (ni.x + nj.x) / 2
            my = (ni.y + nj.y) / 2
            mz = (ni.z + nj.z) / 2

            # Ligne de la poutre
            fig.add_trace(go.Scatter3d(
                x=[ni.x, nj.x], y=[ni.y, nj.y], z=[ni.z, nj.z],
                mode="lines",
                line=dict(color=color, width=5),
                name="Poutre", legendgroup="poutres",
                showlegend=first_p,
                hovertext=hover, hoverinfo="text"
            ))
            first_p = False

            # Option D — label au milieu de la poutre
            if show_labels and label_type in ("Poutres", "Poutres + Poteaux", "Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[mx], y=[my], z=[mz + 0.05],
                    mode="text",
                    text=[f"P{b.id}"],
                    textfont=dict(size=8, color=COL_POUTRE),
                    showlegend=False,
                    hoverinfo="skip"
                ))

    # ── Poteaux ────────────────────────────────────────────────────────────────
    if show_poteau:
        first_c = True
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

            # Option B — survol enrichi
            hover = (f"<b>C{b.id} — {b.nom}</b><br>"
                     f"Section : {b.b*100:.0f}×{b.h*100:.0f} cm<br>"
                     f"Niveau : {b.niveau}<br>"
                     f"Nœuds : {b.ni} → {b.nj}<br>"
                     f"Hauteur : {b.longueur:.2f} m")
            if show_resultats and res:
                r = next((r for r in res.poteaux if r.barre_id == b.id), None)
                if r:
                    hover += (f"<br>─────────────<br>"
                              f"Nu : {r.Nu:.1f} kN<br>"
                              f"As : {r.As:.2f} cm²<br>"
                              f"α : {r.alpha:.3f}  λ : {r.lam:.0f}<br>"
                              f"{'⚠ '+r.vS if r.alerte_am else '✓ OK'}")

            # Milieu du poteau pour le label
            mx = (ni.x + nj.x) / 2
            my = (ni.y + nj.y) / 2
            mz = (ni.z + nj.z) / 2

            fig.add_trace(go.Scatter3d(
                x=[ni.x, nj.x], y=[ni.y, nj.y], z=[ni.z, nj.z],
                mode="lines",
                line=dict(color=color, width=8),
                name="Poteau", legendgroup="poteaux",
                showlegend=first_c,
                hovertext=hover, hoverinfo="text"
            ))
            first_c = False

            # Option D — label au milieu du poteau
            if show_labels and label_type in ("Poteaux", "Poutres + Poteaux", "Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[mx + 0.05], y=[my + 0.05], z=[mz],
                    mode="text",
                    text=[f"C{b.id}"],
                    textfont=dict(size=8, color=COL_POTEAU),
                    showlegend=False,
                    hoverinfo="skip"
                ))

    # ── Dalles ─────────────────────────────────────────────────────────────────
    if show_dalles:
        first_d = True
        for d in projet.dalles:
            pts = [noeud_map.get(nid) for nid in d.noeuds if nid in noeud_map]
            if len(pts) < 3:
                continue
            xs = [p.x for p in pts] + [pts[0].x]
            ys = [p.y for p in pts] + [pts[0].y]
            zs = [p.z for p in pts] + [pts[0].z]

            # Option B — survol enrichi dalle
            hover_d = (f"<b>D{d.id}</b><br>"
                       f"Type : {d.type_dalle}<br>"
                       f"Sens : {d.sens_lx}<br>"
                       f"G = {d.G:.1f} kN/m²  Q = {d.Q:.1f} kN/m²<br>"
                       f"lx = {d.lx:.2f}m  ly = {d.ly:.2f}m<br>"
                       f"Nœuds : {d.noeuds}")
            if show_resultats and res:
                r = next((r for r in res.dalles if r.dalle_id == d.id), None)
                if r:
                    hover_d += (f"<br>─────────────<br>"
                                f"{r.typH}<br>"
                                f"As nerv. : {r.As_nerv:.2f} cm²<br>"
                                f"{'⚠ REVOIR' if r.alerte else '✓ OK'}")

            fig.add_trace(go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                line=dict(color="rgba(100,160,220,0.6)", width=2),
                name="Dalle", legendgroup="dalles",
                showlegend=first_d,
                hovertext=hover_d, hoverinfo="text"
            ))
            first_d = False

            # Surface transparente
            if len(pts) >= 3:
                for i in range(1, len(pts) - 1):
                    fig.add_trace(go.Mesh3d(
                        x=[pts[0].x, pts[i].x, pts[i+1].x if i+1 < len(pts) else pts[0].x],
                        y=[pts[0].y, pts[i].y, pts[i+1].y if i+1 < len(pts) else pts[0].y],
                        z=[pts[0].z, pts[i].z, pts[i+1].z if i+1 < len(pts) else pts[0].z],
                        color="lightblue", opacity=0.15,
                        showscale=False, hoverinfo="skip",
                        showlegend=False,
                    ))

            # Option D — label au centre de la dalle
            if show_labels and label_type in ("Dalles", "Tout"):
                cx = sum(p.x for p in pts) / len(pts)
                cy = sum(p.y for p in pts) / len(pts)
                cz = sum(p.z for p in pts) / len(pts)
                fig.add_trace(go.Scatter3d(
                    x=[cx], y=[cy], z=[cz + 0.05],
                    mode="text",
                    text=[f"D{d.id}"],
                    textfont=dict(size=8, color="rgba(0,100,200,0.8)"),
                    showlegend=False,
                    hoverinfo="skip"
                ))

    # ── Nœuds ──────────────────────────────────────────────────────────────────
    if show_noeuds:
        xs = [n.x for n in projet.noeuds]
        ys = [n.y for n in projet.noeuds]
        zs = [n.z for n in projet.noeuds]
        hover_n = [f"N{n.id} ({n.x:.1f}, {n.y:.1f}, {n.z:.1f})"
                   for n in projet.noeuds]
        ids_txt = [str(n.id) for n in projet.noeuds]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers+text" if show_labels else "markers",
            marker=dict(size=4, color="black"),
            text=ids_txt if show_labels else None,
            textposition="top center",
            textfont=dict(size=8),
            name="Nœuds",
            hovertext=hover_n, hoverinfo="text"
        ))

    # ── Mise en page ───────────────────────────────────────────────────────────
    fig.update_layout(
        height=620,
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
        hoverlabel=dict(
            bgcolor="white",
            font_size=11,
            font_family="Arial"
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Légende couleurs ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='display:flex;gap:24px;font-size:0.83rem;margin-top:4px;
                flex-wrap:wrap;color:#444'>
        <span>🟦 Poutres</span>
        <span>🟨 Poteaux</span>
        <span>🟦 Dalles</span>
        <span>🔴 Alertes (REVOIR)</span>
        <span style='color:#888;font-style:italic'>
            💡 Survolez un élément pour voir ses détails
        </span>
    </div>""", unsafe_allow_html=True)

    # ── Stats ──────────────────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nœuds",   len(projet.noeuds))
    c2.metric("Poutres",  sum(1 for b in projet.barres if b.type_elem=="poutre"))
    c3.metric("Poteaux",  sum(1 for b in projet.barres if b.type_elem=="poteau"))
    c4.metric("Dalles",   len(projet.dalles))
