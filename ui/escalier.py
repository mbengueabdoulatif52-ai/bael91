"""
ui/escalier.py  — v3.10e
Calculateur de charges d'escalier.
Gestion d'état Streamlit correcte :
- key_prefix stable pendant toute la session d'édition/création
- Valeurs des widgets lues depuis session_state via leur key
- Pas d'incrément de compteur à chaque rerun
"""
import streamlit as st
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

RHO_BA = 25.0   # kN/m³ béton armé


# ── Calcul des charges ────────────────────────────────────────────────────────
def _calcul_escalier(esc):
    h = esc['h_marche']; g = esc['giron']
    e_p = esc['e_paillasse']; G_rev = esc['G_rev']; Q = esc['Q']

    alpha  = math.atan(h / g) if g > 0 else 0
    cos_a  = math.cos(alpha)
    e_moy  = e_p / cos_a + h / 2
    G_volee   = e_moy * RHO_BA + G_rev
    G_pal_dep = esc['e_pal_dep'] * RHO_BA + G_rev
    G_pal_int = esc['e_pal_int'] * RHO_BA + G_rev if esc.get('e_pal_int',0)>0 else 0
    G_pal_arr = esc['e_pal_arr'] * RHO_BA + G_rev

    qu_v  = 1.35 * G_volee   + 1.5 * Q
    qu_pd = 1.35 * G_pal_dep + 1.5 * Q
    qu_pi = 1.35 * G_pal_int + 1.5 * Q if G_pal_int > 0 else 0
    qu_pa = 1.35 * G_pal_arr + 1.5 * Q

    larg = esc['larg_volee']
    nb1  = esc['nb_marches_v1']
    nb2  = esc.get('nb_marches_v2', nb1)
    L1   = nb1 * g
    L2   = nb2 * g

    pf_dep = esc.get('prof_pal_dep', larg)
    pf_int = esc.get('prof_pal_int', larg)
    pf_arr = esc.get('prof_pal_arr', larg)

    Q_v1 = qu_v  * L1 * larg
    Q_v2 = qu_v  * L2 * larg if esc['type'] == "en_U" else 0
    Q_pd = qu_pd * pf_dep * larg
    Q_pi = qu_pi * pf_int * larg if pf_int > 0 and esc['type']=="en_U" else 0
    Q_pa = qu_pa * pf_arr * larg

    facteur = 2.0 if esc.get('equiv_moment') else 1.0

    if esc['type'] == "en_U":
        reactions = {
            'depart':        Q_v1/2 + Q_pd/2,
            'intermediaire': Q_v1/2 + Q_v2/2 + Q_pi,
            'arrivee':       Q_v2/2 + Q_pa/2,
        }
    else:
        reactions = {
            'depart':  Q_v1/2 + Q_pd/2,
            'arrivee': Q_v1/2 + Q_pa/2,
        }

    return {
        'alpha_deg': math.degrees(alpha),
        'cos_alpha': cos_a,
        'e_moy':     e_moy,
        'G_volee':   G_volee,
        'qu_volee':  qu_v,
        'L1': L1, 'L2': L2,
        'reactions': reactions,
        'facteur':   facteur,
    }


def _gadd_par_poutre(reactions, poutres_sel, facteur, projet):
    result = {}
    for role, bid in poutres_sel.items():
        if not bid: continue
        R = reactions.get(role, 0)
        if R <= 0: continue
        b = next((b for b in projet.barres if b.id == bid), None)
        if not b: continue
        L = b.longueur if b.longueur > 0 else 1.0
        result[bid] = round(facteur * R / L, 3)
    return result


