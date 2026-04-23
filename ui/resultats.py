"""
ui/resultats.py
Affichage des résultats de calcul BAEL 91
"""
import streamlit as st
import pandas as pd
import math as _math
import re as _re_mod
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def page_resultats(res, projet):
    if res is None:
        st.warning("⚠ Aucun résultat disponible. Lancez le calcul d'abord.")
        if st.button("⚡ Aller au calcul"):
            st.session_state.page = "calcul"
            st.rerun()
        return

    st.markdown("## 📊 Résultats BAEL 91")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    nb_alertes = (sum(1 for r in res.poutres if r.alerte) +
                  sum(1 for r in res.poteaux if r.alerte_am))

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Poutres", len(res.poutres))
    c2.metric("Poteaux", len(res.poteaux))
    c3.metric("Dalles",  len(res.dalles))
    c4.metric("Alertes ⚠",  nb_alertes,
              delta=f"{nb_alertes} à vérifier" if nb_alertes else "Aucune",
              delta_color="inverse")

    # ── Quantitatif rapide ────────────────────────────────────────────────────
    masse_p = sum(r.As_long * 1e-4 * 5.0 * 7850 for r in res.poutres)
    masse_c = sum(r.As * 1e-4 * 3.0 * 7850 for r in res.poteaux)
    masse_t = masse_p + masse_c
    surface = _surface_projet(projet)
    ratio   = masse_t / surface if surface > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div style='background:#EEF4FF;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.5rem;font-weight:700;color:#1F3864'>{masse_t:,.0f} kg</div>
        <div style='font-size:0.8rem;color:#666'>Total acier estimé</div></div>""",
        unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div style='background:#EEF4FF;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.5rem;font-weight:700;color:#1F3864'>{surface:.0f} m²</div>
        <div style='font-size:0.8rem;color:#666'>Surface plancher</div></div>""",
        unsafe_allow_html=True)
    with col3:
        color = "#2D7D46" if 30 <= ratio <= 45 else "#B54708"
        st.markdown(f"""<div style='background:#EEF4FF;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.5rem;font-weight:700;color:{color}'>{ratio:.1f} kg/m²</div>
        <div style='font-size:0.8rem;color:#666'>Ratio acier (réf 30-45)</div></div>""",
        unsafe_allow_html=True)

    st.divider()

    # ── Onglets ────────────────────────────────────────────────────────────────
    tabs = st.tabs(["🏠 Dalles", "📏 Poutres", "📦 Poteaux", "🏛️ Fondations"])

    # ── Dalles ─────────────────────────────────────────────────────────────────
    with tabs[0]:
        if not res.dalles:
            st.info("Aucune dalle calculée.")
        else:
            df_d = pd.DataFrame([{
                "ID":        r.dalle_id,
                "Type":      r.type_dalle,
                "Hourdis/e": r.typH,
                "Mu_x (kN.m)": f"{r.Mu_x:.2f}",
                "Mu_y (kN.m)": f"{r.Mu_y:.2f}" if r.Mu_y > 0 else "—",
                "As nerv. (cm²)":  f"{r.As_nerv:.2f}",
                "As rép. (cm²)":   f"{r.As_rep:.2f}",
                "Statut":  _statut_dalle(r),
            } for r in res.dalles])
            st.dataframe(df_d, use_container_width=True, hide_index=True)

    # ── Poutres ────────────────────────────────────────────────────────────────
    with tabs[1]:
        if not res.poutres:
            st.info("Aucune poutre calculée.")
        else:
            # Grouper par niveau
            niveaux = sorted(set(
                b.niveau for b in projet.barres
                if b.type_elem == "poutre"
            ), reverse=True)

            for niv in niveaux:
                bids_niv = {b.id for b in projet.barres
                            if b.type_elem == "poutre" and b.niveau == niv}
                poutres_niv = [r for r in res.poutres if r.barre_id in bids_niv]
                if not poutres_niv:
                    continue

                with st.expander(f"Niveau {niv} — {len(poutres_niv)} poutres",
                                  expanded=(niv == max(niveaux))):
                    df_p = pd.DataFrame([{
                        "Élément":       r.etiq,
                        "Section":       r.section,
                        "Mu (kN.m)":     f"{r.Mu:.2f}",
                        "Tu (kN)":       f"{r.Tu:.2f}",
                        "As long. (cm²)": f"{r.As_long:.2f}",
                        "As chap. (cm²)": f"{r.As_chap:.2f}" if r.As_chap > 0 else "—",
                        "As chaîn. (cm²)": f"{r.As_chaine:.2f}" if r.As_chaine > 0 else "—",
                        "At/st (cm²/m)": f"{r.At_st:.2f}",
                        "Statut":        _statut_poutre(r),
                    } for r in poutres_niv])
                    st.dataframe(df_p, use_container_width=True, hide_index=True)

    # ── Poteaux ────────────────────────────────────────────────────────────────
    with tabs[2]:
        if not res.poteaux:
            st.info("Aucun poteau calculé.")
        else:
            niveaux_p = sorted(set(
                b.niveau for b in projet.barres if b.type_elem == "poteau"
            ), reverse=True)

            for niv in niveaux_p:
                bids = {b.id for b in projet.barres
                        if b.type_elem == "poteau" and b.niveau == niv}
                pots_niv = [r for r in res.poteaux if r.barre_id in bids]
                if not pots_niv:
                    continue
                with st.expander(f"Niveau {niv} — {len(pots_niv)} poteaux",
                                  expanded=(niv == 1)):
                    df_c = pd.DataFrame([{
                        "Élément":   r.etiq,
                        "Section":   r.section,
                        "Nu (kN)":   f"{r.Nu:.1f}",
                        "As (cm²)":  f"{r.As:.2f}",
                        "α":         f"{r.alpha:.2f}",
                        "λ":         f"{r.lam:.0f}",
                        "Statut":    _statut_poteau(r, projet),
                    } for r in pots_niv])
                    st.dataframe(df_c, use_container_width=True, hide_index=True)

    # ── Fondations ─────────────────────────────────────────────────────────────
    with tabs[3]:
        if not res.semelles:
            st.info("Aucune semelle calculée.")
        else:
            # ── Tableau semelles ───────────────────────────────────────────────
            # Dictionnaire nom saisi → tous poteaux (tous niveaux)
            noms_pots = {b.id: b.nom for b in projet.barres
                         if b.type_elem == "poteau"}
            def _nom_pot(bid):
                return noms_pots.get(bid, f"C{bid}") if bid else "—"

            st.markdown("#### Semelles isolées")
            df_f = pd.DataFrame([{
                "Poteau":        _nom_pot(s.id_poteau),
                "Type":          "Centrée" if s.ex==0 and s.ey==0 else "Excentrique",
                "ex (m)":        f"{getattr(s,'ex_reel',s.ex):.3f}" if s.ex != 0 else "—",
                "ey (m)":        f"{getattr(s,'ey_reel',s.ey):.3f}" if s.ey != 0 else "—",
                # Note : ex/ey peuvent être signés (signe = sens du décalage)
                # Note : ex et ey peuvent être négatifs (sens du décalage)
                "B×L (m)":       f"{s.B:.2f}×{s.L_sem:.2f}",
                "e (cm)":        f"{s.e_sem*100:.0f}",
                "Nu (kN)":       f"{s.Nu_ser:.1f}",
                "q_max (kN/m²)": f"{s.q_max:.0f}",
                "Asx (cm²/m)":   f"{s.Asx:.2f}",
                "Amorces":       f"4HA{s.phi_amorce}",
                "Statut":        _statut_semelle(s, projet.materiaux.q_adm),
            } for s in res.semelles])
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            # ── Tableau longrines ──────────────────────────────────────────────
            rows_long = []
            for s in res.semelles:
                if s.long_X_As > 0:
                    rows_long.append({
                        "Poteau":         _nom_pot(s.id_poteau),
                        "Direction":      "X",
                        "Vers poteau":    _nom_pot(s.long_X_vers),
                        "Section":        f"{s.b_long_X*100:.0f}×{s.h_long_X*100:.0f} cm",
                        "ex (m)":         f"{s.ex:.3f}",  # signe conservé
                        "Moment (kN.m)":  f"{s.long_X_Mu:.1f}",
                        "As long. (cm²)": f"{s.long_X_As:.2f}",
                        "As chap. (cm²)": f"{s.long_X_As*0.5:.2f}",
                        "Vérif":          s.long_X_vM,
                    })
                if s.long_Y_As > 0:
                    rows_long.append({
                        "Poteau":         _nom_pot(s.id_poteau),
                        "Direction":      "Y",
                        "Vers poteau":    _nom_pot(s.long_Y_vers),
                        "Section":        f"{s.b_long_Y*100:.0f}×{s.h_long_Y*100:.0f} cm",
                        "ey (m)":         f"{s.ey:.3f}",
                        "Moment (kN.m)":  f"{s.long_Y_Mu:.1f}",
                        "As long. (cm²)": f"{s.long_Y_As:.2f}",
                        "As chap. (cm²)": f"{s.long_Y_As*0.5:.2f}",
                        "Vérif":          s.long_Y_vM,
                    })

            if rows_long:
                st.markdown("#### Longrines de redressement")
                st.info(
                    "La longrine de redressement reprend le moment "
                    "M = Nu × e dû à l'excentricité de la semelle. "
                    "As chap. = 50% de As long. (chapeau sur appuis)."
                )
                df_long = pd.DataFrame(rows_long)
                st.dataframe(df_long, use_container_width=True, hide_index=True)
            else:
                # Vérifier s'il y a des semelles excentriques sans longrine définie
                exc_sans_long = [s for s in res.semelles
                                 if (s.ex > 0 or s.ey > 0)
                                 and s.long_X_vers == 0 and s.long_Y_vers == 0]
                if exc_sans_long:
                    ids = ", ".join(_nom_pot(s.id_poteau) for s in exc_sans_long)
                    st.warning(
                        f"⚠ Semelles excentriques détectées ({ids}) sans longrine "
                        "définie. Renseignez le poteau voisin dans la feuille "
                        "Fondations du fichier Excel (colonne Long_X_vers ou Long_Y_vers)."
                    )

    # ── Export ─────────────────────────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Exporter Excel", use_container_width=True):
            try:
                from export.excel_writer import exporter_excel
                buf = exporter_excel(res, projet)
                st.download_button(
                    "⬇ Télécharger le fichier Excel",
                    data=buf, file_name=f"{projet.nom}_resultats.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Erreur export Excel : {e}")
    with col2:
        if st.button("📄 Exporter PDF", use_container_width=True):
            try:
                from export.pdf_writer import exporter_pdf
                buf = exporter_pdf(res, projet)
                st.download_button(
                    "⬇ Télécharger le rapport PDF",
                    data=buf, file_name=f"{projet.nom}_rapport.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur export PDF : {e}")


