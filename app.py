"""
ui/saisie.py — Pages de saisie des données
Corrections v1.1 :
  - Sauvegarde automatique à chaque modification
  - Bouton ➕ dans toutes les pages même si liste vide
  - Pas de perte de données lors de la navigation
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core import Projet, Noeud, Barre, Dalle, Semelle


def page_saisie(section: str, projet: Projet):
    handlers = {
        "materiaux":  _saisie_materiaux,
        "noeuds":     _saisie_noeuds,
        "barres":     _saisie_barres,
        "dalles":     _saisie_dalles,
        "fondations": _saisie_fondations,
    }
    fn = handlers.get(section)
    if fn:
        fn(projet)


# ── Matériaux ──────────────────────────────────────────────────────────────────
def _saisie_materiaux(p: Projet):
    st.markdown("## 📋 Matériaux et paramètres BAEL 91")
    st.info("💡 G dans les dalles = charges permanentes **incluant le poids propre** de la dalle.")
    m = p.materiaux

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Béton")
        m.fc28   = st.number_input("fc28 (MPa)", 16.0, 50.0, float(m.fc28), 1.0)
        m.gammab = st.number_input("γb", 1.0, 2.0, float(m.gammab), 0.05)
        m.rhoba  = st.number_input("ρba (kN/m³)", 20.0, 30.0, float(m.rhoba), 0.5)
        st.caption(f"fbu = {m.fbu:.2f} MPa · ftj = {m.ftj:.2f} MPa")
    with col2:
        st.markdown("#### Acier")
        m.fe     = st.number_input("fe (MPa)", 235.0, 500.0, float(m.fe), 5.0)
        m.gammas = st.number_input("γs", 1.0, 2.0, float(m.gammas), 0.05)
        st.caption(f"fsu = {m.fsu:.2f} MPa")
        st.markdown("#### Enrobages")
        m.c_poutre = st.number_input("c poutres (m)", 0.01, 0.10, float(m.c_poutre), 0.005, format="%.3f")
        m.c_dalle  = st.number_input("c dalles (m)",  0.01, 0.10, float(m.c_dalle),  0.005, format="%.3f")
        m.c_poteau = st.number_input("c poteaux (m)", 0.01, 0.10, float(m.c_poteau), 0.005, format="%.3f")
        m.c_fond   = st.number_input("c fondations (m)", 0.01, 0.10, float(m.c_fond), 0.005, format="%.3f")
    with col3:
        st.markdown("#### Fondations")
        m.Df    = st.number_input("Profondeur Df (m)", 0.5, 5.0, float(m.Df), 0.1)
        m.q_adm = st.number_input("q_adm (kN/m²)", 50.0, 500.0, float(m.q_adm), 10.0)

    st.success("✅ Matériaux sauvegardés automatiquement")


# ── Nœuds ──────────────────────────────────────────────────────────────────────
def _saisie_noeuds(p: Projet):
    st.markdown("## 📍 Nœuds")

    # ── Formulaire d'ajout ─────────────────────────────────────────────────────
    with st.expander("➕ Ajouter un nœud", expanded=not bool(p.noeuds)):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            new_id = st.number_input("ID", 1, 9999,
                max([n.id for n in p.noeuds], default=0) + 1,
                key="add_n_id")
        with c2:
            new_x = st.number_input("X (m)", value=0.0, format="%.2f", key="add_n_x")
        with c3:
            new_y = st.number_input("Y (m)", value=0.0, format="%.2f", key="add_n_y")
        with c4:
            new_z = st.number_input("Z (m)", value=0.0, format="%.2f", key="add_n_z")

        if st.button("➕ Ajouter ce nœud", type="primary", key="btn_add_n"):
            ids_existants = {n.id for n in p.noeuds}
            if int(new_id) in ids_existants:
                st.error(f"L'ID {int(new_id)} existe déjà.")
            else:
                p.noeuds.append(Noeud(
                    id=int(new_id), x=float(new_x),
                    y=float(new_y), z=float(new_z)
                ))
                st.success(f"✅ Nœud N{int(new_id)} ajouté")
                st.rerun()

    # ── Ajout multiple ─────────────────────────────────────────────────────────
    with st.expander("➕ Ajouter plusieurs nœuds (tableau)"):
        st.caption("Saisissez vos nœuds puis cliquez Enregistrer. Les données sont conservées.")
        df_new = pd.DataFrame({"ID": pd.Series(dtype=int),
                               "X (m)": pd.Series(dtype=float),
                               "Y (m)": pd.Series(dtype=float),
                               "Z (m)": pd.Series(dtype=float)})
        edited = st.data_editor(df_new, num_rows="dynamic",
                                use_container_width=True, key="editor_noeuds_multi")
        if st.button("💾 Enregistrer ces nœuds", key="save_n_multi"):
            ids_existants = {n.id for n in p.noeuds}
            nb = 0
            for _, r in edited.iterrows():
                if pd.notna(r.get("ID")) and int(r["ID"]) not in ids_existants:
                    p.noeuds.append(Noeud(
                        id=int(r["ID"]), x=float(r["X (m)"]),
                        y=float(r["Y (m)"]), z=float(r["Z (m)"])
                    ))
                    ids_existants.add(int(r["ID"]))
                    nb += 1
            if nb:
                st.success(f"✅ {nb} nœuds ajoutés")
                st.rerun()

    # ── Tableau existant ───────────────────────────────────────────────────────
    if p.noeuds:
        st.markdown(f"**{len(p.noeuds)} nœud(s) défini(s)**")
        df = pd.DataFrame([
            {"ID": n.id, "X (m)": n.x, "Y (m)": n.y, "Z (m)": n.z}
            for n in sorted(p.noeuds, key=lambda n: n.id)
        ])
        edited2 = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            key="editor_noeuds_edit",
            column_config={
                "ID":    st.column_config.NumberColumn(min_value=1, step=1),
                "X (m)": st.column_config.NumberColumn(format="%.2f"),
                "Y (m)": st.column_config.NumberColumn(format="%.2f"),
                "Z (m)": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Appliquer les modifications", type="primary",
                         key="save_noeuds_edit", use_container_width=True):
                p.noeuds = [
                    Noeud(id=int(r["ID"]), x=float(r["X (m)"]),
                          y=float(r["Y (m)"]), z=float(r["Z (m)"]))
                    for _, r in edited2.iterrows()
                    if pd.notna(r.get("ID"))
                ]
                st.success(f"✅ {len(p.noeuds)} nœuds enregistrés")
                st.rerun()
        with col2:
            if st.button("🗑️ Vider la liste", key="clear_noeuds",
                         use_container_width=True):
                p.noeuds = []
                st.rerun()
    else:
        st.info("Aucun nœud défini. Utilisez le formulaire ci-dessus pour en ajouter.")

    # ── Import Excel ───────────────────────────────────────────────────────────
    with st.expander("📥 Importer depuis Excel/CSV"):
        upl = st.file_uploader("Fichier (colonnes : ID, X, Y, Z)",
                               type=["xlsx", "csv"], key="upl_noeuds")
        if upl:
            try:
                df_imp = pd.read_csv(upl) if upl.name.endswith(".csv") \
                         else pd.read_excel(upl)
                cols = list(df_imp.columns)
                st.dataframe(df_imp.head(5))
                if st.button("✅ Importer", key="btn_imp_noeuds"):
                    p.noeuds = [
                        Noeud(id=int(r[cols[0]]), x=float(r[cols[1]]),
                              y=float(r[cols[2]]), z=float(r[cols[3]]))
                        for _, r in df_imp.iterrows()
                    ]
                    st.success(f"✅ {len(p.noeuds)} nœuds importés")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur import : {e}")


# ── Barres ─────────────────────────────────────────────────────────────────────
def _saisie_barres(p: Projet):
    st.markdown("## 📏 Barres (poutres et poteaux)")
    st.caption("Le type (poutre/poteau) et la longueur sont calculés automatiquement "
               "depuis les coordonnées des nœuds.")

    # ── Formulaire d'ajout ─────────────────────────────────────────────────────
    with st.expander("➕ Ajouter une barre", expanded=not bool(p.barres)):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_id  = st.number_input("ID", 1, 9999,
                max([b.id for b in p.barres], default=0) + 1, key="add_b_id")
            new_nom = st.text_input("Nom", f"B{max([b.id for b in p.barres], default=0)+1}",
                                    key="add_b_nom")
            new_ni  = st.number_input("Nœud i", 1, 9999, 1, key="add_b_ni",
                                      help="ID du nœud initial")
            new_nj  = st.number_input("Nœud j", 1, 9999, 2, key="add_b_nj",
                                      help="ID du nœud final")
        with c2:
            new_b = st.number_input("Largeur b (m)", 0.10, 2.00, 0.25, 0.05,
                                    format="%.2f", key="add_b_b")
            new_h = st.number_input("Hauteur h (m)", 0.10, 3.00, 0.40, 0.05,
                                    format="%.2f", key="add_b_h")
        with c3:
            new_Gadd = st.number_input("G_add (kN/m)", 0.0, 50.0, 0.0, 0.5,
                                       key="add_b_G",
                                       help="Charges permanentes additionnelles sur la barre")
            new_Qadd = st.number_input("Q_add (kN/m)", 0.0, 50.0, 0.0, 0.5,
                                       key="add_b_Q",
                                       help="Charges variables additionnelles sur la barre")

        if st.button("➕ Ajouter cette barre", type="primary", key="btn_add_b"):
            ids_existants = {b.id for b in p.barres}
            if int(new_id) in ids_existants:
                st.error(f"L'ID {int(new_id)} existe déjà.")
            elif int(new_ni) == int(new_nj):
                st.error("Ni et Nj doivent être différents.")
            else:
                p.barres.append(Barre(
                    id=int(new_id), nom=str(new_nom),
                    ni=int(new_ni), nj=int(new_nj),
                    b=float(new_b), h=float(new_h),
                    G_add=float(new_Gadd), Q_add=float(new_Qadd)
                ))
                st.success(f"✅ Barre {new_nom} ajoutée")
                st.rerun()

    # ── Ajout multiple ─────────────────────────────────────────────────────────
    with st.expander("➕ Ajouter plusieurs barres (tableau)"):
        df_new = pd.DataFrame({
            "ID": pd.Series(dtype=int), "Nom": pd.Series(dtype=str),
            "Ni": pd.Series(dtype=int), "Nj": pd.Series(dtype=int),
            "b (m)": pd.Series(dtype=float), "h (m)": pd.Series(dtype=float),
            "G_add": pd.Series(dtype=float), "Q_add": pd.Series(dtype=float),
        })
        edited = st.data_editor(df_new, num_rows="dynamic",
                                use_container_width=True, key="editor_barres_multi")
        if st.button("💾 Enregistrer", key="save_b_multi"):
            ids_existants = {b.id for b in p.barres}
            nb = 0
            for _, r in edited.iterrows():
                if pd.notna(r.get("ID")) and int(r["ID"]) not in ids_existants:
                    p.barres.append(Barre(
                        id=int(r["ID"]),
                        nom=str(r.get("Nom", f"B{int(r['ID'])}")),
                        ni=int(r["Ni"]), nj=int(r["Nj"]),
                        b=float(r["b (m)"]), h=float(r["h (m)"]),
                        G_add=float(r.get("G_add", 0)),
                        Q_add=float(r.get("Q_add", 0))
                    ))
                    ids_existants.add(int(r["ID"]))
                    nb += 1
            if nb:
                st.success(f"✅ {nb} barres ajoutées")
                st.rerun()

    # ── Tableau existant ───────────────────────────────────────────────────────
    if p.barres:
        # Calculer les types depuis la topologie
        from core.topologie import calc_niveaux, calc_barres
        try:
            calc_niveaux(p); calc_barres(p)
        except Exception:
            pass

        st.markdown(f"**{len(p.barres)} barre(s) définie(s)**")
        df = pd.DataFrame([{
            "ID": b.id, "Nom": b.nom,
            "Ni": b.ni, "Nj": b.nj,
            "Type": b.type_elem if b.type_elem else "?",
            "L (m)": round(b.longueur, 2) if b.longueur else "?",
            "b (m)": b.b, "h (m)": b.h,
            "G_add": b.G_add, "Q_add": b.Q_add,
        } for b in sorted(p.barres, key=lambda b: b.id)])

        edited2 = st.data_editor(
            df, num_rows="dynamic", use_container_width=True,
            key="editor_barres_edit",
            disabled=["Type", "L (m)"],
            column_config={
                "ID":    st.column_config.NumberColumn(min_value=1, step=1),
                "Ni":    st.column_config.NumberColumn(min_value=1, step=1),
                "Nj":    st.column_config.NumberColumn(min_value=1, step=1),
                "b (m)": st.column_config.NumberColumn(min_value=0.05, max_value=3.0, format="%.2f"),
                "h (m)": st.column_config.NumberColumn(min_value=0.05, max_value=3.0, format="%.2f"),
                "G_add": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                "Q_add": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
            }
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Appliquer les modifications", type="primary",
                         key="save_barres_edit", use_container_width=True):
                p.barres = [
                    Barre(id=int(r["ID"]), nom=str(r["Nom"]),
                          ni=int(r["Ni"]), nj=int(r["Nj"]),
                          b=float(r["b (m)"]), h=float(r["h (m)"]),
                          G_add=float(r["G_add"]), Q_add=float(r["Q_add"]))
                    for _, r in edited2.iterrows()
                    if pd.notna(r.get("ID"))
                ]
                st.success(f"✅ {len(p.barres)} barres enregistrées")
                st.rerun()
        with col2:
            if st.button("🗑️ Vider la liste", key="clear_barres",
                         use_container_width=True):
                p.barres = []
                st.rerun()
    else:
        st.info("Aucune barre définie. Utilisez le formulaire ci-dessus.")


# ── Dalles ─────────────────────────────────────────────────────────────────────
def _saisie_dalles(p: Projet):
    st.markdown("## ▪ Dalles")
    st.warning("**G = charges permanentes incluant le poids propre** "
               "(ex : hourdis 16+4 : G = superposé + 25×0.20 = G + 5.0 kN/m²)")

    # ── Formulaire d'ajout ─────────────────────────────────────────────────────
    with st.expander("➕ Ajouter une dalle", expanded=not bool(p.dalles)):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_id   = st.number_input("ID dalle", 1, 9999,
                max([d.id for d in p.dalles], default=0) + 1, key="add_d_id")
            new_nds  = st.text_input("Nœuds (séparés par virgule)",
                                     "1,2,5,4", key="add_d_nds",
                                     help="Min 3, max 8 nœuds, sens anti-horaire")
        with c2:
            new_G    = st.number_input("G (kN/m²)", 0.0, 50.0, 8.5, 0.5, key="add_d_G",
                                       help="Inclure le poids propre de la dalle")
            new_Q    = st.number_input("Q (kN/m²)", 0.0, 20.0, 2.5, 0.5, key="add_d_Q")
        with c3:
            new_typ  = st.selectbox("Type", ["Hourdis", "Dalle pleine"], key="add_d_type")
            new_sens = st.selectbox("Sens portée",
                                    ["Sens X", "Sens Y", "XY"],
                                    key="add_d_sens",
                                    help="Hourdis : imposer Sens X ou Y. Dalle pleine : XY si carrée")
            new_e    = 0.0
            if new_typ == "Dalle pleine":
                new_e = st.number_input("Épaisseur e (m)", 0.08, 0.50, 0.20, 0.01,
                                        format="%.2f", key="add_d_e")

        if st.button("➕ Ajouter cette dalle", type="primary", key="btn_add_d"):
            try:
                nds = [int(x.strip()) for x in new_nds.split(",")]
                if len(nds) < 3:
                    st.error("Minimum 3 nœuds.")
                else:
                    p.dalles.append(Dalle(
                        id=int(new_id), noeuds=nds,
                        G=float(new_G), Q=float(new_Q),
                        sens_lx=new_sens,
                        type_dalle="Hourdis" if new_typ == "Hourdis" else "Pleine",
                        e_dalle=float(new_e)
                    ))
                    st.success(f"✅ Dalle D{int(new_id)} ajoutée")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ── Tableau existant ───────────────────────────────────────────────────────
    if p.dalles:
        st.markdown(f"**{len(p.dalles)} dalle(s) définie(s)**")
        df = pd.DataFrame([{
            "ID": d.id,
            "Nœuds": ",".join(map(str, d.noeuds)),
            "Sens":  d.sens_lx,
            "G (kN/m²)": d.G,
            "Q (kN/m²)": d.Q,
            "Type": d.type_dalle,
            "e (m)": d.e_dalle if d.type_dalle == "Pleine" else "",
        } for d in sorted(p.dalles, key=lambda d: d.id)])
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("🗑️ Supprimer toutes les dalles", key="clear_dalles"):
            p.dalles = []
            st.rerun()
    else:
        st.info("Aucune dalle définie. Utilisez le formulaire ci-dessus.")


# ── Fondations ─────────────────────────────────────────────────────────────────
def _saisie_fondations(p: Projet):
    st.markdown("## 🏛️ Fondations — Semelles isolées")
    st.info("ex=0 et ey=0 pour une semelle centrée (cas le plus courant).")

    # Générer automatiquement
    if st.button("🔄 Générer les semelles depuis les poteaux niv. 1",
                 type="primary", key="gen_semelles"):
        from core.topologie import calc_niveaux, calc_barres
        calc_niveaux(p); calc_barres(p)
        pots = [b for b in p.barres if b.type_elem == "poteau" and b.niveau == 1]
        ids_existants = {s.id_poteau for s in p.semelles}
        nb = 0
        for b in pots:
            if b.id not in ids_existants:
                p.semelles.append(Semelle(id_poteau=b.id))
                nb += 1
        st.success(f"✅ {nb} semelles générées — {len(p.semelles)} au total")
        st.rerun()

    if p.semelles:
        st.markdown(f"**{len(p.semelles)} semelle(s)**")
        tout_centre = all(s.ex == 0 and s.ey == 0 for s in p.semelles)

        df = pd.DataFrame([{
            "ID poteau": s.id_poteau,
            "ex (m)": s.ex,
            "ey (m)": s.ey,
            "q_adm_loc (kN/m²)": s.q_adm_loc,
        } for s in sorted(p.semelles, key=lambda s: s.id_poteau)])

        if tout_centre:
            st.caption("Toutes les semelles sont centrées (ex=ey=0).")

        edited = st.data_editor(
            df, num_rows="fixed", use_container_width=True,
            key="editor_fonds",
            column_config={
                "ex (m)": st.column_config.NumberColumn(format="%.3f"),
                "ey (m)": st.column_config.NumberColumn(format="%.3f"),
                "q_adm_loc (kN/m²)": st.column_config.NumberColumn(
                    min_value=0.0, help="0 = utiliser la valeur globale des matériaux"),
            }
        )
        if st.button("💾 Appliquer", type="primary", key="save_fonds",
                     use_container_width=True):
            for _, r in edited.iterrows():
                sid = int(r["ID poteau"])
                s = next((s for s in p.semelles if s.id_poteau == sid), None)
                if s:
                    s.ex = float(r["ex (m)"])
                    s.ey = float(r["ey (m)"])
                    s.q_adm_loc = float(r["q_adm_loc (kN/m²)"])
            st.success("✅ Fondations mises à jour")
    else:
        st.info("Cliquez le bouton ci-dessus pour générer les semelles automatiquement "
                "depuis les poteaux de niveau 1.")