# ── Formulaire ────────────────────────────────────────────────────────────────
def _formulaire_escalier(projet, kp):
    """
    kp = key_prefix stable (ne change pas entre les reruns).
    Toutes les valeurs sont lues directement depuis st.session_state[key]
    grâce au mécanisme natif de Streamlit (chaque widget avec une key
    persist automatiquement sa valeur dans session_state).
    """
    # ── Nom ──────────────────────────────────────────────────────────────────
    st.text_input("Nom de l'escalier", key=f"{kp}_nom")
    nom = st.session_state.get(f"{kp}_nom", f"Escalier {kp}")

    # ── Type ─────────────────────────────────────────────────────────────────
    types_labels = [
        "Escalier en U (2 volées + palier intermédiaire)",
        "Escalier quart tournant (1 volée + palier à 90°)",
        "Volée droite simple",
    ]
    types_vals = ["en_U", "quart_tournant", "volee_droite"]
    st.radio("Type d'escalier", types_labels, key=f"{kp}_type")
    type_idx = types_labels.index(st.session_state.get(f"{kp}_type",
                                  types_labels[0]))
    type_esc = types_vals[type_idx]

    # ── Géométrie marches ─────────────────────────────────────────────────────
    st.markdown("**Géométrie des marches**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("Hauteur de marche h (m)",
                        min_value=0.10, max_value=0.25,
                        step=0.01, format="%.2f", key=f"{kp}_h")
    with c2:
        st.number_input("Giron g — largeur de marche (m)",
                        min_value=0.15, max_value=0.40,
                        step=0.01, format="%.2f", key=f"{kp}_g")
    with c3:
        st.number_input("Épaisseur paillasse — dalle support (m)",
                        min_value=0.08, max_value=0.30,
                        step=0.01, format="%.2f", key=f"{kp}_ep")

    h_m = st.session_state.get(f"{kp}_h", 0.17)
    gir = st.session_state.get(f"{kp}_g", 0.28)
    e_p = st.session_state.get(f"{kp}_ep", 0.15)

    blondel = 2*h_m + gir
    ok_b = 0.60 <= blondel <= 0.65
    st.caption(f"Règle de Blondel (2h+g) = {blondel:.3f}m "
               f"{'✓ OK' if ok_b else '⚠ hors norme [0.60–0.65m]'}")

    # ── Volée ─────────────────────────────────────────────────────────────────
    st.markdown("**Volée — portion inclinée**")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Largeur de la volée (m)",
                        min_value=0.80, max_value=3.00,
                        step=0.05, format="%.2f", key=f"{kp}_larg")
        st.number_input("Nb marches volée 1",
                        min_value=1, max_value=30,
                        step=1, key=f"{kp}_nb1")
    larg = st.session_state.get(f"{kp}_larg", 1.20)
    nb1  = st.session_state.get(f"{kp}_nb1", 9)
    st.caption(f"Longueur horizontale volée 1 = {nb1}×{gir:.2f} = **{nb1*gir:.2f}m**")

    with c2:
        if type_esc == "en_U":
            st.checkbox("Volée 2 identique à Volée 1",
                        key=f"{kp}_v2id")
            volee2_id = st.session_state.get(f"{kp}_v2id", True)
            if not volee2_id:
                st.number_input("Nb marches volée 2",
                                min_value=1, max_value=30,
                                step=1, key=f"{kp}_nb2")
                nb2 = st.session_state.get(f"{kp}_nb2", nb1)
                st.caption(f"Longueur horizontale volée 2 = "
                           f"{nb2}×{gir:.2f} = **{nb2*gir:.2f}m**")
            else:
                nb2 = nb1
                st.caption(f"Volée 2 = {nb2} marches = {nb2*gir:.2f}m ✓")
        else:
            nb2 = nb1; volee2_id = True

    # ── Paliers ───────────────────────────────────────────────────────────────
    st.markdown("**Paliers**")
    if type_esc == "en_U":
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            st.caption("Palier départ (bas)")
            st.number_input("Épaisseur (m)", min_value=0.10, max_value=0.30,
                            step=0.01, format="%.2f", key=f"{kp}_epd")
            st.number_input("Profondeur (m)", min_value=0.50, max_value=3.00,
                            step=0.05, format="%.2f", key=f"{kp}_ppd")
        with cp2:
            st.caption("Palier intermédiaire")
            st.number_input("Épaisseur (m)", min_value=0.10, max_value=0.30,
                            step=0.01, format="%.2f", key=f"{kp}_epi")
            st.number_input("Profondeur (m)", min_value=0.50, max_value=3.00,
                            step=0.05, format="%.2f", key=f"{kp}_ppi")
        with cp3:
            st.caption("Palier arrivée (haut)")
            st.number_input("Épaisseur (m)", min_value=0.10, max_value=0.30,
                            step=0.01, format="%.2f", key=f"{kp}_epa")
            st.number_input("Profondeur (m)", min_value=0.50, max_value=3.00,
                            step=0.05, format="%.2f", key=f"{kp}_ppa")
        e_pd  = st.session_state.get(f"{kp}_epd", 0.15)
        pf_pd = st.session_state.get(f"{kp}_ppd", larg)
        e_pi  = st.session_state.get(f"{kp}_epi", 0.15)
        pf_pi = st.session_state.get(f"{kp}_ppi", larg)
        e_pa  = st.session_state.get(f"{kp}_epa", 0.15)
        pf_pa = st.session_state.get(f"{kp}_ppa", larg)
    else:
        cp1, cp2 = st.columns(2)
        with cp1:
            st.caption("Palier bas")
            st.number_input("Épaisseur (m)", min_value=0.10, max_value=0.30,
                            step=0.01, format="%.2f", key=f"{kp}_epd_s")
            st.number_input("Profondeur (m)", min_value=0.50, max_value=3.00,
                            step=0.05, format="%.2f", key=f"{kp}_ppd_s")
        with cp2:
            st.caption("Palier haut")
            st.number_input("Épaisseur (m)", min_value=0.10, max_value=0.30,
                            step=0.01, format="%.2f", key=f"{kp}_epa_s")
            st.number_input("Profondeur (m)", min_value=0.50, max_value=3.00,
                            step=0.05, format="%.2f", key=f"{kp}_ppa_s")
        e_pd  = st.session_state.get(f"{kp}_epd_s", 0.15)
        pf_pd = st.session_state.get(f"{kp}_ppd_s", larg)
        e_pi  = 0; pf_pi = 0
        e_pa  = st.session_state.get(f"{kp}_epa_s", 0.15)
        pf_pa = st.session_state.get(f"{kp}_ppa_s", larg)

    # ── Charges ───────────────────────────────────────────────────────────────
    st.markdown("**Charges**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("Revêtement G_rev (kN/m²)",
                        min_value=0.0, max_value=5.0,
                        step=0.10, format="%.2f", key=f"{kp}_Grev")
    with c2:
        usage_opts = ["Habitation (2.5)", "Bureaux (2.5)",
                      "ERP/École (4.0)", "Hôpital (4.0)", "Autre"]
        st.selectbox("Usage", usage_opts, key=f"{kp}_usage")
    with c3:
        usage_val = st.session_state.get(f"{kp}_usage", "Habitation (2.5)")
        if "Autre" in usage_val:
            st.number_input("Q (kN/m²)", min_value=1.0, max_value=10.0,
                            step=0.5, format="%.1f", key=f"{kp}_Qcust")
            Q = st.session_state.get(f"{kp}_Qcust", 2.5)
        else:
            Q = 4.0 if "4.0" in usage_val else 2.5
            st.metric("Q exploitation", f"{Q} kN/m²")

    st.checkbox("Équivalence en moment (G_add = 2R/L)",
                key=f"{kp}_eqm")

    G_rev    = st.session_state.get(f"{kp}_Grev", 1.50)
    equiv_m  = st.session_state.get(f"{kp}_eqm", False)

    # ── Sélection poutres palières ────────────────────────────────────────────
    st.markdown("**Sélection des poutres palières**")

    # Filtre par niveau
    niveaux_dispo = sorted(set(b.niveau for b in projet.barres
                               if b.type_elem == "poutre"))
    niv_opts = ["Tous"] + [f"Niveau {n}" for n in niveaux_dispo]
    st.selectbox("Filtrer par niveau", niv_opts, key=f"{kp}_niv")
    niv_sel    = st.session_state.get(f"{kp}_niv", "Tous")
    niv_filtre = None if niv_sel == "Tous" else int(niv_sel.split()[-1])

    poutres_f = [b for b in projet.barres
                 if b.type_elem == "poutre"
                 and (niv_filtre is None or b.niveau == niv_filtre)]
    # opts : label → bid
    opts = {"— Aucune —": None}
    for b in poutres_f:
        opts[f"{b.nom} — Niv.{b.niveau} L={b.longueur:.2f}m"] = b.id

    roles = (["depart","intermediaire","arrivee"]
             if type_esc == "en_U" else ["depart","arrivee"])
    labels_role = {
        "depart":        "Poutre palière départ (bas)",
        "intermediaire": "Poutre palière intermédiaire",
        "arrivee":       "Poutre palière arrivée (haut)",
    }

    poutres_sel = {}
    for role in roles:
        # sel_key : clé du widget — gérée exclusivement par Streamlit
        # id_key  : clé séparée pour l'ID — modifiable librement
        sel_key = f"{kp}_sel_{role}"
        id_key  = f"{kp}_id_{role}"

        opts_list = list(opts.keys())

        # Retrouver l'index depuis l'ID stocké dans id_key (clé séparée)
        cur_bid   = st.session_state.get(id_key)
        cur_label = next((l for l,v in opts.items() if v==cur_bid),
                         "— Aucune —")
        cur_idx   = opts_list.index(cur_label) if cur_label in opts_list else 0

        # Widget selectbox — NE PAS écrire dans session_state[sel_key]
        # Streamlit le gère automatiquement
        st.selectbox(labels_role[role], opts_list,
                     index=cur_idx, key=sel_key)

        # Lire le label et stocker l'ID dans la clé séparée
        sel_label = st.session_state.get(sel_key, "— Aucune —")
        bid_sel   = opts.get(sel_label)
        st.session_state[id_key] = bid_sel  # écriture autorisée (clé séparée)
        poutres_sel[role] = bid_sel

    # ── Assembler le dict escalier ────────────────────────────────────────────
    return {
        'nom': nom, 'type': type_esc,
        'h_marche': h_m, 'giron': gir, 'e_paillasse': e_p,
        'larg_volee': larg,
        'nb_marches_v1': nb1, 'nb_marches_v2': nb2,
        'volee2_identique': volee2_id if type_esc=="en_U" else True,
        'e_pal_dep': e_pd, 'prof_pal_dep': pf_pd,
        'e_pal_int': e_pi, 'prof_pal_int': pf_pi,
        'e_pal_arr': e_pa, 'prof_pal_arr': pf_pa,
        'G_rev': G_rev, 'Q': Q, 'equiv_moment': equiv_m,
        'poutres_sel': poutres_sel,
    }