# ── Utilitaires ────────────────────────────────────────────────────────────────
def _badge(texte: str) -> str:
    """Retourne l'emoji statut selon le texte."""
    if not texte:
        return "—"
    if "REVOIR" in texte.upper():
        return f"⚠ {texte}"
    if "OK" in texte.upper() or "ok" in texte.lower():
        return f"✅ {texte}"
    return texte


def _statut_poteau(r, projet):
    """Statut unifié pour un poteau — messages explicites avec valeurs."""
    b = next((b for b in projet.barres if b.id == r.barre_id), None)
    alertes = []

    if r.alerte_am:
        vS = r.vS or ""
        if "As=" in vS and "As_max" in vS:
            # As > As_max (5% section)
            if b:
                As_max = 0.05 * b.b * 1000 * b.h * 1000 / 100
                alertes.append(
                    f"\u274c As={r.As:.2f} > As_max={As_max:.2f}cm\u00b2 "
                    f"\u2014 augmenter b ou h")
        elif "sig=" in vS and ">" in vS:
            # Contrainte béton dépassée
            import re
            m = re.search("sig=([0-9.]+)>([0-9.]+)MPa", vS)
            if m:
                alertes.append(
                    f"\u274c \u03c3_b\u00e9ton={m.group(1)} > "
                    f"fbu={m.group(2)}MPa \u2014 section insuffisante")
            else:
                alertes.append(f"\u274c Contrainte b\u00e9ton d\u00e9pass\u00e9e")
        elif "REVOIR" in vS.upper():
            alertes.append(f"\u274c {vS}")
        else:
            # vS = "Sect:OK" ou similaire → alerte de recouvrement
            alertes.append(
                f"\u26a0 Recouvrement non conforme "
                f"(variation As > 50% vs niveau sup.)")

    if r.lam > 70:
        alertes.append(
            f"\u274c \u03bb={r.lam:.0f} > 70 "
            f"(hors m\u00e9thode forfaitaire)")

    return " | ".join(alertes) if alertes else "\u2705 OK"

