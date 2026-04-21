"""
trois_moments.py
Équivalent de 6_Mod_3Moments.bas
Méthode des trois moments (Clapeyron) — une barre = une entité indépendante.
Les appuis intermédiaires sont les noeuds colinéaires entre ni et nj
qui ont un poteau (NoeudEstAppui).
"""
import math
from typing import List
from .declarations import Barre, Travee, Projet


def calc_poutre_contin(
    barre: Barre,
    q_dalle: float,
    projet: Projet,
) -> List[Travee]:
    """
    Calcule les efforts d'une poutre (continue ou isostatique).
    q_dalle : charge des dalles seule (kN/m), sans pp ni G_add.
    Le pp et G_add sont ajoutés ici.
    Retourne la liste des travées.
    """
    noeud_map = {n.id: n for n in projet.noeuds}

    b_p = barre.b if barre.b > 0 else 0.25
    h_p = barre.h if barre.h > 0 else 0.50

    # Charge totale par mètre linéaire (ELU)
    q_pp  = 1.35 * projet.materiaux.rhoba * b_p * h_p
    q_add = 1.35 * barre.G_add + 1.5 * barre.Q_add
    q_tot = q_dalle + q_pp + q_add

    # Appuis intermédiaires colinéaires entre ni et nj
    appuis_int = _get_appuis_intermediaires(barre, projet, noeud_map)
    nb_appuis = len(appuis_int)

    # Construire la liste des nœuds de gauche à droite
    noeuds_ligne = [barre.ni] + appuis_int + [barre.nj]
    nb_travees = len(noeuds_ligne) - 1

    # Longueurs et charges de chaque travée
    Ls = []
    for i in range(nb_travees):
        na = noeuds_ligne[i]
        nb2 = noeuds_ligne[i + 1]
        n1 = noeud_map.get(na)
        n2 = noeud_map.get(nb2)
        if n1 and n2:
            L = math.sqrt((n2.x-n1.x)**2 + (n2.y-n1.y)**2 + (n2.z-n1.z)**2)
        else:
            L = barre.longueur / nb_travees
        Ls.append(max(L, 0.001))

    # Même charge sur toutes les travées (répartition uniforme)
    qs = [q_tot] * nb_travees

    # Conditions aux limites
    ni_libre = not _noeud_est_appui(barre.ni, projet)
    nj_libre = not _noeud_est_appui(barre.nj, projet)

    # Cas 1 : poutre isostatique (pas d'appui intermédiaire)
    if nb_appuis == 0:
        return [_calc_isostatique(
            noeuds_ligne[0], noeuds_ligne[1],
            Ls[0], qs[0], ni_libre, nj_libre
        )]

    # Cas 2 : poutre continue — résoudre par Clapeyron
    M = _clapeyron(Ls, qs, ni_libre, nj_libre)

    # Construire les travées
    result = []
    for i in range(nb_travees):
        Mi = M[i]
        Mj = M[i + 1]
        tv = _calc_efforts_travee(
            noeuds_ligne[i], noeuds_ligne[i + 1],
            Ls[i], qs[i], Mi, Mj
        )
        result.append(tv)

    return result


# ── Appuis intermédiaires ─────────────────────────────────────────────────────
def _get_appuis_intermediaires(
    barre: Barre,
    projet: Projet,
    noeud_map: dict,
) -> List[int]:
    """
    Retourne les IDs des noeuds colinéaires entre ni et nj
    qui ont un poteau (= appui), triés par position le long de la barre.
    """
    ni = noeud_map.get(barre.ni)
    nj = noeud_map.get(barre.nj)
    if not ni or not nj:
        return []

    dx = nj.x - ni.x
    dy = nj.y - ni.y
    dz = nj.z - ni.z
    L2 = dx**2 + dy**2 + dz**2
    if L2 < 1e-6:
        return []

    appuis = []
    for n in projet.noeuds:
        if n.id == barre.ni or n.id == barre.nj:
            continue
        # Vérifier colinéarité
        if not _est_colineaire(ni, nj, n):
            continue
        # Vérifier que c'est un appui (a un poteau)
        if not _noeud_est_appui(n.id, projet):
            continue
        # Calculer la position paramétrique t ∈ (0,1)
        t = ((n.x-ni.x)*dx + (n.y-ni.y)*dy + (n.z-ni.z)*dz) / L2
        if 0.001 < t < 0.999:
            appuis.append((t, n.id))

    appuis.sort(key=lambda x: x[0])
    return [nid for _, nid in appuis]


def _est_colineaire(n1, n2, nt, tol=0.05) -> bool:
    """Vérifie si nt est colinéaire avec n1-n2."""
    dx = n2.x - n1.x; dy = n2.y - n1.y; dz = n2.z - n1.z
    ex = nt.x - n1.x; ey = nt.y - n1.y; ez = nt.z - n1.z
    # Produit vectoriel
    cx = dy*ez - dz*ey
    cy = dz*ex - dx*ez
    cz = dx*ey - dy*ex
    dist2 = cx**2 + cy**2 + cz**2
    L2 = dx**2 + dy**2 + dz**2
    return L2 > 1e-6 and dist2 / L2 < tol**2