def _init_form_from_esc(kp, esc):
    """Pré-remplir les clés session_state depuis un escalier existant (édition)."""
    mapping = {
        f"{kp}_nom":   esc.get('nom', ''),
        f"{kp}_h":     esc.get('h_marche', 0.17),
        f"{kp}_g":     esc.get('giron', 0.28),
        f"{kp}_ep":    esc.get('e_paillasse', 0.15),
        f"{kp}_larg":  esc.get('larg_volee', 1.20),
        f"{kp}_nb1":   esc.get('nb_marches_v1', 9),
        f"{kp}_nb2":   esc.get('nb_marches_v2', 9),
        f"{kp}_v2id":  esc.get('volee2_identique', True),
        f"{kp}_epd":   esc.get('e_pal_dep', 0.15),
        f"{kp}_ppd":   esc.get('prof_pal_dep', 1.20),
        f"{kp}_epi":   esc.get('e_pal_int', 0.15),
        f"{kp}_ppi":   esc.get('prof_pal_int', 1.20),
        f"{kp}_epa":   esc.get('e_pal_arr', 0.15),
        f"{kp}_ppa":   esc.get('prof_pal_arr', 1.20),
        f"{kp}_Grev":  esc.get('G_rev', 1.50),
        f"{kp}_eqm":   esc.get('equiv_moment', False),
    }
    # Type
    types_labels = [
        "Escalier en U (2 volées + palier intermédiaire)",
        "Escalier quart tournant (1 volée + palier à 90°)",
        "Volée droite simple",
    ]
    types_vals = ["en_U", "quart_tournant", "volee_droite"]
    t_idx = types_vals.index(esc.get('type','en_U'))
    mapping[f"{kp}_type"] = types_labels[t_idx]
    # Usage
    Q = esc.get('Q', 2.5)
    mapping[f"{kp}_usage"] = "ERP/École (4.0)" if Q == 4.0 else "Habitation (2.5)"

    for k, v in mapping.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Page principale ───────────────────────────────────────────────────────────