def _statut_poutre(r):
    """Statut unifié pour une poutre — messages explicites avec valeurs."""
    alertes = []
    # Flexion
    if r.mu_r > 0.392:
        alertes.append(
            f"❌ μ={r.mu_r:.3f} > 0.392 (béton insuffisant, revoir b×h)")
    # Cisaillement
    if r.vCis and "REVOIR" in r.vCis.upper():
        alertes.append(f"❌ Cisaillement excessif ({r.vCis})")
    # Flèche — extraire les valeurs du message vFleche
    if r.vFleche and "REVOIR" in r.vFleche.upper():
        m = _re_mod.search(r"f≈([\d.]+)>([\d.]+)mm", r.vFleche)
        if m:
            alertes.append(
                f"⚠ Flèche f≈{m.group(1)}mm > {m.group(2)}mm (indicatif)")
        else:
            alertes.append(f"⚠ Flèche excessive ({r.vFleche})")
    # Hauteur minimale
    if r.vH and "REVOIR" in r.vH.upper():
        alertes.append(f"⚠ {r.vH}")
    return " | ".join(alertes) if alertes else "✅ OK"


def _statut_dalle(r):
    """Statut unifié pour une dalle — messages explicites."""
    alertes = []
    if r.alerte:
        # Flexion
        if hasattr(r, 'mu_r') and r.mu_r > 0.392:
            alertes.append(
                f"❌ μ={r.mu_r:.3f} > 0.392 (section insuffisante)")
        elif r.vFlex and "REVOIR" in r.vFlex.upper():
            alertes.append(f"❌ Section insuffisante ({r.vFlex})")
        # Hauteur hourdis
        if hasattr(r, 'vH') and r.vH and "REVOIR" in r.vH.upper():
            alertes.append(f"⚠ {r.vH}")
        # Fallback
        if not alertes:
            alertes.append("⚠ REVOIR")
    return " | ".join(alertes) if alertes else "✅ OK"


def _statut_semelle(s, q_adm):
    """Statut unifié pour une semelle — lit sem.alertes calculées dans fondations.py."""
    # Utiliser la liste d'alertes calculée par le moteur
    alertes = getattr(s, 'alertes', None)
    if alertes is None:
        # Rétrocompatibilité — recalculer si alertes non disponibles
        alertes = []
        if hasattr(s, 'q_min') and s.q_min is not None and s.q_min < 0:
            alertes.append(f"❌ Soulèvement (q_min={s.q_min:.0f}kN/m²<0)")
        if s.q_max > q_adm * 1.01:
            alertes.append(
                f"❌ q_max={s.q_max:.0f} > q_adm={q_adm:.0f}kN/m²")
        if s.alerte and not alertes:
            alertes.append(f"⚠ {s.alerte}")
    if not alertes:
        return "✅ OK"
    return " | ".join(alertes)

def _surface_projet(projet) -> float:
    """Estime la surface totale du plancher."""
    if not projet or not projet.noeuds:
        return 150.0
    xs = [n.x for n in projet.noeuds]
    ys = [n.y for n in projet.noeuds]
    if xs and ys:
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    return 150.0
