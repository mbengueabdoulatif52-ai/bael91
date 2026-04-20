"""
ui/visualisation.py
Visualisation 3D de la structure avec Plotly
v3.8 : Amorces auto (IDs négatifs), semelles excentriques corrigées,
       vue volumétrique améliorée, semelles + longrines à Z=-Df
"""
import streamlit as st
from pathlib import Path
import sys
import math
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False


# ── Helpers géométrie ─────────────────────────────────────────────────────────
def _prisme(cx, cy, z_bas, z_haut, bx, by, color, opacity=0.85):
    """Prisme rectangulaire vertical via Mesh3d."""
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


def _prisme_horiz(x1,y1,x2,y2, z_bas, z_haut, larg, color, opacity=0.80):
    """Prisme rectangulaire horizontal (poutre) entre deux points."""
    dx = x2 - x1; dy = y2 - y1
    L = math.sqrt(dx**2 + dy**2)
    if L < 0.01:
        return None
    # Vecteur perpendiculaire
    nx = -dy/L * larg/2; ny = dx/L * larg/2
    # 8 sommets
    x = [x1+nx, x1-nx, x2-nx, x2+nx,
         x1+nx, x1-nx, x2-nx, x2+nx]
    y = [y1+ny, y1-ny, y2-ny, y2+ny,
         y1+ny, y1-ny, y2-ny, y2+ny]
    z = [z_bas]*4 + [z_haut]*4
    i = [0,0,0,1,1,2,4,4,4,5,5,6]
    j = [1,2,4,2,5,3,5,6,0,6,1,7]
    k = [2,3,5,5,6,7,6,7,7,2,2,3]
    return go.Mesh3d(x=x,y=y,z=z,i=i,j=j,k=k,
                     color=color,opacity=opacity,flatshading=True,
                     showscale=False,hoverinfo="skip",showlegend=False,
                     lighting=dict(ambient=0.7,diffuse=0.5))


def _generer_amorces(projet, Df):
    """
    Génère automatiquement les amorces pour chaque poteau de niveau 1.
    IDs négatifs pour éviter tout conflit avec les éléments saisis.
    Retourne (noeuds_virtuels, barres_amorces)
    """
    from core.topologie import index_noeud
    noeud_map = {n.id: n for n in projet.noeuds}

    poteaux_n1 = [b for b in projet.barres
                  if b.type_elem == "poteau" and b.niveau == 1]

    noeuds_virtuels = {}  # id_negatif → (x, y, z)
    barres_amorces  = []  # dict avec infos

    for b in poteaux_n1:
        ni = noeud_map.get(b.ni)
        if not ni:
            continue
        # Nœud virtuel à Z = -Df (même X, Y que le pied du poteau)
        id_nv = -b.id  # ID négatif
        noeuds_virtuels[id_nv] = (ni.x, ni.y, -Df)

        barres_amorces.append({
            'id':    -b.id,
            'nom':   f"Amorce_{b.nom}",
            'pot_id': b.id,
            'pot_nom': b.nom,
            'ni_id': id_nv,       # nœud virtuel à Z=-Df
            'nj_id': b.ni,        # nœud réel à Z=0
            'x':     ni.x,
            'y':     ni.y,
            'z_bas': -Df,
            'z_haut': 0.0,
            'b':     b.b,
            'h':     b.h,
        })

    return noeuds_virtuels, barres_amorces


def _centre_semelle(n_base, s):
    """
    Calcule le centre réel de la semelle.
    Le centre = position du nœud amorce (= position du poteau) + excentricités signées.
    ex positif → décalage vers X croissants (droite)
    ex négatif → décalage vers X décroissants (gauche)
    ey positif → décalage vers Y croissants (haut)
    ey négatif → décalage vers Y décroissants (bas)
    """
    cx = n_base.x + s.ex   # signe respecté directement
    cy = n_base.y + s.ey   # signe respecté directement
    return cx, cy