def _noeud_est_appui(nid: int, projet: Projet) -> bool:
    """Un nœud est un appui s'il a un poteau qui lui est attaché."""
    for b in projet.barres:
        if b.type_elem == "poteau":
            if b.ni == nid or b.nj == nid:
                return True
    return False


# ── Calcul isostatique ────────────────────────────────────────────────────────
def _calc_isostatique(
    ni: int, nj: int,
    L: float, q: float,
    ni_libre: bool, nj_libre: bool,
) -> Travee:
    if ni_libre and not nj_libre:
        # Console ancrée à droite
        return Travee(ni=ni, nj=nj, L=L, q=q,
                      Mu_span=0, Mu_appui_i=0, Mu_appui_j=-q*L**2/2,
                      Tu_i=0, Tu_j=q*L)
    elif nj_libre and not ni_libre:
        # Console ancrée à gauche
        return Travee(ni=ni, nj=nj, L=L, q=q,
                      Mu_span=0, Mu_appui_i=-q*L**2/2, Mu_appui_j=0,
                      Tu_i=q*L, Tu_j=0)
    else:
        # Bi-appuyée standard
        return Travee(ni=ni, nj=nj, L=L, q=q,
                      Mu_span=q*L**2/8,
                      Mu_appui_i=0, Mu_appui_j=0,
                      Tu_i=q*L/2, Tu_j=q*L/2)


# ── Méthode des trois moments ─────────────────────────────────────────────────
def _clapeyron(
    Ls: List[float],
    qs: List[float],
    ni_libre: bool = False,
    nj_libre: bool = False,
) -> List[float]:
    """
    Résout le système de Clapeyron.
    M[0]=M[n]=0 (appuis simples ou bouts libres).
    Retourne M[0..n] (moments sur appuis).
    """
    n = len(Ls)
    M = [0.0] * (n + 1)

    if nj_libre and n >= 1:
        M[n - 1] = -qs[n-1] * Ls[n-1]**2 / 2
    if ni_libre and n >= 1:
        M[1] = -qs[0] * Ls[0]**2 / 2

    debut = 2 if not ni_libre else 3
    fin   = n - 1 if not nj_libre else n - 2

    if fin < debut:
        return M

    nb_inc = fin - debut + 1
    # Matrice augmentée [A|b]
    mat = [[0.0] * (nb_inc + 1) for _ in range(nb_inc)]

    for idx in range(nb_inc):
        k = debut + idx  # indice appui interne (1-based dans M)
        Lk  = Ls[k - 2]   # travée k-1
        Lk1 = Ls[k - 1]   # travée k
        qk  = qs[k - 2]
        qk1 = qs[k - 1]

        mat[idx][idx] = 2 * (Lk + Lk1)
        if idx > 0:
            mat[idx][idx - 1] = Lk
        if idx < nb_inc - 1:
            mat[idx][idx + 1] = Lk1

        rhs = -(qk * Lk**3 + qk1 * Lk1**3) / 4
        if idx == 0:
            rhs -= M[k - 1] * Lk
        if idx == nb_inc - 1:
            rhs -= M[k + 1] * Lk1
        mat[idx][nb_inc] = rhs

    sol = _gauss(mat, nb_inc)
    for idx, val in enumerate(sol):
        M[debut + idx] = val

    return M


def _gauss(mat: List[List[float]], n: int) -> List[float]:
    """Élimination de Gauss avec pivot partiel."""
    for k in range(n):
        # Pivot
        max_row = max(range(k, n), key=lambda i: abs(mat[i][k]))
        mat[k], mat[max_row] = mat[max_row], mat[k]
        pivot = mat[k][k]
        if abs(pivot) < 1e-10:
            pivot = 1e-10
        for i in range(k + 1, n):
            f = mat[i][k] / pivot
            for j in range(k, n + 1):
                mat[i][j] -= f * mat[k][j]

    sol = [0.0] * n
    for i in range(n - 1, -1, -1):
        sol[i] = mat[i][n]
        for j in range(i + 1, n):
            sol[i] -= mat[i][j] * sol[j]
        if abs(mat[i][i]) > 1e-10:
            sol[i] /= mat[i][i]

    return sol


def _calc_efforts_travee(
    ni: int, nj: int,
    L: float, q: float,
    Mi: float, Mj: float,
) -> Travee:
    """Calcule les efforts dans une travée à partir des moments sur appuis."""
    # Réactions (équilibre)
    Ri = (q * L**2 / 2 - Mj + Mi) / L
    Rj = q * L - Ri
    Ti = abs(Ri)
    Tj = abs(Rj)

    # Position et valeur du moment max en travée
    x_max = Ri / q if q > 1e-6 else L / 2
    x_max = max(0.0, min(x_max, L))
    Mu_span = Mi + Ri * x_max - q * x_max**2 / 2
    Mu_span = max(Mu_span, 0.0)

    return Travee(
        ni=ni, nj=nj, L=L, q=q,
        Mu_span=Mu_span,
        Mu_appui_i=Mi, Mu_appui_j=Mj,
        Tu_i=Ti, Tu_j=Tj,
    )