def page_escalier(projet=None):
    st.markdown("## 🪜 Escaliers — Charges et injection sur poutres")

    # Initialiser session state
    for k, v in [("escaliers", []), ("esc_mode", "liste"),
                 ("esc_edit_idx", None), ("esc_form_kp", None)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if projet is None or not projet.barres:
        st.warning("Importez d'abord un projet depuis **📂 Import**.")
        return

    escaliers = st.session_state.escaliers
    mode      = st.session_state.esc_mode

    # ══════════════════════════════════════════════════════════════════════════
    # MODE LISTE
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "liste":

        if not escaliers:
            st.info("Aucun escalier configuré. "
                    "Cliquez sur **➕ Ajouter un escalier**.")
        else:
            st.markdown(f"### {len(escaliers)} escalier(s) configuré(s)")
            for i, esc in enumerate(escaliers):
                calc = _calcul_escalier(esc)
                gadd = _gadd_par_poutre(
                    calc['reactions'], esc.get('poutres_sel',{}),
                    calc['facteur'], projet)
                st.session_state.escaliers[i]['gadd'] = gadd

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3,2,1,1])
                    with c1:
                        tl = {"en_U":"Escalier en U",
                              "quart_tournant":"Quart tournant",
                              "volee_droite":"Volée droite"}.get(
                                  esc['type'], esc['type'])
                        nb_tot = esc['nb_marches_v1'] + (
                            esc.get('nb_marches_v2',0)
                            if esc['type']=="en_U" else 0)
                        h_tot = nb_tot * esc['h_marche']
                        st.markdown(
                            f"**{esc['nom']}**  \n"
                            f"{tl} · {esc['larg_volee']}m · "
                            f"{nb_tot} marches · H={h_tot:.2f}m")
                    with c2:
                        st.caption(f"G_volée={calc['G_volee']:.2f}kN/m²  "
                                   f"Q={esc['Q']}kN/m²")
                        if gadd:
                            for bid, g in gadd.items():
                                b = next((b for b in projet.barres
                                         if b.id==bid), None)
                                if b:
                                    st.caption(f"→ {b.nom} +{g:.2f}kN/m")
                        else:
                            st.caption("⚠ Aucune poutre sélectionnée")
                    with c3:
                        if st.button("✏️", key=f"btn_edit_{i}",
                                     help="Éditer",
                                     use_container_width=True):
                            st.session_state.esc_mode     = "edit"
                            st.session_state.esc_edit_idx = i
                            st.session_state.esc_form_kp  = f"edit_{i}"
                            _init_form_from_esc(f"edit_{i}",
                                                st.session_state.escaliers[i])
                            st.rerun()
                        if st.button("📋", key=f"btn_dup_{i}",
                                     help="Dupliquer",
                                     use_container_width=True):
                            dup = {k:v for k,v in esc.items()
                                   if k not in ('poutres_sel','gadd')}
                            dup['nom'] = esc['nom'] + " (copie)"
                            dup['poutres_sel'] = {}
                            dup['gadd'] = {}
                            st.session_state.escaliers.append(dup)
                            st.rerun()
                    with c4:
                        if st.button("🗑️", key=f"btn_del_{i}",
                                     help="Supprimer",
                                     use_container_width=True,
                                     type="secondary"):
                            st.session_state.escaliers.pop(i)
                            st.rerun()

        st.divider()
        if st.button("➕ Ajouter un escalier",
                     type="primary", use_container_width=True):
            # Générer un key_prefix unique et stable pour cette création
            import time
            kp = f"new_{int(time.time()*1000) % 100000}"
            st.session_state.esc_mode    = "new"
            st.session_state.esc_form_kp = kp
            st.rerun()

        # Récapitulatif global
        if escaliers:
            st.divider()
            st.markdown("### 📋 Récapitulatif des G_add")
            total = {}
            for esc in escaliers:
                for bid, g in esc.get('gadd',{}).items():
                    total[bid] = total.get(bid,0) + g
            if total:
                rows = []
                for bid, g in total.items():
                    b = next((b for b in projet.barres if b.id==bid), None)
                    if b:
                        rows.append({
                            "Poutre": b.nom, "Niveau": b.niveau,
                            "G_add escalier": f"{g:.2f} kN/m",
                            "G_add existant": f"{b.G_add:.2f} kN/m",
                            "Total": f"{b.G_add+g:.2f} kN/m",
                        })
                import pandas as pd
                st.dataframe(pd.DataFrame(rows),
                             hide_index=True, use_container_width=True)
                st.info("Ces charges seront injectées lors du calcul "
                        "depuis **🔷 Visualisation & Calcul**.")
            else:
                st.warning("Aucune poutre sélectionnée.")

    # ══════════════════════════════════════════════════════════════════════════
    # MODE NEW / EDIT
    # ══════════════════════════════════════════════════════════════════════════
    else:
        is_edit = (mode == "edit")
        idx     = st.session_state.esc_edit_idx
        kp      = st.session_state.esc_form_kp

        titre = "✏️ Modifier l'escalier" if is_edit else "➕ Nouvel escalier"
        st.markdown(f"### {titre}")

        if kp is None:
            st.error("Erreur de navigation. Retour à la liste.")
            st.session_state.esc_mode = "liste"
            st.rerun()
            return

        # Afficher le formulaire — le kp est stable pendant toute la session
        new_esc = _formulaire_escalier(projet, kp)

        # Aperçu des charges
        calc = _calcul_escalier(new_esc)
        gadd = _gadd_par_poutre(
            calc['reactions'], new_esc.get('poutres_sel',{}),
            calc['facteur'], projet)

        with st.expander("📊 Aperçu des charges calculées", expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("G volée",       f"{calc['G_volee']:.2f} kN/m²")
            c2.metric("α inclinaison", f"{calc['alpha_deg']:.1f}°")
            c3.metric("e_moy",         f"{calc['e_moy']*100:.1f} cm")
            st.markdown("**Réactions d'appui ELU :**")
            for role, R in calc['reactions'].items():
                bid   = new_esc.get('poutres_sel',{}).get(role)
                b     = next((b for b in projet.barres if b.id==bid), None)
                nom_p = b.nom if b else "— aucune poutre —"
                gv    = gadd.get(bid, 0) if bid else 0
                Lp    = b.longueur if b else 0
                lbl   = {"depart":"Départ","intermediaire":"Intermédiaire",
                         "arrivee":"Arrivée"}.get(role, role)
                st.markdown(
                    f"- **{lbl}** : R={R:.1f}kN → {nom_p} "
                    + (f"G_add={gv:.2f}kN/m (L={Lp:.2f}m)"
                       if gv>0 else "⚠ poutre non sélectionnée"))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            lbl_save = ("💾 Enregistrer" if is_edit else "✅ Valider et ajouter")
            if st.button(lbl_save, type="primary", use_container_width=True):
                new_esc['gadd'] = gadd
                if is_edit and idx is not None:
                    st.session_state.escaliers[idx] = new_esc
                else:
                    st.session_state.escaliers.append(new_esc)
                st.session_state.esc_mode     = "liste"
                st.session_state.esc_edit_idx = None
                st.session_state.esc_form_kp  = None
                st.rerun()
        with c2:
            if st.button("✖ Annuler", use_container_width=True):
                st.session_state.esc_mode     = "liste"
                st.session_state.esc_edit_idx = None
                st.session_state.esc_form_kp  = None
                st.rerun()