# ── Page principale ───────────────────────────────────────────────────────────
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
    Df     = projet.materiaux.Df
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
        show_amorces = st.checkbox("Amorces",    res is not None)
        show_res     = st.checkbox("Résultats",  res is not None)
    with col4:
        show_vol     = st.checkbox("Vue volumétrique", False)
        show_labels  = st.checkbox("Étiquettes",       False)

    label_type = "Poutres + Poteaux"
    if show_labels:
        label_type = st.selectbox("Étiqueter",
            ["Poutres + Poteaux","Poutres","Poteaux",
             "Dalles","Fondations","Tout"],
            key="label_type")

    # Palette
    COL_POUTRE   = "#2E75B6"
    COL_POTEAU   = "#D4AF37"
    COL_AMORCE   = "#A0522D"   # marron clair
    COL_ALERTE   = "#E74C3C"
    COL_SEMELLE  = "#8B4513"
    COL_LONGRINE = "#FF8C00"
    COL_DALLE    = "lightblue"

    fig = go.Figure()

    # ══════════════════════════════════════════════════════════════════════════
    # POUTRES
    # ══════════════════════════════════════════════════════════════════════════
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
                     f"Section {b.b*100:.0f}×{b.h*100:.0f}cm  "
                     f"Niv={b.niveau}  L={b.longueur:.2f}m")
            if r_p:
                hover += (f"<br>────────<br>Mu={r_p.Mu:.2f}kN.m  "
                          f"As={r_p.As_long:.2f}cm²<br>"
                          f"{'⚠ REVOIR' if r_p.alerte else '✓ OK'}")

            mx=(ni.x+nj.x)/2; my=(ni.y+nj.y)/2; mz=ni.z

            if show_vol:
                t = _prisme_horiz(ni.x,ni.y,nj.x,nj.y,
                                  mz-b.h, mz, b.b, color, 0.85)
                if t: fig.add_trace(t)
                # Ligne axe pour survol
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[mz,mz],
                    mode="lines",line=dict(color=color,width=1),
                    name="Poutre",legendgroup="poutres",
                    showlegend=first_p,
                    hovertext=hover,hoverinfo="text"))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=5),
                    name="Poutre",legendgroup="poutres",
                    showlegend=first_p,
                    hovertext=hover,hoverinfo="text"))
            first_p = False

            if show_labels and label_type in ("Poutres","Poutres + Poteaux","Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[(ni.x+nj.x)/2],y=[(ni.y+nj.y)/2],z=[mz+0.05],
                    mode="text",text=[b.nom],
                    textfont=dict(size=7,color=COL_POUTRE),
                    showlegend=False,hoverinfo="skip"))

    # ══════════════════════════════════════════════════════════════════════════
    # POTEAUX
    # ══════════════════════════════════════════════════════════════════════════
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
                     f"Section {b.b*100:.0f}×{b.h*100:.0f}cm  "
                     f"Niv={b.niveau}  H={b.longueur:.2f}m")
            if r_c:
                hover += (f"<br>────────<br>Nu={r_c.Nu:.1f}kN  "
                          f"As={r_c.As:.2f}cm²<br>"
                          f"λ={r_c.lam:.0f}  α={r_c.alpha:.3f}<br>"
                          f"{'⚠ REVOIR' if r_c.alerte_am else '✓ OK'}")

            mx=(ni.x+nj.x)/2; my=(ni.y+nj.y)/2; mz=(ni.z+nj.z)/2

            if show_vol:
                fig.add_trace(_prisme(ni.x,ni.y,ni.z,nj.z,
                                      b.b,b.h,color,0.90))
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=1),
                    name="Poteau",legendgroup="poteaux",
                    showlegend=first_c,
                    hovertext=hover,hoverinfo="text"))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[ni.x,nj.x],y=[ni.y,nj.y],z=[ni.z,nj.z],
                    mode="lines",line=dict(color=color,width=8),
                    name="Poteau",legendgroup="poteaux",
                    showlegend=first_c,
                    hovertext=hover,hoverinfo="text"))
            first_c = False

            if show_labels and label_type in ("Poteaux","Poutres + Poteaux","Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[mx+0.05],y=[my+0.05],z=[mz],
                    mode="text",text=[b.nom],
                    textfont=dict(size=7,color=COL_POTEAU),
                    showlegend=False,hoverinfo="skip"))

    # ══════════════════════════════════════════════════════════════════════════
    # AMORCES — Générées automatiquement (IDs négatifs)
    # ══════════════════════════════════════════════════════════════════════════
    if show_amorces:
        _, barres_amorces = _generer_amorces(projet, Df)
        first_am = True

        for am in barres_amorces:
            # Informations amorce depuis les résultats
            r_am = None
            if res:
                r_am = next((r for r in res.poteaux
                             if r.barre_id==am['pot_id']), None)

            hover_am = (f"<b>Amorce — {am['pot_nom']}</b><br>"
                        f"Section {am['b']*100:.0f}×{am['h']*100:.0f}cm<br>"
                        f"Z : {am['z_bas']:.2f}m → {am['z_haut']:.2f}m<br>"
                        f"(ID barre : {am['id']})")
            if r_am:
                hover_am += (f"<br>────────<br>"
                             f"Amorces : 4HA{r_am.phi_am}  "
                             f"ls={r_am.ls_am*100:.0f}cm")

            if show_vol:
                fig.add_trace(_prisme(am['x'],am['y'],
                                      am['z_bas'],am['z_haut'],
                                      am['b'],am['h'],
                                      COL_AMORCE, 0.80))
                fig.add_trace(go.Scatter3d(
                    x=[am['x'],am['x']],
                    y=[am['y'],am['y']],
                    z=[am['z_bas'],am['z_haut']],
                    mode="lines",line=dict(color=COL_AMORCE,width=1),
                    name="Amorce",legendgroup="amorces",
                    showlegend=first_am,
                    hovertext=hover_am,hoverinfo="text"))
            else:
                fig.add_trace(go.Scatter3d(
                    x=[am['x'],am['x']],
                    y=[am['y'],am['y']],
                    z=[am['z_bas'],am['z_haut']],
                    mode="lines",
                    line=dict(color=COL_AMORCE,width=5,dash="dash"),
                    name="Amorce",legendgroup="amorces",
                    showlegend=first_am,
                    hovertext=hover_am,hoverinfo="text"))
            first_am = False

            if show_labels and label_type in ("Fondations","Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[am['x']+0.05],y=[am['y']+0.05],
                    z=[am['z_bas']+Df/2],
                    mode="text",text=[f"Am{am['pot_id']}"],
                    textfont=dict(size=6,color=COL_AMORCE),
                    showlegend=False,hoverinfo="skip"))

    # ══════════════════════════════════════════════════════════════════════════
    # DALLES
    # ══════════════════════════════════════════════════════════════════════════
    if show_dalles:
        first_d = True
        for d in projet.dalles:
            pts = [noeud_map.get(nid) for nid in d.noeuds
                   if nid in noeud_map]
            if len(pts) < 3: continue
            xs=[p.x for p in pts]+[pts[0].x]
            ys=[p.y for p in pts]+[pts[0].y]
            zs=[p.z for p in pts]+[pts[0].z]

            hover_d = (f"<b>D{d.id}</b>  {d.type_dalle}  {d.sens_lx}<br>"
                       f"G={d.G:.1f}kN/m²  Q={d.Q:.1f}kN/m²")
            if show_res and res:
                r_d = next((r for r in res.dalles
                            if r.dalle_id==d.id),None)
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
                p0=pts[0]; pi=pts[i]
                pi1=pts[i+1] if i+1<len(pts) else pts[0]
                if show_vol:
                    fig.add_trace(go.Mesh3d(
                        x=[p0.x,pi.x,pi1.x,p0.x,pi.x,pi1.x],
                        y=[p0.y,pi.y,pi1.y,p0.y,pi.y,pi1.y],
                        z=[p0.z,pi.z,pi1.z,
                           p0.z-h_d,pi.z-h_d,pi1.z-h_d],
                        color=COL_DALLE,opacity=0.25,
                        showscale=False,hoverinfo="skip",
                        showlegend=False))
                else:
                    fig.add_trace(go.Mesh3d(
                        x=[p0.x,pi.x,pi1.x],
                        y=[p0.y,pi.y,pi1.y],
                        z=[p0.z,pi.z,pi1.z],
                        color=COL_DALLE,opacity=0.15,
                        showscale=False,hoverinfo="skip",
                        showlegend=False))

            if show_labels and label_type in ("Dalles","Tout"):
                cx=sum(p.x for p in pts)/len(pts)
                cy=sum(p.y for p in pts)/len(pts)
                cz=sum(p.z for p in pts)/len(pts)
                fig.add_trace(go.Scatter3d(
                    x=[cx],y=[cy],z=[cz+0.05],
                    mode="text",text=[f"D{d.id}"],
                    textfont=dict(size=7,color="rgba(0,100,200,0.8)"),
                    showlegend=False,hoverinfo="skip"))

    # ══════════════════════════════════════════════════════════════════════════
    # NŒUDS
    # ══════════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════════
    # FONDATIONS — Semelles excentriques corrigées + Longrines
    # ══════════════════════════════════════════════════════════════════════════
    if show_fond and res and res.semelles:
        pots_n1 = {b.id: b for b in projet.barres
                   if b.type_elem=="poteau" and b.niveau==1}
        first_sem = True; first_lon = True

        for s in res.semelles:
            pot = pots_n1.get(s.id_poteau)
            if not pot: continue
            n_base = noeud_map.get(pot.ni)
            if not n_base: continue

            # Centre réel de la semelle (excentricité corrigée)
            cx, cy = _centre_semelle(n_base, s)
            B  = max(s.B, 0.40)
            L  = max(s.L_sem, 0.40)
            e  = max(s.e_sem, 0.15)
            z_top = z_fond
            z_bot = z_fond - e
            col_s = COL_ALERTE if s.alerte else COL_SEMELLE

            hover_s = (f"<b>Semelle C{s.id_poteau}</b><br>"
                       f"{'Excentrique' if s.ex!=0 or s.ey!=0 else 'Centrée'}"
                       f"  ex={abs(s.ex):.2f}m  ey={abs(s.ey):.2f}m<br>"
                       f"B×L={B:.2f}×{L:.2f}m  e={e*100:.0f}cm<br>"
                       f"Nu={s.Nu_ser:.1f}kN  q_max={s.q_max:.0f}kN/m²<br>"
                       f"Asx={s.Asx:.2f}cm²/m<br>"
                       f"{'⚠ '+s.alerte if s.alerte else '✓ OK'}")

            if show_vol:
                fig.add_trace(_prisme(cx,cy,z_bot,z_top,B,L,col_s,0.80))
                fig.add_trace(go.Scatter3d(
                    x=[cx],y=[cy],z=[z_top],mode="markers",
                    marker=dict(size=5,color=col_s),
                    name="Semelle",legendgroup="semelles",
                    showlegend=first_sem,
                    hovertext=hover_s,hoverinfo="text"))
            else:
                dx,dy = B/2, L/2
                xs_s=[cx-dx,cx+dx,cx+dx,cx-dx,cx-dx]
                ys_s=[cy-dy,cy-dy,cy+dy,cy+dy,cy-dy]
                fig.add_trace(go.Scatter3d(
                    x=xs_s,y=ys_s,z=[z_top]*5,
                    mode="lines",line=dict(color=col_s,width=4),
                    name="Semelle",legendgroup="semelles",
                    showlegend=first_sem,
                    hovertext=hover_s,hoverinfo="text"))
                fig.add_trace(go.Mesh3d(
                    x=[cx-dx,cx+dx,cx+dx,cx-dx],
                    y=[cy-dy,cy-dy,cy+dy,cy+dy],
                    z=[z_top]*4,
                    color=col_s,opacity=0.45,
                    showscale=False,hoverinfo="skip",showlegend=False))
            first_sem = False

            # Ligne axe poteau → semelle (montre l'excentricité)
            fig.add_trace(go.Scatter3d(
                x=[n_base.x, cx],
                y=[n_base.y, cy],
                z=[0.0, z_top],
                mode="lines",
                line=dict(color=COL_POTEAU,width=2,dash="dot"),
                showlegend=False,hoverinfo="skip"))

            if show_labels and label_type in ("Fondations","Tout"):
                fig.add_trace(go.Scatter3d(
                    x=[cx],y=[cy],z=[z_top-0.12],
                    mode="text",text=[f"C{s.id_poteau}"],
                    textfont=dict(size=7,color=COL_SEMELLE),
                    showlegend=False,hoverinfo="skip"))

            # ── Longrines ────────────────────────────────────────────────────
            for direction, As_l, vers_id, e_val, Mu_l in [
                ("X", s.long_X_As, s.long_X_vers, s.ex, s.long_X_Mu),
                ("Y", s.long_Y_As, s.long_Y_vers, s.ey, s.long_Y_Mu),
            ]:
                if As_l <= 0 or vers_id <= 0: continue
                pot2 = pots_n1.get(vers_id)
                if not pot2: continue
                n2   = noeud_map.get(pot2.ni)
                if not n2: continue

                # Centre de la semelle voisine
                s2 = next((ss for ss in res.semelles
                           if ss.id_poteau==vers_id), None)
                if s2:
                    cx2,cy2 = _centre_semelle(n2,s2)
                else:
                    cx2,cy2 = n2.x, n2.y

                hover_l = (f"<b>Longrine C{s.id_poteau}→C{vers_id}</b><br>"
                           f"Direction {direction}  e={e_val:+.3f}m<br>"
                           f"M={Mu_l:.1f}kN.m<br>"
                           f"As long.={As_l:.2f}cm²  "
                           f"As chap.={As_l*0.5:.2f}cm²")

                if show_vol:
                    b_l = (s.b_long_X if direction=="X"
                           else s.b_long_Y) or 0.25
                    h_l = (s.h_long_X if direction=="X"
                           else s.h_long_Y) or 0.40
                    t = _prisme_horiz(cx,cy,cx2,cy2,
                                      z_top-h_l,z_top,b_l,
                                      COL_LONGRINE,0.80)
                    if t: fig.add_trace(t)

                # La longrine relie les nœuds amorces (position des poteaux)
                # pas les centres des semelles
                fig.add_trace(go.Scatter3d(
                    x=[n_base.x, n2.x],
                    y=[n_base.y, n2.y],
                    z=[z_top, z_top],
                    mode="lines",line=dict(color=COL_LONGRINE,width=6),
                    name="Longrine",legendgroup="longrines",
                    showlegend=first_lon,
                    hovertext=hover_l,hoverinfo="text"))
                first_lon = False

                if show_labels and label_type in ("Fondations","Tout"):
                    fig.add_trace(go.Scatter3d(
                        x=[(cx+cx2)/2],y=[(cy+cy2)/2],
                        z=[z_top+0.08],
                        mode="text",text=[f"L{direction}"],
                        textfont=dict(size=7,color=COL_LONGRINE),
                        showlegend=False,hoverinfo="skip"))

    # ── Mise en page ──────────────────────────────────────────────────────────
    scene = dict(
        xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)",
        aspectmode="data", bgcolor="white")
    if show_fond or show_amorces:
        scene["zaxis"] = dict(range=[z_fond-0.5, None])

    fig.update_layout(
        height=720, showlegend=True,
        legend=dict(x=0,y=1,bgcolor="rgba(255,255,255,0.88)",
                    bordercolor="#ccc",borderwidth=1),
        scene=scene,
        margin=dict(l=0,r=0,b=0,t=30),
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white",font_size=11,font_family="Arial"))

    st.plotly_chart(fig, use_container_width=True)

    # Légende
    leg = ("🟦 Poutres &nbsp; 🟨 Poteaux &nbsp; 🩵 Dalles")
    if show_amorces: leg += " &nbsp; 🟤 Amorces"
    if show_fond:    leg += " &nbsp; 🟫 Semelles &nbsp; 🟠 Longrines"
    leg += (" &nbsp; 🔴 Alertes"
            " &nbsp; <i style='color:#888'>💡 Survolez pour détails</i>")
    st.markdown(
        f"<div style='font-size:0.83rem;color:#444;margin-top:4px'>"
        f"{leg}</div>", unsafe_allow_html=True)

    st.divider()
    cols = st.columns(5)
    cols[0].metric("Nœuds",    len(projet.noeuds))
    cols[1].metric("Poutres",  sum(1 for b in projet.barres
                                   if b.type_elem=="poutre"))
    cols[2].metric("Poteaux",  sum(1 for b in projet.barres
                                   if b.type_elem=="poteau"))
    cols[3].metric("Dalles",   len(projet.dalles))
    cols[4].metric("Semelles", len(res.semelles) if res else 0)
