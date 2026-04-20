"""
ui/escalier.py
Calculateur de charges d'escalier — Injection directe sur les poutres palières
Priorité 1 : Escalier en U symétrique (standard Dakar/Sénégal)
Priorité 2 : Escalier quart tournant
Priorité 3 : Volée droite simple
"""
import streamlit as st
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def page_escalier(projet=None):
    st.markdown("## 🪜 Calculateur de charges d'escalier")

    if projet is None or not projet.barres:
        st.warning("Chargez d'abord un projet pour pouvoir sélectionner "
                   "les poutres palières.")
        st.info("Vous pouvez quand même calculer les charges sans projet chargé.")

    mat_rho = 25.0  # kN/m³ béton armé

    # ── Type d'escalier ───────────────────────────────────────────────────────
    st.markdown("### 1. Type d'escalier")
    type_esc = st.radio(
        "Choisir le type",
        ["Escalier en U (2 volées + palier intermédiaire)",
         "Escalier quart tournant (1 volée + palier à 90°)",
         "Volée droite simple"],
        index=0,
        horizontal=True
    )

    st.divider()

    # ── Géométrie des marches ─────────────────────────────────────────────────
    st.markdown("### 2. Géométrie des marches")
    c1, c2, c3 = st.columns(3)
    with c1:
        h_marche = st.number_input("Hauteur de marche h (m)",
                                   value=0.17, step=0.01, format="%.2f")
    with c2:
        giron = st.number_input("Giron g (m)",
                                value=0.28, step=0.01, format="%.2f")
    with c3:
        e_paillasse = st.number_input("Épaisseur paillasse (m)",
                                      value=0.15, step=0.01, format="%.2f")

    # Calcul angle
    if giron > 0:
        alpha_rad = math.atan(h_marche / giron)
        alpha_deg = math.degrees(alpha_rad)
        cos_alpha = math.cos(alpha_rad)
    else:
        alpha_deg = 0; cos_alpha = 1.0

    # Vérification réglementaire
    rapport = h_marche / giron if giron > 0 else 0
    regle_blondel = 2 * h_marche + giron
    ok_blondel = 0.60 <= regle_blondel <= 0.65
    col_info = st.columns(4)
    col_info[0].metric("Angle α", f"{alpha_deg:.1f}°")
    col_info[1].metric("cos(α)", f"{cos_alpha:.3f}")
    col_info[2].metric("2h+g (Blondel)", f"{regle_blondel:.2f}m",
                       delta="OK ✓" if ok_blondel else "⚠ hors norme")
    col_info[3].metric("Pente", f"1/{giron/h_marche:.1f}" if h_marche > 0 else "—")

    st.divider()

    # ── Dimensions des volées et paliers ──────────────────────────────────────
    st.markdown("### 3. Dimensions")

    if "en U" in type_esc:
        # ── ESCALIER EN U ─────────────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Volée 1**")
            larg_v1   = st.number_input("Largeur volée (m)",
                                        value=1.20, step=0.05, format="%.2f",
                                        key="larg_v1")
            long_v1   = st.number_input("Longueur horizontale (m)",
                                        value=3.00, step=0.05, format="%.2f",
                                        key="long_v1")
            nb_m_v1   = st.number_input("Nb marches volée 1",
                                        value=9, step=1, min_value=1,
                                        key="nb_m_v1")
        with c2:
            volee2_identique = st.checkbox("Volée 2 identique à Volée 1",
                                           value=True)
            if volee2_identique:
                larg_v2 = larg_v1; long_v2 = long_v1; nb_m_v2 = nb_m_v1
                st.info("Volée 2 = Volée 1 ✓")
            else:
                st.markdown("**Volée 2**")
                larg_v2 = st.number_input("Largeur volée 2 (m)",
                                          value=1.20, step=0.05, format="%.2f",
                                          key="larg_v2")
                long_v2 = st.number_input("Longueur horizontale 2 (m)",
                                          value=3.00, step=0.05, format="%.2f",
                                          key="long_v2")
                nb_m_v2 = st.number_input("Nb marches volée 2",
                                          value=9, step=1, min_value=1,
                                          key="nb_m_v2")

        # Paliers
        st.markdown("**Paliers**")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            e_pal_dep  = st.number_input("Épaisseur palier départ (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_pal_dep")
            prof_pal_dep = st.number_input("Profondeur palier départ (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_dep")
        with cp2:
            e_pal_int  = st.number_input("Épaisseur palier intermédiaire (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_pal_int")
            prof_pal_int = st.number_input("Profondeur palier intermédiaire (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_int")
        with cp3:
            e_pal_arr  = st.number_input("Épaisseur palier arrivée (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_pal_arr")
            prof_pal_arr = st.number_input("Profondeur palier arrivée (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_arr")
        # Largeur paliers = largeur volée (hypothèse standard)
        larg_pal = larg_v1

    elif "quart" in type_esc.lower():
        # ── ESCALIER QUART TOURNANT ───────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            larg_v1  = st.number_input("Largeur volée (m)",
                                       value=1.20, step=0.05, format="%.2f",
                                       key="larg_v1_qt")
            long_v1  = st.number_input("Longueur horizontale (m)",
                                       value=3.00, step=0.05, format="%.2f",
                                       key="long_v1_qt")
            nb_m_v1  = st.number_input("Nb marches",
                                       value=9, step=1, min_value=1,
                                       key="nb_m_qt")
        with c2:
            e_pal_dep  = st.number_input("Épaisseur palier départ (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_dep_qt")
            prof_pal_dep = st.number_input("Profondeur palier départ (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_dep_qt")
            e_pal_arr  = st.number_input("Épaisseur palier arrivée (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_arr_qt")
            prof_pal_arr = st.number_input("Profondeur palier arrivée (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_arr_qt")
        larg_v2=larg_v1; long_v2=0; nb_m_v2=0
        e_pal_int=0; prof_pal_int=0; larg_pal=larg_v1

    else:
        # ── VOLÉE DROITE SIMPLE ───────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            larg_v1  = st.number_input("Largeur volée (m)",
                                       value=1.20, step=0.05, format="%.2f",
                                       key="larg_v1_s")
            long_v1  = st.number_input("Longueur horizontale (m)",
                                       value=3.00, step=0.05, format="%.2f",
                                       key="long_v1_s")
            nb_m_v1  = st.number_input("Nb marches",
                                       value=9, step=1, min_value=1,
                                       key="nb_m_s")
        with c2:
            e_pal_dep  = st.number_input("Épaisseur palier bas (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_dep_s")
            prof_pal_dep = st.number_input("Profondeur palier bas (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_dep_s")
            e_pal_arr  = st.number_input("Épaisseur palier haut (m)",
                                         value=0.15, step=0.01, format="%.2f",
                                         key="e_arr_s")
            prof_pal_arr = st.number_input("Profondeur palier haut (m)",
                                           value=1.20, step=0.05, format="%.2f",
                                           key="prof_arr_s")
        larg_v2=larg_v1; long_v2=0; nb_m_v2=0
        e_pal_int=0; prof_pal_int=0; larg_pal=larg_v1

    st.divider()

    # ── Charges ───────────────────────────────────────────────────────────────
    st.markdown("### 4. Charges")
    c1, c2, c3 = st.columns(3)
    with c1:
        G_rev = st.number_input("Revêtement G_rev (kN/m²)",
                                value=1.50, step=0.10, format="%.2f")
    with c2:
        usage = st.selectbox("Usage",
                             ["Habitation (Q=2.5)", "Bureaux (Q=2.5)",
                              "ERP/École (Q=4.0)", "Hôpital (Q=4.0)",
                              "Personnalisé"])
        Q_map = {"Habitation (Q=2.5)": 2.5, "Bureaux (Q=2.5)": 2.5,
                 "ERP/École (Q=4.0)": 4.0, "Hôpital (Q=4.0)": 4.0}
        Q = Q_map.get(usage, 2.5)
    with c3:
        if usage == "Personnalisé":
            Q = st.number_input("Q personnalisé (kN/m²)",
                                value=2.5, step=0.5, format="%.1f")
        else:
            st.metric("Q exploitation", f"{Q} kN/m²")

    equiv_moment = st.checkbox(
        "Option 'Équivalence en moment' (G_add = 2R/L) — "
        "charge ponctuelle au milieu de la poutre",
        value=False)

    st.divider()

    # ── Calcul ────────────────────────────────────────────────────────────────
    if st.button("🔢 Calculer les charges", type="primary"):

        # ── Calculs géométriques ─────────────────────────────────────────────
        # Volée
        e_moy = e_paillasse / cos_alpha + h_marche / 2
        G_volee  = e_moy * mat_rho + G_rev
        G_palier_dep = e_pal_dep * mat_rho + G_rev
        G_palier_int = e_pal_int * mat_rho + G_rev if e_pal_int > 0 else 0
        G_palier_arr = e_pal_arr * mat_rho + G_rev

        # ELU
        qu_volee  = 1.35 * G_volee  + 1.5 * Q
        qu_pal_dep = 1.35 * G_palier_dep + 1.5 * Q
        qu_pal_int = 1.35 * G_palier_int + 1.5 * Q if G_palier_int > 0 else 0
        qu_pal_arr = 1.35 * G_palier_arr + 1.5 * Q

        # Charges totales
        Q_v1  = qu_volee  * long_v1 * larg_v1
        Q_v2  = qu_volee  * long_v2 * larg_v2 if long_v2 > 0 else 0
        Q_pd  = qu_pal_dep * prof_pal_dep * larg_pal
        Q_pi  = qu_pal_int * prof_pal_int * larg_pal if prof_pal_int > 0 else 0
        Q_pa  = qu_pal_arr * prof_pal_arr * larg_pal

        # Réactions (50% par appui)
        R_v1_bas  = Q_v1 / 2   # volée 1 → appui bas
        R_v1_haut = Q_v1 / 2   # volée 1 → appui haut
        R_v2_bas  = Q_v2 / 2 if Q_v2 > 0 else 0
        R_v2_haut = Q_v2 / 2 if Q_v2 > 0 else 0

        # Réactions totales par poutre palière
        if "en U" in type_esc:
            R_depart       = R_v1_bas + Q_pd / 2
            R_intermediaire = R_v1_haut + R_v2_bas + Q_pi
            R_arrivee      = R_v2_haut + Q_pa / 2
        elif "quart" in type_esc.lower():
            R_depart  = R_v1_bas + Q_pd / 2
            R_arrivee = R_v1_haut + Q_pa / 2
            R_intermediaire = 0
        else:
            R_depart  = R_v1_bas + Q_pd / 2
            R_arrivee = R_v1_haut + Q_pa / 2
            R_intermediaire = 0

        facteur = 2.0 if equiv_moment else 1.0

        # ── Affichage détail ─────────────────────────────────────────────────
        st.markdown("### 📊 Résultats détaillés")

        with st.expander("Détail des calculs géométriques", expanded=True):
            st.markdown(f"""
| Paramètre | Formule | Résultat |
|---|---|---|
| Angle α | arctan({h_marche}/{giron}) | **{alpha_deg:.1f}°** |
| cos(α) | | **{cos_alpha:.4f}** |
| e_moy | {e_paillasse}/cos({alpha_deg:.1f}°) + {h_marche}/2 | **{e_moy:.3f} m** |
| G_volée | {e_moy:.3f}×25 + {G_rev} | **{G_volee:.2f} kN/m²** |
| G_palier départ | {e_pal_dep}×25 + {G_rev} | **{G_palier_dep:.2f} kN/m²** |
{f"| G_palier intermédiaire | {e_pal_int}×25 + {G_rev} | **{G_palier_int:.2f} kN/m²** |" if e_pal_int > 0 else ""}
| G_palier arrivée | {e_pal_arr}×25 + {G_rev} | **{G_palier_arr:.2f} kN/m²** |
| qu_volée | 1.35×{G_volee:.2f} + 1.5×{Q} | **{qu_volee:.2f} kN/m²** |
""")

        with st.expander("Charges totales et réactions", expanded=True):
            lignes = f"""
| Zone | Surface (m²) | qu (kN/m²) | Charge totale (kN) |
|---|---|---|---|
| Volée 1 | {long_v1}×{larg_v1}={long_v1*larg_v1:.2f} | {qu_volee:.2f} | **{Q_v1:.1f}** |
"""
            if long_v2 > 0:
                lignes += f"| Volée 2 | {long_v2}×{larg_v2}={long_v2*larg_v2:.2f} | {qu_volee:.2f} | **{Q_v2:.1f}** |\n"
            lignes += f"| Palier départ | {prof_pal_dep}×{larg_pal}={prof_pal_dep*larg_pal:.2f} | {qu_pal_dep:.2f} | **{Q_pd:.1f}** |\n"
            if Q_pi > 0:
                lignes += f"| Palier intermédiaire | {prof_pal_int}×{larg_pal}={prof_pal_int*larg_pal:.2f} | {qu_pal_int:.2f} | **{Q_pi:.1f}** |\n"
            lignes += f"| Palier arrivée | {prof_pal_arr}×{larg_pal}={prof_pal_arr*larg_pal:.2f} | {qu_pal_arr:.2f} | **{Q_pa:.1f}** |\n"
            st.markdown(lignes)

        # ── Réactions par poutre ─────────────────────────────────────────────
        st.markdown("### 🎯 Réactions à appliquer sur les poutres palières")

        poutres_data = []
        if "en U" in type_esc:
            poutres_data = [
                ("Palier départ (bas)",        R_depart,       "poutre_dep"),
                ("Palier intermédiaire",        R_intermediaire,"poutre_int"),
                ("Palier arrivée (haut)",       R_arrivee,      "poutre_arr"),
            ]
        else:
            poutres_data = [
                ("Palier bas",   R_depart,  "poutre_dep"),
                ("Palier haut",  R_arrivee, "poutre_arr"),
            ]

        # Liste des poutres du projet
        poutres_projet = []
        if projet and projet.barres:
            poutres_projet = [b for b in projet.barres
                              if b.type_elem == "poutre"]

        st.markdown("#### Sélectionner les poutres et calculer G_add")

        gadd_results = []
        for label, R, key in poutres_data:
            if R <= 0:
                continue
            st.markdown(f"**{label} — Réaction totale R = {R:.1f} kN**")
            c1, c2, c3 = st.columns([2,1,2])
            with c1:
                if poutres_projet:
                    opts = {f"{b.nom} (L={b.longueur:.2f}m)": b
                            for b in poutres_projet}
                    sel = st.selectbox(f"Poutre palière",
                                       list(opts.keys()), key=f"sel_{key}")
                    b_sel = opts[sel]
                    L_p = b_sel.longueur
                    nom_p = b_sel.nom
                    bid_p = b_sel.id
                else:
                    L_p = st.number_input(f"Portée poutre (m)",
                                          value=3.50, step=0.05,
                                          format="%.2f", key=f"L_{key}")
                    nom_p = label; bid_p = None
            with c2:
                G_add_calc = facteur * R / L_p
                st.metric("G_add (kN/m)", f"{G_add_calc:.2f}")
            with c3:
                st.markdown(f"""
```
R = {R:.1f} kN
L = {L_p:.2f} m
G_add = {facteur}×{R:.1f}/{L_p:.2f}
      = {G_add_calc:.2f} kN/m
```""")
            gadd_results.append({
                'label': label, 'R': R, 'L': L_p,
                'G_add': G_add_calc, 'nom': nom_p, 'bid': bid_p
            })

        # ── Injection sur les poutres ─────────────────────────────────────────
        if gadd_results and projet and projet.barres:
            st.divider()
            st.markdown("### ✅ Appliquer les charges sur les poutres")
            st.info("Les G_add seront ajoutés aux valeurs existantes "
                    "des poutres sélectionnées (en mémoire).")

            if st.button("🚀 Injecter les G_add sur les poutres", type="primary"):
                modif = []
                for r in gadd_results:
                    if r['bid'] is None:
                        continue
                    b = next((b for b in projet.barres
                              if b.id == r['bid']), None)
                    if b:
                        b.G_add += r['G_add']
                        modif.append(
                            f"✓ **{b.nom}** : G_add = "
                            f"{b.G_add - r['G_add']:.2f} + "
                            f"{r['G_add']:.2f} = **{b.G_add:.2f} kN/m**")

                if modif:
                    st.success("Charges injectées avec succès !")
                    for m in modif:
                        st.markdown(m)
                    st.warning("⚠ Relancez le calcul pour prendre en "
                               "compte les nouvelles charges.")

        # ── Récapitulatif à copier ────────────────────────────────────────────
        st.divider()
        st.markdown("### 📋 Récapitulatif")
        recap = "| Poutre palière | R (kN) | Portée (m) | G_add à ajouter (kN/m) |\n"
        recap += "|---|---|---|---|\n"
        for r in gadd_results:
            recap += (f"| {r['nom']} | {r['R']:.1f} | "
                      f"{r['L']:.2f} | **{r['G_add']:.2f}** |\n")
        st.markdown(recap)

        note = ("*Note : G_add = R/L (charge répartie équivalente)*"
                if not equiv_moment
                else "*Note : G_add = 2R/L (équivalence en moment — "
                     "charge ponctuelle au milieu)*")
        st.caption(note)

        # Hauteur totale
        nb_total = nb_m_v1 + (nb_m_v2 if long_v2 > 0 else 0)
        h_total = nb_total * h_marche
        st.info(f"ℹ️ Hauteur totale de l'escalier : "
                f"{nb_total} marches × {h_marche}m = **{h_total:.2f}m**")
