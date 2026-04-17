"""
principal.py
Équivalent de 8_Mod_Principal.bas
Orchestration du calcul : descente de charges, dimensionnement niveau par niveau.
Architecture identique au VBA :
- Chaque barre traitée indépendamment
- Descente de charges du niveau le plus haut vers le bas
- Fondations en dernier
"""
from typing import List, Dict
from .declarations import (
    Projet, Barre, Travee,
    ResultatPoutre, ResultatPoteau, ResultatDalle
)
from .charges import charges_totales_poutre, calc_chainage_rive
from .trois_moments import calc_poutre_contin
from .bael import dim_poutre, dim_poteau, dim_dalle
from .fondations import calc_toutes_semelles
from .topologie import est_poutre_de_rive, index_noeud


class ResultatsProjet:
    def __init__(self):
        self.poutres:   List[ResultatPoutre] = []
        self.poteaux:   List[ResultatPoteau] = []
        self.dalles:    List[ResultatDalle]  = []
        self.semelles   = []
        self.charges_reportees: Dict[int, float] = {}
        self.niveaux_calcules:  List[int] = []


def lancer_calcul(projet: Projet) -> ResultatsProjet:
    """
    Calcul complet BAEL 91.
    Suit exactement la séquence du VBA :
    1. Géométrie
    2. Pour chaque niveau (haut → bas) :
       a. Dalles (dimensionnement)
       b. Poutres (Clapeyron + BAEL)
       c. Poteaux (descente + BAEL)
    3. Fondations
    """
    from .topologie import calc_niveaux, calc_barres, calc_dalles

    calc_niveaux(projet)
    calc_barres(projet)
    calc_dalles(projet)

    res = ResultatsProjet()
    # charges_reportees : index 1-based dans projet.noeuds
    charges: Dict[int, float] = {}

    noeud_map = {n.id: n for n in projet.noeuds}

    # ── Descente de charges : niveau le plus haut en premier ─────────────────
    for niv in range(projet.nb_niveaux, 0, -1):

        # ── Dalles ────────────────────────────────────────────────────────────
        for d in projet.dalles:
            if d.niveau == niv:
                rd = dim_dalle(d, projet.materiaux)
                res.dalles.append(rd)

        # ── Poutres ───────────────────────────────────────────────────────────
        for barre in projet.barres:
            if barre.type_elem != "poutre" or barre.niveau != niv:
                continue

            # Charges des dalles sur cette barre
            q_dalle = charges_totales_poutre(barre, projet)

            # Clapeyron : pp et G_add ajoutés dans calc_poutre_contin
            travees = calc_poutre_contin(barre, q_dalle, projet)
            nb_tv = len(travees)

            for it, tv in enumerate(travees, 1):
                b_p = barre.b if barre.b > 0 else 0.25
                h_p = barre.h if barre.h > 0 else 0.50
                q_ser = tv.q / 1.35
                Ms = q_ser * tv.L**2 / 8

                r = dim_poutre(
                    Mu=tv.Mu_span,
                    Tu=max(tv.Tu_i, tv.Tu_j),
                    Ms=Ms,
                    b=b_p, h=h_p, L=tv.L,
                    mat=projet.materiaux,
                    M_appui=max(abs(tv.Mu_appui_i), abs(tv.Mu_appui_j)),
                )

                # Chaînage rive
                As_chaine = 0.0
                if est_poutre_de_rive(barre, projet.dalles):
                    Nu_app = _nu_poteau_about(barre, charges, projet)
                    _, As_chaine, _ = calc_chainage_rive(barre, Nu_app)
                    # Appliquer fe du matériau
                    T = max(0.01 * Nu_app, 20.0)
                    As_chaine = max(T * 1000 / (projet.materiaux.fsu) / 100, 1.0)

                etiq = (f"P{barre.id}({barre.ni}-{barre.nj})" if nb_tv == 1
                        else f"P{barre.id} T{it}({tv.ni}-{tv.nj})")

                rp = ResultatPoutre(
                    barre_id=barre.id, travee=it, etiq=etiq,
                    Mu=round(tv.Mu_span, 2),
                    Tu=round(max(tv.Tu_i, tv.Tu_j), 2),
                    As_long=r["As_long"], As_chap=r["As_chap"],
                    As_chaine=round(As_chaine, 2),
                    At_st=r["At_st"],
                    st_max=r.get("st_max", 40.0),
                    st_ok=r.get("st_ok", True),
                    mu_r=r["mu_r"],
                    vH=r["vH"], vFlex=r["vFlex"], vCis=r["vCis"],
                    vELS=r["vELS"], vFleche=r["vFleche"],
                    section=r["section"], alerte=r["alerte"],
                )
                res.poutres.append(rp)

        # ── Poteaux ───────────────────────────────────────────────────────────
        for barre in projet.barres:
            if barre.type_elem != "poteau" or barre.niveau != niv:
                continue

            b_c = barre.b if barre.b > 0 else 0.25
            h_c = barre.h if barre.h > 0 else 0.25

            # Nu = charges reportées sur le nœud supérieur
            idx_nj = index_noeud(barre.nj, projet.noeuds)
            Nu = charges.get(idx_nj, 0.0)

            # Poids propre du poteau
            Nu += 1.35 * projet.materiaux.rhoba * b_c * h_c * barre.longueur

            # Demi-charges des poutres arrivant sur nj
            for pb in projet.barres:
                # Les poutres qui reposent sur ce poteau sont au niveau niv+1
                # (leur Z correspond au nj du poteau)
                if pb.type_elem != "poutre" or pb.niveau != niv + 1:
                    continue
                if pb.ni != barre.nj and pb.nj != barre.nj:
                    continue
                bj = pb.b if pb.b > 0 else 0.25
                hj = pb.h if pb.h > 0 else 0.50
                q_p = (charges_totales_poutre(pb, projet)
                       + 1.35 * projet.materiaux.rhoba * bj * hj
                       + 1.35 * pb.G_add + 1.5 * pb.Q_add)
                Nu += q_p * pb.longueur / 2

            lf = 0.7 * barre.longueur
            r = dim_poteau(Nu, b_c, h_c, lf, projet.materiaux)

            # Vérif amorces par rapport au poteau supérieur
            As_sup = _as_poteau_sup(barre, projet)
            alerte_am = As_sup > 0 and r["As"] > As_sup * 1.5

            rp = ResultatPoteau(
                barre_id=barre.id,
                etiq=f"C{barre.id}({barre.ni}-{barre.nj})",
                Nu=round(Nu, 1),
                As=r["As"], alpha=r["alpha"], lam=r["lam"],
                phi_am=r["phi_am"], ls_am=r["ls_am"],
                vL=r["vL"], vS=r["vS"],
                section=r["section"], alerte_am=alerte_am,
            )
            res.poteaux.append(rp)

            # Propagation vers le nœud inférieur
            idx_ni = index_noeud(barre.ni, projet.noeuds)
            if idx_ni > 0:
                charges[idx_ni] = charges.get(idx_ni, 0.0) + Nu

        res.niveaux_calcules.append(niv)

    # ── Fondations ────────────────────────────────────────────────────────────
    calc_toutes_semelles(projet, charges)
    res.semelles = projet.semelles
    res.charges_reportees = charges

    return res


# ── Utilitaires ───────────────────────────────────────────────────────────────
def _nu_poteau_about(barre: Barre, charges: Dict, projet: Projet) -> float:
    """Nu max du poteau d'about d'une poutre de rive."""
    nu_max = 0.0
    for pb in projet.barres:
        if pb.type_elem == "poteau":
            if pb.nj == barre.ni or pb.nj == barre.nj:
                idx = index_noeud(pb.ni, projet.noeuds)
                if idx > 0:
                    nu_max = max(nu_max, charges.get(idx, 0.0))
    return max(nu_max, 100.0)


def _as_poteau_sup(barre: Barre, projet: Projet) -> float:
    """As minimum du poteau au niveau supérieur."""
    for pb in projet.barres:
        if pb.type_elem == "poteau" and pb.niveau == barre.niveau + 1:
            if pb.ni == barre.nj:
                b = pb.b if pb.b > 0 else barre.b
                h = pb.h if pb.h > 0 else barre.h
                return 0.002 * b * 1000 * h * 1000 / 100
    return 0.0
