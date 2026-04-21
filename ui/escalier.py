"""
ui/escalier.py  — v3.10
Calculateur de charges d'escalier avec gestion de plusieurs escaliers.
Injection directe sur les poutres palières via st.session_state.
"""
import streamlit as st
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

RHO_BA = 25.0   # kN/m³ béton armé


# ── Calcul des charges ────────────────────────────────────────────────────────
def _calcul_escalier(esc):
    """Calcule G_volée, G_palier et les réactions à partir des données d'un escalier."""
    h = esc['h_marche']; g = esc['giron']
    e_p = esc['e_paillasse']; G_rev = esc['G_rev']; Q = esc['Q']

    alpha  = math.atan(h / g) if g > 0 else 0
    cos_a  = math.cos(alpha)
    e_moy  = e_p / cos_a + h / 2
    G_volee   = e_moy * RHO_BA + G_rev
    G_pal_dep = esc['e_pal_dep'] * RHO_BA + G_rev
    G_pal_int = esc['e_pal_int'] * RHO_BA + G_rev if esc.get('e_pal_int',0)>0 else 0
    G_pal_arr = esc['e_pal_arr'] * RHO_BA + G_rev

    qu_v   = 1.35 * G_volee   + 1.5 * Q
    qu_pd  = 1.35 * G_pal_dep + 1.5 * Q
    qu_pi  = 1.35 * G_pal_int + 1.5 * Q if G_pal_int > 0 else 0
    qu_pa  = 1.35 * G_pal_arr + 1.5 * Q

    larg = esc['larg_volee']
    nb1  = esc['nb_marches_v1']; nb2 = esc.get('nb_marches_v2', nb1)
    L1   = nb1 * g;              L2  = nb2 * g

    # Paliers
    pf_dep = esc.get('prof_pal_dep', larg)
    pf_int = esc.get('prof_pal_int', larg)
    pf_arr = esc.get('prof_pal_arr', larg)

    Q_v1 = qu_v * L1 * larg
    Q_v2 = qu_v * L2 * larg if esc['type'] in ("en_U",) else 0
    Q_pd = qu_pd * pf_dep * larg
    Q_pi = qu_pi * pf_int * larg if pf_int > 0 and esc['type']=="en_U" else 0
    Q_pa = qu_pa * pf_arr * larg

    # Réactions
    R_v1b = Q_v1 / 2; R_v1h = Q_v1 / 2
    R_v2b = Q_v2 / 2; R_v2h = Q_v2 / 2

    facteur = 2.0 if esc.get('equiv_moment') else 1.0

    if esc['type'] == "en_U":
        reactions = {
            'depart':        R_v1b + Q_pd/2,
            'intermediaire': R_v1h + R_v2b + Q_pi,
            'arrivee':       R_v2h + Q_pa/2,
        }
    elif esc['type'] == "quart_tournant":
        reactions = {
            'depart':  R_v1b + Q_pd/2,
            'arrivee': R_v1h + Q_pa/2,
        }
    else:  # volee_droite
        reactions = {
            'depart':  R_v1b + Q_pd/2,
            'arrivee': R_v1h + Q_pa/2,
        }

    return {
        'alpha_deg': math.degrees(alpha),
        'cos_alpha': cos_a,
        'e_moy': e_moy,
        'G_volee': G_volee, 'G_pal_dep': G_pal_dep,
        'G_pal_int': G_pal_int, 'G_pal_arr': G_pal_arr,
        'qu_volee': qu_v,
        'L1': L1, 'L2': L2,
        'Q_v1': Q_v1, 'Q_v2': Q_v2,
        'Q_pd': Q_pd, 'Q_pi': Q_pi, 'Q_pa': Q_pa,
        'reactions': reactions,
        'facteur': facteur,
    }


def _gadd_par_poutre(reactions, poutres_sel, facteur, projet):
    """Calcule G_add pour chaque poutre palière sélectionnée."""
    result = {}
    for role, bid in poutres_sel.items():
        if bid is None or bid <= 0: continue
        R = reactions.get(role, 0)
        if R <= 0: continue
        b = next((b for b in projet.barres if b.id == bid), None)
        if not b: continue
        L = b.longueur if b.longueur > 0 else 1.0
        result[bid] = round(facteur * R / L, 3)
    return result


