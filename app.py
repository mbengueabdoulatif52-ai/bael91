"""
app.py — Application Streamlit BAEL 91
v3.1 : Option C — import Excel de saisie
"""
import streamlit as st
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="BAEL 91 — Dimensionnement béton armé",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>
.main-title{font-size:1.8rem;font-weight:700;color:#1F3864;margin-bottom:.2rem}
.sub-title{font-size:1rem;color:#666;margin-bottom:1.5rem}
.section-header{background:#1F3864;color:white;padding:6px 14px;
    border-radius:6px;font-weight:600;margin:1rem 0 .5rem}
.metric-card{background:#F0F4FA;border-radius:8px;
    padding:12px 16px;text-align:center}
.metric-val{font-size:1.6rem;font-weight:700;color:#1F3864}
.metric-lbl{font-size:.78rem;color:#666}
</style>""", unsafe_allow_html=True)

# ── Imports ────────────────────────────────────────────────────────────────────
from core import (
    Materiaux, Noeud, Barre, Dalle, Semelle, Projet,
    lancer_calcul, valider_topologie,
    calc_niveaux, calc_barres, calc_dalles,
    lire_excel, valider_coherence,
)
from ui.gestion_projets import (
    charger_projets, sauvegarder_projet, nouveau_projet,
    charger_projet, serialiser_projet,
)
from ui.resultats import page_resultats
from ui.visualisation import page_visualisation

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [("projet", None), ("resultats", None), ("page", "accueil")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ BAEL 91")
    st.markdown("*Dimensionnement béton armé*")
    st.divider()

    pages = {
        "🏠 Accueil":       "accueil",
        "📥 Import & Calcul":"import",
        "📊 Résultats":     "resultats",
        "🔷 Visualisation": "visualisation",
        "💾 Projets":       "projets",
    }
    for label, key in pages.items():
        btn_type = "primary" if st.session_state.page == key else "secondary"
        if st.button(label, use_container_width=True,
                     type=btn_type, key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()

    st.divider()

    # Projet actif
    if st.session_state.projet:
        p = st.session_state.projet
        st.markdown(f"**Actif :** `{p.nom}`")
        st.caption(
            f"{len(p.noeuds)} nœuds · "
            f"{len(p.barres)} barres · "
            f"{len(p.dalles)} dalles"
        )
        if st.session_state.resultats:
            st.markdown("✅ *Calcul effectué*")
        if st.button("💾 Sauvegarder", use_container_width=True):
            sauvegarder_projet(p)
            st.toast("Projet sauvegardé ✅")
    else:
        st.caption("Aucun projet actif")


# ── PAGES ──────────────────────────────────────────────────────────────────────
page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# ACCUEIL
# ══════════════════════════════════════════════════════════════════════════════
if page == "accueil":
    st.markdown(
        '<div class="main-title">🏗️ BAEL 91 — Dimensionnement béton armé</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Outil de calcul pour structures en béton armé '
        '— BAEL 91 révisé 99</div>',
        unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,(val,lbl) in zip([c1,c2,c3,c4],[
        ("500+","Nœuds max"),("500+","Barres max"),
        ("200+","Dalles max"),("✓","BAEL 91 révisé 99")
    ]):
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-val">{val}</div>'
            f'<div class="metric-lbl">{lbl}</div></div>',
            unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔄 Workflow recommandé")
        st.markdown("""
1. **📥 Télécharger** le fichier Excel de saisie modèle
2. **✏️ Remplir** vos données dans Excel (nœuds, barres, dalles...)
3. **📤 Importer** le fichier dans l'application
4. **⚡ Calculer** automatiquement
5. **📊 Consulter** les résultats et exporter PDF/Excel
        """)
    with col2:
        st.markdown("### 📋 Fonctionnalités")
        st.markdown("""
- Dalles hourdis et pleines (coefficients BAEL Annexe E3)
- Poutres continues (méthode de Clapeyron)
- Poteaux avec flambement BAEL 99
- Descente de charges complète
- Semelles centrées et excentriques + longrines
- Export PDF (Unicode) et Excel
- Visualisation 3D interactive
- Sauvegarde projets JSON
        """)

    st.info(
        "💡 **Important** : G dans les dalles = charges permanentes "
        "**incluant le poids propre** (ρba × épaisseur). "
        "Exemple hourdis 16+4 : G = charges superposées + 25×0.20 = G + 5.0 kN/m²"
    )

    st.divider()
    st.markdown("### 📥 Télécharger le fichier Excel de saisie")
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown(
            "Le fichier contient 6 feuilles pré-remplies avec un projet R+3 "
            "de démonstration : **Matériaux, Nœuds, Barres, Dalles, "
            "Fondations, Guide**."
        )
    with col2:
        try:
            # Chemin relatif au dossier de l'app (Cloud-ready)
            _excel_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "BAEL91_Saisie_v13.xlsx"
            )
            with open(_excel_path, "rb") as f:
                st.download_button(
                    "⬇ Télécharger BAEL91_Saisie_v13.xlsx",
                    data=f.read(),
                    file_name="BAEL91_Saisie_v13.xlsx",
                    mime="application/vnd.openxmlformats-officedocument"
                         ".spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                )
        except FileNotFoundError:
            st.warning("Fichier modèle non trouvé.")


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT & CALCUL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "import":
    st.markdown(
        '<div class="section-header">📥 Import du fichier Excel & Calcul</div>',
        unsafe_allow_html=True)

    st.markdown("""
    **Workflow :**
    1. Remplissez le fichier Excel de saisie (téléchargeable depuis l'Accueil)
    2. Glissez-déposez le fichier ci-dessous
    3. Vérifiez les données importées
    4. Lancez le calcul
    """)

    # ── Upload ─────────────────────────────────────────────────────────────────
    st.markdown("#### Étape 1 — Importer le fichier Excel")
    uploaded = st.file_uploader(
        "Glissez votre fichier BAEL91_Saisie.xlsx ici",
        type=["xlsx"],
        key="uploader_excel",
        help="Fichier Excel avec les feuilles : Materiaux, Noeuds, Barres, "
             "Dalles, Fondations"
    )

    if uploaded:
        with st.spinner("Lecture du fichier Excel..."):
            projet, erreurs = lire_excel(uploaded)
            avertissements  = valider_coherence(projet)

        # ── Résumé import ──────────────────────────────────────────────────────
        st.markdown("#### Étape 2 — Données importées")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Nœuds",    len(projet.noeuds))
        c2.metric("Barres",   len(projet.barres))
        c3.metric("Dalles",   len(projet.dalles))
        c4.metric("Semelles", len(projet.semelles))
        c5.metric("Erreurs",  len(erreurs),
                  delta=f"{len(erreurs)} problème(s)" if erreurs else "Aucune",
                  delta_color="inverse")

        # Erreurs bloquantes
        err_bloquantes = [e for e in erreurs
                         if not e.startswith("Avertissement")
                         and "semble faible" not in e
                         and "ne sera pas calculée" not in e
                         and "inexistant" not in e]

        if erreurs:
            with st.expander(
                f"⚠ {len(erreurs)} message(s) lors de l'import",
                expanded=True
            ):
                for e in erreurs:
                    st.warning(e)

        if avertissements:
            with st.expander(f"ℹ {len(avertissements)} avertissement(s)"):
                for a in avertissements:
                    st.info(a)

        # Aperçu des données
        with st.expander("👁 Aperçu des données"):
            tab1,tab2,tab3,tab4 = st.tabs(
                ["Matériaux","Nœuds","Barres","Dalles"])
            with tab1:
                m = projet.materiaux
                import pandas as pd
                df_m = pd.DataFrame([
                    ("fc28", f"{m.fc28:.0f} MPa"),
                    ("fe",   f"{m.fe:.0f} MPa"),
                    ("q_adm",f"{m.q_adm:.0f} kN/m²"),
                    ("Classe exposition", m.classe_exposition),
                    ("Enrobage poutres",  f"{m.c_poutre*100:.0f} cm"),
                    ("Enrobage dalles",   f"{m.c_dalle*100:.0f} cm"),
                ], columns=["Paramètre","Valeur"])
                st.dataframe(df_m, hide_index=True, use_container_width=True)
            with tab2:
                import pandas as pd
                df_n = pd.DataFrame([
                    {"ID":n.id,"X":n.x,"Y":n.y,"Z":n.z}
                    for n in projet.noeuds[:20]
                ])
                st.dataframe(df_n, hide_index=True)
                if len(projet.noeuds) > 20:
                    st.caption(
                        f"... et {len(projet.noeuds)-20} autres nœuds")
            with tab3:
                import pandas as pd
                from core.topologie import calc_niveaux, calc_barres
                calc_niveaux(projet); calc_barres(projet)
                df_b = pd.DataFrame([{
                    "ID":b.id,"Nom":b.nom,
                    "Ni":b.ni,"Nj":b.nj,
                    "Type":b.type_elem,
                    "b(m)":b.b,"h(m)":b.h,
                    "L(m)":round(b.longueur,2),
                } for b in projet.barres[:20]])
                st.dataframe(df_b, hide_index=True)
                if len(projet.barres) > 20:
                    st.caption(f"... et {len(projet.barres)-20} autres barres")
            with tab4:
                import pandas as pd
                df_d = pd.DataFrame([{
                    "ID":d.id,
                    "Nœuds":str(d.noeuds[:4])+"..." if len(d.noeuds)>4
                            else str(d.noeuds),
                    "Type":d.type_dalle,
                    "Sens":d.sens_lx,
                    "G":d.G,"Q":d.Q,
                } for d in projet.dalles])
                st.dataframe(df_d, hide_index=True)

        # Nom du projet
        st.markdown("#### Étape 3 — Nommer le projet")
        nom = st.text_input("Nom du projet", value=projet.nom,
                            key="nom_projet_import")
        projet.nom = nom

        # ── Calcul ─────────────────────────────────────────────────────────────
        st.markdown("#### Étape 4 — Lancer le calcul")

        can_calc = len(projet.noeuds) > 0 and len(projet.barres) > 0

        if not can_calc:
            st.error("Impossible de calculer : nœuds ou barres manquants.")
        else:
            # Vérification topologie
            calc_niveaux(projet); calc_barres(projet); calc_dalles(projet)
            topo_errors = valider_topologie(projet)
            if topo_errors:
                st.error("**Erreurs de topologie :**")
                for e in topo_errors:
                    st.markdown(f"- {e}")

            if st.button("🚀 Lancer le calcul BAEL 91",
                         type="primary", use_container_width=True,
                         disabled=bool(topo_errors)):
                with st.spinner("Calcul BAEL 91 en cours..."):
                    try:
                        res = lancer_calcul(projet)
                        st.session_state.projet   = projet
                        st.session_state.resultats = res

                        nb_alertes = (
                            sum(1 for r in res.poutres if r.alerte) +
                            sum(1 for r in res.poteaux if r.alerte_am)
                        )
                        st.success(
                            f"✅ Calcul terminé — "
                            f"{len(res.poutres)} poutres · "
                            f"{len(res.poteaux)} poteaux · "
                            f"{len(res.dalles)} dalles"
                            + (f" · ⚠ {nb_alertes} alerte(s)"
                               if nb_alertes else "")
                        )

                        # Sauvegarde automatique
                        sauvegarder_projet(projet)

                        # Redirection
                        st.session_state.page = "resultats"
                        st.rerun()

                    except Exception as e:
                        import traceback
                        st.error(f"Erreur pendant le calcul : {e}")
                        st.code(traceback.format_exc())

    else:
        # Pas encore de fichier uploadé
        st.info(
            "👆 Glissez votre fichier Excel de saisie ci-dessus. "
            "Si vous n'avez pas encore le fichier modèle, "
            "téléchargez-le depuis la page **Accueil**."
        )

        # Charger un projet sauvegardé
        st.divider()
        st.markdown("#### Ou ouvrir un projet sauvegardé")
        projets_lst = charger_projets()
        if projets_lst:
            noms = [p["nom"] for p in projets_lst]
            choix = st.selectbox("Projet", noms, key="sel_proj_import")
            if st.button("📂 Ouvrir ce projet", use_container_width=True):
                pf = next(p["fichier"] for p in projets_lst
                          if p["nom"] == choix)
                st.session_state.projet   = charger_projet(pf)
                st.session_state.resultats = None
                st.toast(f"Projet '{choix}' chargé ✅")
                st.rerun()
        else:
            st.caption("Aucun projet sauvegardé.")


# ══════════════════════════════════════════════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "resultats":
    page_resultats(st.session_state.resultats, st.session_state.projet)


# ══════════════════════════════════════════════════════════════════════════════
# VISUALISATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "visualisation":
    page_visualisation(
        st.session_state.projet,
        st.session_state.resultats
    )


# ══════════════════════════════════════════════════════════════════════════════
# GESTION PROJETS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "projets":
    st.markdown(
        '<div class="section-header">💾 Gestion des projets</div>',
        unsafe_allow_html=True)

    projets_lst = charger_projets()

    if not projets_lst:
        st.info("Aucun projet sauvegardé.")
    else:
        import pandas as pd
        df_p = pd.DataFrame([{
            "Nom": p["nom"],
            "Fichier": Path(p["fichier"]).name,
        } for p in projets_lst])
        st.dataframe(df_p, use_container_width=True, hide_index=True)

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            choix = st.selectbox(
                "Sélectionner un projet",
                [p["nom"] for p in projets_lst],
                key="sel_proj_gestion"
            )
            if st.button("📂 Charger", use_container_width=True):
                pf = next(p["fichier"] for p in projets_lst
                          if p["nom"] == choix)
                st.session_state.projet    = charger_projet(pf)
                st.session_state.resultats = None
                st.toast(f"'{choix}' chargé ✅")
                st.rerun()

        with col2:
            if st.session_state.projet:
                if st.button("💾 Sauvegarder le projet actif",
                             use_container_width=True):
                    sauvegarder_projet(st.session_state.projet)
                    st.toast("Sauvegardé ✅")
                    st.rerun()
