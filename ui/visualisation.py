"""
ui/visualisation.py
Visualisation 3D de la structure avec Plotly
v3 : Semelles + longrines à Z=-Df, vue volumétrique, labels, survol enrichi
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


def _boite(cx, cy, z_bas, z_haut, bx, by, color, opacity=0.85):
    """Prisme rectangulaire volumétrique via Mesh3d."""
    dx, dy = bx/2, by/2
    x = [cx-dx,cx+dx,cx+dx,cx-dx, cx-dx,cx+dx,cx+dx,cx-dx]
    y = [cy-dy,cy-dy,cy+dy,cy+dy, cy-dy,cy-dy,cy+dy,cy+dy]
    z = [z_bas]*4 + [z_haut]*4
    i = [0,0,0,1,1,2,4,4,4,5,5,6]
    j = [1,2,4,2,5,3,5,6,0,6,1,7]
    k = [2,3,5,5,6,7,6,7,7,2,2,3]
    return go.Mesh3d(x=x,y=y,z=z,i=i,j=j,k=k,
                     color=color,opacity=opacity,flatshading=True,
                     showscale=False,hoverinfo="skip",showlegend=False,
                     lighting=dict(ambient=0.7,diffuse=0.5))


def page_visualisation(projet, res=None):
    st.markdown("## 🔷 Visualisation 3D de la structure")

    if projet is None or not projet.noeuds:
        st.warning("Aucun projet ou nœuds définis.")
        return
    if not PLOTLY_OK:
        st.error("Plotly non disponible. pip install plotly")
        return

    from core.topologie import calc_niveaux, calc_barres, calc_dalles
    calc_niveaux(projet); calc_barres(projet); calc_dalles(projet)

    noeud_map = {n.id: n for n in projet.noeuds}
    Df    = projet.materiaux.Df
    z_fond = -Df

    # ── Options ───────────────────────────────────────────────────────────────
    col1,col2,col3,col4 = st.columns(4)
    with col1:
        show_poutre  = st.checkbox("Poutres",    True)
        show_poteau  = st.checkbox("Poteaux",    True)
    with col2:
        show_dalles  = st.checkbox("Dalles",     True)
        show_noeuds  = st.checkbox("Nœuds",      False)
    with col3:
        show_fond    = st.checkbox("Fondations", res is not None)
        show_res     = st.checkbox("Colorer résultats", res is not None)
    with col4:
        show_vol     = st.checkbox("Vue volumétrique", False)
        show_labels  = st.checkbox("Étiquettes",       False)

    label_type = "Poutres + Poteaux"
    if show_labels:
        label_type = st.selectbox("Étiqueter",
            ["Poutres + Poteaux","Poutres","Poteaux","Dalles","Fondations","Tout"],
            key="label_type")

    COL_POUTRE   = "#2E75B6"
    COL_POTEAU   = "#D4AF37"
    COL_ALERTE   = "#E74C3C"
    COL_SEMELLE  = "#8B4513"
    COL_LONGRINE = "#FF8C00"
    COL_DALLE    = "lightblue"

    fig = go.Figure()

    # ── Poutres ───────────────────────────────────────────────────────────────
    if show_poutre:
        first_p = True
        for b in projet.barres:
            if b.type_elem != "poutre": continue
            ni = noeud_map.get(b.ni); nj = noeud_map.get(b.nj)
            if not ni or not nj: continue

            color = COL_POUTRE; r_p = None
            if show_res and res:
                r_p = next((r for r in res.poutres if r.barre_id==b.id),None)
                if r_p and r_p.alerte: color = COL_ALERTE

            hover = (f"<b>{b.nom}({b.ni}-{b.nj})</b><br>"
                     f"Section : {b.b*100:.0f}×{b.h*100:.0f}cm  Niv={b.niveau}<br>"
                     f"L={b.longueur:.2f}m  G_add={b.G_add:.1f}kN/m")
            if r_p:
                hover += (f"<br>────────<br>Mu={r_p.Mu:.2f}kN.m  "
                          f"As={r_p.As_long:.2f}cm²<br>"
                          f"{'⚠ REVOIR' if r_p.alerte else '✓ OK'}")

            mx=(ni.x+nj.x)/2; my=(ni.y+nj.y)/2; mz=(ni.z+nj.z)/2

            if show_vol:
                fig.add_trace(_boite(mx,my, ni.z-b.h,ni.z,
                                     b.longueur,b.b, color,0.80))
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=2),
                    name="Poutre",legendgroup="poutres",showlegend=first_p,
                    hovertext=hover,hoverinfo="text"))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=5),
                    name="Poutre",legendgroup="poutres",showlegend=first_p,
                    hovertext=hover,hoverinfo="text"))
            first_p = False

            if show_labels and label_type in ("Poutres","Poutres + Poteaux","Tout"):
                fig.add_trace(go.Scatter3d(x=[mx],y=[my],z=[mz+0.05],
                    mode="text",text=[b.nom],
                    textfont=dict(size=7,color=COL_POUTRE),
                    showlegend=False,hoverinfo="skip"))

    # ── Poteaux ───────────────────────────────────────────────────────────────
    if show_poteau:
        first_c = True
        for b in projet.barres:
            if b.type_elem != "poteau": continue
            ni = noeud_map.get(b.ni); nj = noeud_map.get(b.nj)
            if not ni or not nj: continue

            color = COL_POTEAU; r_c = None
            if show_res and res:
                r_c = next((r for r in res.poteaux if r.barre_id==b.id),None)
                if r_c and r_c.alerte_am: color = COL_ALERTE

            hover = (f"<b>{b.nom}({b.ni}-{b.nj})</b><br>"
                     f"Section : {b.b*100:.0f}×{b.h*100:.0f}cm  Niv={b.niveau}<br>"
                     f"H={b.longueur:.2f}m")
            if r_c:
                hover += (f"<br>────────<br>Nu={r_c.Nu:.1f}kN  As={r_c.As:.2f}cm²<br>"
                          f"λ={r_c.lam:.0f}  α={r_c.alpha:.3f}<br>"
                          f"{'⚠ REVOIR' if r_c.alerte_am else '✓ OK'}")

            mx=(ni.x+nj.x)/2; my=(ni.y+nj.y)/2; mz=(ni.z+nj.z)/2

            if show_vol:
                fig.add_trace(_boite(ni.x,ni.y,ni.z,nj.z,
                                     b.b,b.h, color,0.85))
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=2),
                    name="Poteau",legendgroup="poteaux",showlegend=first_c,
                    hovertext=hover,hoverinfo="text"))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=8),
                    name="Poteau",legendgroup="poteaux",showlegend=first_c,
                    hovertext=hover,hoverinfo="text"))
            first_c = False

            if show_labels and label_type in ("Poteaux","Poutres + Poteaux","Tout"):
                fig.add_trace(go.Scatter3d(x=[mx+0.05],y=[my+0.05],z=[mz],
                    mode="text",text=[b.nom],
                    textfont=dict(size=7,color=COL_POTEAU),
                    showlegend=False,hoverinfo="skip"))

    # ── Dalles ────────────────────────────────────────────────────────────────
    if show_dalles:
        first_d = True
        for d in projet.dalles:
            pts = [noeud_map.get(nid) for nid in d.noeuds if nid in noeud_map]
            if len(pts) < 3: continue
            xs=[p.x for p in pts]+[pts[0].x]
            ys=[p.y for p in pts]+[pts[0].y]
            zs=[p.z for p in pts]+[pts[0].z]

            hover_d = (f"<b>D{d.id}</b>  {d.type_dalle}  Sens:{d.sens_lx}<br>"
                       f"G={d.G:.1f}kN/m²  Q={d.Q:.1f}kN/m²<br>"
                       f"lx={d.lx:.2f}m  ly={d.ly:.2f}m")
            if show_res and res:
                r_d = next((r for r in res.dalles if r.dalle_id==d.id),None)
                if r_d:
                    hover_d += (f"<br>────────<br>{r_d.typH}  "
                                f"As={r_d.As_nerv:.2f}cm²<br>"
                                f"{'⚠ REVOIR' if r_d.alerte else '✓ OK'}")

            fig.add_trace(go.Scatter3d(
                x=xs,y=ys,z=zs,mode="lines",
                line=dict(color="rgba(100,160,220,0.6)",width=2),
                name="Dalle",legendgroup="dalles",showlegend=first_d,
                hovertext=hover_d,hoverinfo="text"))
            first_d = False

            h_d = d.e_dalle if d.e_dalle > 0 else 0.20
            for i in range(1,len(pts)-1):
                p0=pts[0]; pi=pts[i]; pi1=pts[i+1] if i+1<len(pts) else pts[0]
                if show_vol:
                    fig.add_trace(go.Mesh3d(
                        x=[p0.x,pi.x,pi1.x,p0.x,pi.x,pi1.x],
                        y=[p0.y,pi.y,pi1.y,p0.y,pi.y,pi1.y],
                        z=[p0.z,pi.z,pi1.z,
                           p0.z-h_d,pi.z-h_d,pi1.z-h_d],
                        color=COL_DALLE,opacity=0.25,
                        showscale=False,hoverinfo="skip",showlegend=False))
                else:
                    fig.add_trace(go.Mesh3d(
                        x=[p0.x,pi.x,pi1.x],y=[p0.y,pi.y,pi1.y],
                        z=[p0.z,pi.z,pi1.z],
                        color=COL_DALLE,opacity=0.15,
                        showscale=False,hoverinfo="skip",showlegend=False))

            if show_labels and label_type in ("Dalles","Tout"):
                cx=sum(p.x for p in pts)/len(pts)
                cy=sum(p.y for p in pts)/len(pts)
                cz=sum(p.z for p in pts)/len(pts)
                fig.add_trace(go.Scatter3d(x=[cx],y=[cy],z=[cz+0.05],
                    mode="text",text=[f"D{d.id}"],
                    textfont=dict(size=7,color="rgba(0,100,200,0.8)"),
                    showlegend=False,hoverinfo="skip"))

    # ── Nœuds ─────────────────────────────────────────────────────────────────
    if show_noeuds:
        fig.add_trace(go.Scatter3d(
            x=[n.x for n in projet.noeuds],
            y=[n.y for n in projet.noeuds],
            z=[n.z for n in projet.noeuds],
            mode="markers+text" if show_labels else "markers",
            marker=dict(size=4,color="black"),
            text=[str(n.id) for n in projet.noeuds] if show_labels else None,
            textposition="top center",textfont=dict(size=8),
            name="Nœuds",
            hovertext=[f"N{n.id} ({n.x:.2f},{n.y:.2f},{n.z:.2f})"
                       for n in projet.noeuds],
            hoverinfo="text"))

    # ── Fondations : Semelles + Longrines ─────────────────────────────────────
    if show_fond and res and res.semelles:
        pots_n1 = {b.id: b for b in projet.barres
                   if b.type_elem=="poteau" and b.niveau==1}
        first_sem = True; first_lon = True

        for s in res.semelles:
            pot = pots_n1.get(s.id_poteau)
            if not pot: continue
            n_base = noeud_map.get(pot.ni)
            if not n_base: continue

            cx,cy = n_base.x, n_base.y
            B  = max(s.B, 0.40)
            L  = max(s.L_sem, 0.40)
            e  = max(s.e_sem, 0.15)
            z_top = z_fond
            z_bot = z_fond - e
            col_s = COL_ALERTE if s.alerte else COL_SEMELLE

            hover_s = (f"<b>Semelle C{s.id_poteau}</b><br>"
                       f"{'Centrée' if s.ex==0 and s.ey==0 else 'Excentrique'}<br>"
                       f"B×L = {B:.2f}×{L:.2f}m  e={e*100:.0f}cm<br>"
                       f"Nu = {s.Nu_ser:.1f}kN<br>"
                       f"q_max = {s.q_max:.0f}kN/m²<br>"
                       f"Asx = {s.Asx:.2f}cm²/m<br>"
                       f"{'⚠ '+s.alerte if s.alerte else '✓ OK'}")

            if show_vol:
                fig.add_trace(_boite(cx,cy,z_bot,z_top,B,L,col_s,0.80))
                # Point de survol
                fig.add_trace(go.Scatter3d(
                    x=[cx],y=[cy],z=[z_top],mode="markers",
                    marker=dict(size=6,color=col_s),
                    name="Semelle",legendgroup="semelles",showlegend=first_sem,
                    hovertext=hover_s,hoverinfo="text"))
            else:
                dx,dy = B/2, L/2
                xs_s=[cx-dx,cx+dx,cx+dx,cx-dx,cx-dx]
                ys_s=[cy-dy,cy-dy,cy+dy,cy+dy,cy-dy]
                fig.add_trace(go.Scatter3d(
                    x=xs_s,y=ys_s,z=[z_top]*5,
                    mode="lines",line=dict(color=col_s,width=4),
                    name="Semelle",legendgroup="semelles",showlegend=first_sem,
                    hovertext=hover_s,hoverinfo="text"))
                fig.add_trace(go.Mesh3d(
                    x=[cx-dx,cx+dx,cx+dx,cx-dx],
                    y=[cy-dy,cy-dy,cy+dy,cy+dy],
                    z=[z_top]*4,
                    color=col_s,opacity=0.45,
                    showscale=False,hoverinfo="skip",showlegend=False))
            first_sem = False

            # Ligne verticale poteau → semelle
            fig.add_trace(go.Scatter3d(
                x=[cx,cx],y=[cy,cy],z=[0,z_top],
                mode="lines",line=dict(color=COL_POTEAU,width=3,dash="dot"),
                showlegend=False,hoverinfo="skip"))

            if show_labels and label_type in ("Fondations","Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[cx],y=[cy],z=[z_top-0.12],
                    mode="text",text=[f"C{s.id_poteau}"],
                    textfont=dict(size=7,color=COL_SEMELLE),
                    showlegend=False,hoverinfo="skip"))

            # Longrines
            for direction, As_l, vers_id, e_val, Mu_l in [
                ("X", s.long_X_As, s.long_X_vers, abs(s.ex), s.long_X_Mu),
                ("Y", s.long_Y_As, s.long_Y_vers, abs(s.ey), s.long_Y_Mu),
            ]:
                if As_l <= 0 or vers_id <= 0: continue
                pot2 = pots_n1.get(vers_id)
                if not pot2: continue
                n2 = noeud_map.get(pot2.ni)
                if not n2: continue

                hover_l = (f"<b>Longrine C{s.id_poteau}→C{vers_id}</b><br>"
                           f"Direction {direction}  e={e_val:.3f}m<br>"
                           f"M={Mu_l:.1f}kN.m<br>"
                           f"As long.={As_l:.2f}cm²  As chap.={As_l*0.5:.2f}cm²")

                if show_vol:
                    # Longrine volumétrique
                    import math
                    L_long = math.sqrt((n2.x-cx)**2+(n2.y-cy)**2)
                    mx_l=(cx+n2.x)/2; my_l=(cy+n2.y)/2
                    b_l = getattr(s,'b_long_X',0.25) if direction=="X" else getattr(s,'b_long_Y',0.25)
                    h_l = getattr(s,'h_long_X',0.40) if direction=="X" else getattr(s,'h_long_Y',0.40)
                    fig.add_trace(_boite(mx_l,my_l,z_top-h_l,z_top,
                                         L_long,b_l,COL_LONGRINE,0.75))

                fig.add_trace(go.Scatter3d(
                    x=[cx,n2.x],y=[cy,n2.y],z=[z_top,z_top],
                    mode="lines",line=dict(color=COL_LONGRINE,width=6),
                    name="Longrine",legendgroup="longrines",showlegend=first_lon,
                    hovertext=hover_l,hoverinfo="text"))
                first_lon = False

                if show_labels and label_type in ("Fondations","Tout"):
                    fig.add_trace(go.Scatter3d(
                        x=[(cx+n2.x)/2],y=[(cy+n2.y)/2],z=[z_top+0.08],
                        mode="text",text=[f"L{direction}"],
                        textfont=dict(size=7,color=COL_LONGRINE),
                        showlegend=False,hoverinfo="skip"))

    # ── Mise en page ──────────────────────────────────────────────────────────
    scene = dict(xaxis_title="X (m)",yaxis_title="Y (m)",zaxis_title="Z (m)",
                 aspectmode="data",bgcolor="white")
    if show_fond:
        scene["zaxis"] = dict(range=[z_fond-0.5, None])

    fig.update_layout(
        height=700,showlegend=True,
        legend=dict(x=0,y=1,bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="#ccc",borderwidth=1),
        scene=scene,
        margin=dict(l=0,r=0,b=0,t=30),
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white",font_size=11,font_family="Arial"))

    st.plotly_chart(fig, use_container_width=True)

    leg = "🟦 Poutres &nbsp; 🟨 Poteaux &nbsp; 🩵 Dalles"
    if show_fond: leg += " &nbsp; 🟫 Semelles &nbsp; 🟠 Longrines"
    leg += " &nbsp; 🔴 Alertes &nbsp; <i style='color:#888'>💡 Survolez pour les détails</i>"
    st.markdown(f"<div style='font-size:0.83rem;color:#444;margin-top:4px'>{leg}</div>",
                unsafe_allow_html=True)

    st.divider()
    cols = st.columns(5)
    cols[0].metric("Nœuds",    len(projet.noeuds))
    cols[1].metric("Poutres",  sum(1 for b in projet.barres if b.type_elem=="poutre"))
    cols[2].metric("Poteaux",  sum(1 for b in projet.barres if b.type_elem=="poteau"))
    cols[3].metric("Dalles",   len(projet.dalles))
    cols[4].metric("Semelles", len(res.semelles) if res else 0)