# ── Formulaire d'un escalier ──────────────────────────────────────────────────
def _formulaire_escalier(projet, esc_init=None, key_prefix="new"):
    """Formulaire de saisie pour un escalier. Retourne le dict ou None si annulé."""
    is_edit = esc_init is not None
    esc = esc_init.copy() if is_edit else {}

    # Nom
    nom = st.text_input("Nom de l'escalier",
                        value=esc.get('nom', f"Escalier {key_prefix}"),
                        key=f"{key_prefix}_nom")

    # Type
    types = {
        "Escalier en U (2 volées + palier intermédiaire)": "en_U",
        "Escalier quart tournant (1 volée + palier à 90°)":  "quart_tournant",
        "Volée droite simple":                               "volee_droite",
    }
    type_label = {v:k for k,v in types.items()}.get(
        esc.get('type','en_U'),
        "Escalier en U (2 volées + palier intermédiaire)")
    type_sel = st.radio("Type d'escalier", list(types.keys()),
                        index=list(types.keys()).index(type_label),
                        key=f"{key_prefix}_type")
    type_esc = types[type_sel]

    st.markdown("**Géométrie des marches**")
    c1, c2, c3 = st.columns(3)
    with c1:
        h_m = st.number_input("Hauteur de marche h (m)",
                              value=esc.get('h_marche',0.17),
                              step=0.01, format="%.2f",
                              key=f"{key_prefix}_h")
    with c2:
        gir = st.number_input("Giron g — largeur de marche (m)",
                              value=esc.get('giron',0.28),
                              step=0.01, format="%.2f",
                              key=f"{key_prefix}_g")
    with c3:
        e_p = st.number_input("Épaisseur paillasse — dalle support (m)",
                              value=esc.get('e_paillasse',0.15),
                              step=0.01, format="%.2f",
                              key=f"{key_prefix}_ep")

    # Vérification Blondel
    blondel = 2*h_m + gir
    ok_b = 0.60 <= blondel <= 0.65
    st.caption(f"Règle de Blondel (2h+g) = {blondel:.3f}m "
               f"{'✓ OK' if ok_b else '⚠ hors norme [0.60–0.65m]'}")

    st.markdown("**Volée — portion inclinée**")
    c1, c2 = st.columns(2)
    with c1:
        larg = st.number_input("Largeur de la volée (m)",
                               value=esc.get('larg_volee',1.20),
                               step=0.05, format="%.2f",
                               key=f"{key_prefix}_larg")
        nb1  = st.number_input("Nb marches volée 1",
                               value=esc.get('nb_marches_v1',9),
                               min_value=1, step=1,
                               key=f"{key_prefix}_nb1")
        L1   = nb1 * gir
        st.caption(f"Longueur horizontale volée 1 = {nb1}×{gir:.2f} = **{L1:.2f}m**")
    with c2:
        if type_esc == "en_U":
            volee2_id = st.checkbox("Volée 2 identique à Volée 1",
                                    value=esc.get('volee2_identique', True),
                                    key=f"{key_prefix}_v2id")
            if volee2_id:
                nb2 = nb1
                st.caption(f"Volée 2 = {nb2} marches = {nb2*gir:.2f}m ✓")
            else:
                nb2 = st.number_input("Nb marches volée 2",
                                      value=esc.get('nb_marches_v2', nb1),
                                      min_value=1, step=1,
                                      key=f"{key_prefix}_nb2")
                L2 = nb2 * gir
                st.caption(f"Longueur horizontale volée 2 = {nb2}×{gir:.2f} = **{L2:.2f}m**")
        else:
            nb2 = nb1; volee2_id = True

    # Paliers
    st.markdown("**Paliers**")
    if type_esc == "en_U":
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            st.caption("Palier départ (bas)")
            e_pd = st.number_input("Épaisseur (m)", value=esc.get('e_pal_dep',0.15),
                                   step=0.01, format="%.2f", key=f"{key_prefix}_epd")
            pf_pd= st.number_input("Profondeur (m)", value=esc.get('prof_pal_dep',larg),
                                   step=0.05, format="%.2f", key=f"{key_prefix}_ppd")
        with cp2:
            st.caption("Palier intermédiaire")
            e_pi = st.number_input("Épaisseur (m)", value=esc.get('e_pal_int',0.15),
                                   step=0.01, format="%.2f", key=f"{key_prefix}_epi")
            pf_pi= st.number_input("Profondeur (m)", value=esc.get('prof_pal_int',larg),
                                   step=0.05, format="%.2f", key=f"{key_prefix}_ppi")
        with cp3:
            st.caption("Palier arrivée (haut)")
            e_pa = st.number_input("Épaisseur (m)", value=esc.get('e_pal_arr',0.15),
                                   step=0.01, format="%.2f", key=f"{key_prefix}_epa")
            pf_pa= st.number_input("Profondeur (m)", value=esc.get('prof_pal_arr',larg),
                                   step=0.05, format="%.2f", key=f"{key_prefix}_ppa")
    else:
        cp1, cp2 = st.columns(2)
        with cp1:
            st.caption("Palier bas")
            e_pd  = st.number_input("Épaisseur (m)", value=esc.get('e_pal_dep',0.15),
                                    step=0.01, format="%.2f", key=f"{key_prefix}_epd2")
            pf_pd = st.number_input("Profondeur (m)", value=esc.get('prof_pal_dep',larg),
                                    step=0.05, format="%.2f", key=f"{key_prefix}_ppd2")
        with cp2:
            st.caption("Palier haut")
            e_pa  = st.number_input("Épaisseur (m)", value=esc.get('e_pal_arr',0.15),
                                    step=0.01, format="%.2f", key=f"{key_prefix}_epa2")
            pf_pa = st.number_input("Profondeur (m)", value=esc.get('prof_pal_arr',larg),
                                    step=0.05, format="%.2f", key=f"{key_prefix}_ppa2")
        e_pi = 0; pf_pi = 0

    # Charges
    st.markdown("**Charges**")
    c1, c2, c3 = st.columns(3)
    with c1:
        G_rev = st.number_input("Revêtement G_rev (kN/m²)",
                                value=esc.get('G_rev',1.50),
                                step=0.10, format="%.2f",
                                key=f"{key_prefix}_Grev")
    with c2:
        usage_map = {"Habitation":2.5,"Bureaux":2.5,
                     "ERP/École":4.0,"Hôpital":4.0,"Personnalisé":0}
        usage_def = next((k for k,v in usage_map.items()
                         if v == esc.get('Q',2.5)), "Habitation")
        usage = st.selectbox("Usage", list(usage_map.keys()),
                             index=list(usage_map.keys()).index(usage_def),
                             key=f"{key_prefix}_usage")
        Q = usage_map[usage] if usage != "Personnalisé" else \
            st.number_input("Q (kN/m²)", value=2.5, step=0.5,
                            key=f"{key_prefix}_Qcust")
        if usage != "Personnalisé":
            st.caption(f"Q = {Q} kN/m²")
    with c3:
        equiv_m = st.checkbox("Équivalence en moment (G_add=2R/L)",
                              value=esc.get('equiv_moment',False),
                              key=f"{key_prefix}_eqm")

    # Sélection des poutres palières
    st.markdown("**Sélection des poutres palières**")

    # Filtre par niveau
    niveaux_dispo = sorted(set(b.niveau for b in projet.barres
                               if b.type_elem == "poutre"))
    niv_labels = ["Tous"] + [f"Niveau {n}" for n in niveaux_dispo]
    niv_sel = st.selectbox("Filtrer par niveau",
                           niv_labels, key=f"{key_prefix}_niv")
    niv_filtre = None if niv_sel == "Tous" else int(niv_sel.split()[-1])

    poutres_filtrées = [b for b in projet.barres
                        if b.type_elem == "poutre"
                        and (niv_filtre is None or b.niveau == niv_filtre)]
    opts = {f"{b.nom} — Niv.{b.niveau} L={b.longueur:.2f}m": b.id
            for b in poutres_filtrées}
    opts_list = ["— Aucune —"] + list(opts.keys())

    poutres_sel = esc.get('poutres_sel', {})
    roles = (["depart","intermediaire","arrivee"]
             if type_esc == "en_U"
             else ["depart","arrivee"])
    labels_role = {
        "depart":        "Poutre palière départ (bas)",
        "intermediaire": "Poutre palière intermédiaire",
        "arrivee":       "Poutre palière arrivée (haut)",
    }

    new_poutres_sel = {}
    for role in roles:
        bid_cur = poutres_sel.get(role)
        cur_label = next((l for l,v in opts.items() if v==bid_cur), "— Aucune —")
        idx = opts_list.index(cur_label) if cur_label in opts_list else 0
        sel = st.selectbox(labels_role[role], opts_list,
                           index=idx, key=f"{key_prefix}_{role}")
        new_poutres_sel[role] = opts.get(sel)

    # Assembler le dict escalier
    new_esc = {
        'nom': nom, 'type': type_esc,
        'h_marche': h_m, 'giron': gir, 'e_paillasse': e_p,
        'larg_volee': larg,
        'nb_marches_v1': nb1, 'nb_marches_v2': nb2,
        'volee2_identique': volee2_id if type_esc=="en_U" else True,
        'e_pal_dep': e_pd, 'prof_pal_dep': pf_pd,
        'e_pal_int': e_pi, 'prof_pal_int': pf_pi,
        'e_pal_arr': e_pa, 'prof_pal_arr': pf_pa,
        'G_rev': G_rev, 'Q': Q, 'equiv_moment': equiv_m,
        'poutres_sel': new_poutres_sel,
    }
    return new_esc


