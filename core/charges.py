"""
charges.py
Équivalent de 5_Mod_Charges.bas
Distribution des charges dalles → poutres (BAEL 91)

RÈGLE FONDAMENTALE :
  qu = 1.35 × G + 1.5 × Q
  Le poids propre de la dalle est inclus par l'utilisateur dans G.
  Le programme ne rajoute PAS rhoba × h.
"""
import math
from typing import List
from .declarations import Projet, Barre, Dalle, Materiaux


# ── Calcul qu ─────────────────────────────────────────────────────────────────
def calc_qu(dalle: Dalle) -> float:
    """
    Charge ELU surfacique (kN/m²).
    Poids propre inclus dans G par l'utilisateur.
    """
    return 1.35 * dalle.G + 1.5 * dalle.Q


def calc_qs(dalle: Dalle) -> float:
    """Charge service surfacique (kN/m²)."""
    return dalle.G + dalle.Q


# ── Distribution vers une poutre ──────────────────────────────────────────────
def charge_lineaire_poutre(
    dalle: Dalle,
    barre: Barre,
    noeud_map: dict,
    barres: List[Barre],
) -> float:
    """
    Charge linéaire (kN/m) apportée par la dalle sur la poutre.

    Logique BAEL :
    - Hourdis : 1 seul sens pur, rho ignoré
        · Poutre perpendiculaire aux nervures → q = qu × ly/2
        · Poutre parallèle aux nervures       → q = 0
    - Dalle pleine :
        · rho ≤ 0.4 (1 sens) : idem hourdis
        · rho > 0.4 (2 sens) :
            - Sens principal (côté ly)    : q = qu × lx/2 × (1 - rho²/3)
            - Sens secondaire (côté lx)   : q = qu × lx² / (6 × ly)
    """
    if barre.type_elem != "poutre":
        return 0.0

    qu = calc_qu(dalle)
    lx = dalle.lx
    ly = dalle.ly
    rho = dalle.rho

    # Trouver si la poutre est un bord de cette dalle
    ni_cote, nj_cote = _trouver_cote(dalle, barre)
    if ni_cote is None:
        return 0.0

    # Vérifier que le bord est appuyé
    if not _bord_est_appuye(ni_cote, nj_cote, barres):
        return 0.0

    # Nombre de bords libres (porte-à-faux)
    nb_libres = _compter_bords_libres(dalle, barres)

    # Orientation de ce côté
    n1 = noeud_map.get(ni_cote)
    n2 = noeud_map.get(nj_cote)
    if n1 is None or n2 is None:
        return 0.0

    dx = abs(n2.x - n1.x)
    dy = abs(n2.y - n1.y)

    # sensLx = True si ce côté est parallèle à lx (direction principale des nervures)
    # Identique au VBA : InStr(sens,"X")>0 And InStr(sens,"Y")=0 → sensLx = (dx>dy)
    s = dalle.sens_lx.upper().replace("SENS ", "").strip()
    len_cote = math.sqrt(dx**2 + dy**2)
    if "X" in s and "Y" not in s:
        # Nervures en X → côté horizontal (dx>dy) = parallèle aux nervures = sensLx
        sens_lx = dx > dy
    elif "Y" in s and "X" not in s:
        # Nervures en Y → côté vertical (dy>dx) = parallèle aux nervures = sensLx
        sens_lx = dy > dx
    else:
        # Auto / XY : comparer longueur du côté à lx et ly
        diff_lx = abs(len_cote - lx)
        diff_ly = abs(len_cote - ly)
        if abs(diff_lx - diff_ly) < 0.001:
            # Côtés de même longueur → utiliser orientation dx/dy comme le VBA
            sens_lx = (dx >= dy)
        else:
            sens_lx = diff_lx <= diff_ly

    # Distribution selon type
    if dalle.type_dalle == "Hourdis":
        # Hourdis : 1 sens pur
        if nb_libres >= 1:
            # Porte-à-faux : tout sur l'appui (côté perpendiculaire aux nervures)
            return qu * lx if not sens_lx else 0.0
        else:
            return 0.0 if sens_lx else qu * ly / 2

    else:
        # Dalle pleine
        if nb_libres >= 1:
            return qu * lx
        elif rho <= 0.4:
            return 0.0 if sens_lx else qu * ly / 2
        else:
            if sens_lx:
                return qu * lx**2 / (6 * ly)
            else:
                return qu * lx / 2 * (1 - rho**2 / 3)


def charges_totales_poutre(
    barre: Barre,
    projet: Projet,
) -> float:
    """Somme des charges linéaires de toutes les dalles sur une poutre."""
    noeud_map = {n.id: n for n in projet.noeuds}
    total = 0.0
    for d in projet.dalles:
        total += charge_lineaire_poutre(d, barre, noeud_map, projet.barres)
    return total


# ── Chaînage de rive BAEL Art. 8.8 ───────────────────────────────────────────
def calc_chainage_rive(
    barre: Barre,
    Nu_poteau: float,
) -> tuple:
    """
    Calcule l'effort et l'armature de chaînage pour une poutre de rive.
    T ≥ max(1% × Nu_poteau, 20 kN)
    Retourne (T_kN, As_cm2, description)
    """
    T = max(0.01 * Nu_poteau, 20.0)
    mat_fe = 400.0  # MPa — utilisera gMat.fe en pratique
    As = T * 1000 / (mat_fe / 1.15) / 100  # cm²
    As = max(As, 1.0)  # minimum 1 cm²
    vCh = f"T={T:.1f} kN  As={As:.2f} cm²"
    return T, As, vCh


# ── Utilitaires internes ──────────────────────────────────────────────────────
def _trouver_cote(dalle: Dalle, barre: Barre):
    """Retourne (ni, nj) du côté de la dalle qui correspond à la poutre."""
    nb = len(dalle.noeuds)
    for i in range(nb):
        ni = dalle.noeuds[i]
        nj = dalle.noeuds[(i + 1) % nb]
        if (ni == barre.ni and nj == barre.nj) or \
           (ni == barre.nj and nj == barre.ni):
            return ni, nj
    return None, None


def _bord_est_appuye(ni: int, nj: int, barres: List[Barre]) -> bool:
    for bar in barres:
        if bar.type_elem == "poutre":
            if (bar.ni == ni and bar.nj == nj) or \
               (bar.ni == nj and bar.nj == ni):
                return True
    return False


def _compter_bords_libres(dalle: Dalle, barres: List[Barre]) -> int:
    nb = len(dalle.noeuds)
    libres = 0
    for i in range(nb):
        ni = dalle.noeuds[i]
        nj = dalle.noeuds[(i + 1) % nb]
        if not _bord_est_appuye(ni, nj, barres):
            libres += 1
    return libres