# ── Page principale ───────────────────────────────────────────────────────────
def page_escalier(projet=None):
    st.markdown("## 🪜 Escaliers — Charges et injection sur poutres")

    # Initialiser session state
    if "escaliers" not in st.session_state:
        st.session_state.escaliers = []
    if "esc_mode" not in st.session_state:
        st.session_state.esc_mode = "liste"   # liste | new | edit
    if "esc_edit_idx" not in st.session_state:
        st.session_state.esc_edit_idx = None

    if projet is None or not projet.barres:
        st.warning("Importez d'abord un projet depuis **📂 Import**.")
        st.info("Le calculateur d'escalier nécessite un projet chargé "
                "pour sélectionner les poutres palières.")
        return

    escaliers = st.session_state.escaliers

    # ══════════════════════════════════════════════════════════════════════════
    # MODE LISTE
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.esc_mode == "liste":

        if not escaliers:
            st.info("Aucun escalier configuré. Cliquez sur "
                    "**+ Ajouter un escalier** pour commencer.")
        else:
            st.markdown(f"### {len(escaliers)} escalier(s) configuré(s)")
            for i, esc in enumerate(escaliers):
                # Calculer les résultats
                calc = _calcul_escalier(esc)
                gadd = _gadd_par_poutre(
                    calc['reactions'], esc.get('poutres_sel',{}),
                    calc['facteur'], projet)
                # Mettre à jour gadd dans l'escalier
                st.session_state.escaliers[i]['gadd'] = gadd

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3,2,1,1])
                    with c1:
                        type_label = {
                            "en_U":"Escalier en U",
                            "quart_tournant":"Quart tournant",
                            "volee_droite":"Volée droite"
                        }.get(esc['type'], esc['type'])
                        nb_tot = esc['nb_marches_v1'] + \
                                 (esc.get('nb_marches_v2',0)
                                  if esc['type']=="en_U" else 0)
                        h_tot  = nb_tot * esc['h_marche']
                        st.markdown(
                            f"**{esc['nom']}**  \n"
                            f"{type_label} · {esc['larg_volee']}m larg. · "
                            f"{nb_tot} marches · H={h_tot:.2f}m")
                    with c2:
                        st.caption(
                            f"G_volée={calc['G_volee']:.2f} kN/m²  "
                            f"Q={esc['Q']} kN/m²")
                        if gadd:
                            for bid, g in gadd.items():
                                b = next((b for b in projet.barres
                                         if b.id==bid), None)
                                if b:
                                    st.caption(f"→ {b.nom} +{g:.2f}kN/m")
                        else:
                            st.caption("⚠ Aucune poutre sélectionnée")
                    with c3:
                        if st.button("✏️ Éditer", key=f"edit_{i}",
                                     use_container_width=True):
                            st.session_state.esc_mode = "edit"
                            st.session_state.esc_edit_idx = i
                            st.rerun()
                        if st.button("📋 Dupliquer", key=f"dup_{i}",
                                     use_container_width=True):
                            dup = esc.copy()
                            dup['nom'] = esc['nom'] + " (copie)"
                            dup['poutres_sel'] = {}  # Option B
                            dup['gadd'] = {}
                            st.session_state.escaliers.append(dup)
                            st.rerun()
                    with c4:
                        if st.button("🗑️ Supprimer", key=f"del_{i}",
                                     use_container_width=True,
                                     type="secondary"):
                            st.session_state.escaliers.pop(i)
                            st.rerun()

        st.divider()
        if st.button("➕ Ajouter un escalier",
                     type="primary", use_container_width=True):
            st.session_state.esc_mode = "new"
            st.rerun()

        # Récapitulatif global
        if escaliers:
            st.divider()
            st.markdown("### 📋 Récapitulatif des G_add à injecter")
            # Agréger par poutre
            total_gadd = {}
            for esc in escaliers:
                for bid, g in esc.get('gadd',{}).items():
                    total_gadd[bid] = total_gadd.get(bid,0) + g

            if total_gadd:
                rows = []
                for bid, g in total_gadd.items():
                    b = next((b for b in projet.barres if b.id==bid), None)
                    if b:
                        rows.append({
                            "Poutre": b.nom,
                            "Niveau": b.niveau,
                            "G_add escalier (kN/m)": f"{g:.2f}",
                            "G_add existant (kN/m)": f"{b.G_add:.2f}",
                            "Total G_add (kN/m)": f"{b.G_add + g:.2f}",
                        })
                import pandas as pd
                st.dataframe(pd.DataFrame(rows),
                             hide_index=True, use_container_width=True)
                st.info("Ces G_add seront automatiquement appliqués "
                        "lors du calcul depuis **🔷 Visualisation & Calcul**.")
            else:
                st.warning("Aucune poutre sélectionnée dans les escaliers configurés.")

    # ══════════════════════════════════════════════════════════════════════════
    # MODE AJOUT / ÉDITION
    # ══════════════════════════════════════════════════════════════════════════
    else:
        is_edit = st.session_state.esc_mode == "edit"
        idx     = st.session_state.esc_edit_idx
        titre   = "✏️ Modifier l'escalier" if is_edit else "➕ Nouvel escalier"
        st.markdown(f"### {titre}")

        esc_init = escaliers[idx] if is_edit and idx is not None else None
        # Utiliser un compteur unique pour éviter les conflits de clés Streamlit
    if "esc_counter" not in st.session_state:
        st.session_state.esc_counter = 0
    if not is_edit:
        st.session_state.esc_counter += 1
    key_pfx = f"edit_{idx}" if is_edit else f"new_{st.session_state.esc_counter}"

        new_esc = _formulaire_escalier(projet, esc_init, key_pfx)

        # Aperçu des résultats
        if new_esc:
            calc = _calcul_escalier(new_esc)
            gadd = _gadd_par_poutre(
                calc['reactions'], new_esc.get('poutres_sel',{}),
                calc['facteur'], projet)

            with st.expander("📊 Aperçu des charges calculées", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("G volée", f"{calc['G_volee']:.2f} kN/m²")
                c2.metric("α inclinaison", f"{calc['alpha_deg']:.1f}°")
                c3.metric("e_moy", f"{calc['e_moy']*100:.1f} cm")

                st.markdown("**Réactions d'appui ELU :**")
                for role, R in calc['reactions'].items():
                    bid = new_esc.get('poutres_sel',{}).get(role)
                    b   = next((b for b in projet.barres if b.id==bid), None)
                    nom_p = b.nom if b else "— aucune poutre —"
                    gadd_val = gadd.get(bid, 0) if bid else 0
                    L_p = b.longueur if b else 0
                    label = {"depart":"Départ","intermediaire":"Intermédiaire",
                             "arrivee":"Arrivée"}.get(role, role)
                    st.markdown(
                        f"- **{label}** : R={R:.1f}kN → {nom_p} "
                        + (f"G_add={gadd_val:.2f}kN/m (L={L_p:.2f}m)"
                           if gadd_val > 0 else "⚠ poutre non sélectionnée"))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            label_save = "💾 Enregistrer les modifications" if is_edit \
                         else "✅ Valider et ajouter"
            if st.button(label_save, type="primary", use_container_width=True):
                new_esc['gadd'] = gadd
                if is_edit and idx is not None:
                    st.session_state.escaliers[idx] = new_esc
                else:
                    st.session_state.escaliers.append(new_esc)
                st.session_state.esc_mode = "liste"
                st.session_state.esc_edit_idx = None
                st.rerun()
        with c2:
            if st.button("✖ Annuler", use_container_width=True):
                st.session_state.esc_mode = "liste"
                st.session_state.esc_edit_idx = None
                st.rerun()
