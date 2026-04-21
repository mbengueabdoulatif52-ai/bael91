"""
topologie.py
Équivalent de 3_Mod_Topologie.bas
Calcul de la géométrie : niveaux, types de barres, géométrie des dalles
"""
import math
from typing import List, Tuple
from .declarations import Projet, Noeud, Barre, Dalle


# ── Niveaux ───────────────────────────────────────────────────────────────────
def calc_niveaux(projet: Projet) -> None:
    """
    Identifie les niveaux distincts depuis les cotes Z des nœuds.
    Trie les niveaux par Z croissant et numérote à partir de 1.
    """
    z_vals = sorted(set(round(n.z, 3) for n in projet.noeuds))
    projet.niveaux = z_vals
    projet.nb_niveaux = len(z_vals)

    z_to_niv = {z: i + 1 for i, z in enumerate(z_vals)}
    for n in projet.noeuds:
        n.niveau = z_to_niv[round(n.z, 3)]


def niveau_depuis_z(z: float, niveaux: List[float]) -> int:
    """Retourne le numéro de niveau correspondant à une cote Z."""
    for i, zn in enumerate(niveaux):
        if abs(z - zn) < 0.001:
            return i + 1
    return 0


# ── Barres ────────────────────────────────────────────────────────────────────
def calc_barres(projet: Projet) -> None:
    """
    Calcule pour chaque barre :
    - la longueur
    - le type (poutre ou poteau)
    - le niveau
    """
    noeud_map = {n.id: n for n in projet.noeuds}

    for bar in projet.barres:
        ni = noeud_map.get(bar.ni)
        nj = noeud_map.get(bar.nj)
        if ni is None or nj is None:
            continue

        dx = nj.x - ni.x
        dy = nj.y - ni.y
        dz = nj.z - ni.z
        bar.longueur = math.sqrt(dx**2 + dy**2 + dz**2)

        # Type : poteau si vertical, poutre si horizontal
        long_horiz = math.sqrt(dx**2 + dy**2)
        if long_horiz < 0.001:
            bar.type_elem = "poteau"
            bar.niveau = niveau_depuis_z(ni.z, projet.niveaux)
        else:
            bar.type_elem = "poutre"
            bar.niveau = niveau_depuis_z(nj.z, projet.niveaux)


# ── Dalles ────────────────────────────────────────────────────────────────────
def calc_geom_dalle(dalle: Dalle, noeud_map: dict) -> None:
    """
    Calcule lx, ly, rho et le mode de travail d'une dalle.

    Règles :
    - Hourdis : sens imposé (X ou Y), rho ignoré pour la distribution
    - Dalle pleine : rho = lx/ly, mode 1 sens si rho ≤ 0.4, 2 sens sinon
    - Poids propre NON calculé ici — inclus par l'utilisateur dans G
    """
    if not dalle.noeuds:
        return

    coords = []
    for nid in dalle.noeuds:
        n = noeud_map.get(nid)
        if n:
            coords.append((n.x, n.y, n.z))

    if not coords:
        return

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]

    dim_x = max(xs) - min(xs)
    dim_y = max(ys) - min(ys)

    if dim_x <= 0 or dim_y <= 0:
        return

    # Sens de portée
    s = dalle.sens_lx.upper().replace("SENS ", "").strip()

    if "X" in s and "Y" not in s:
        # Sens X imposé : nervures portent dans X
        dalle.lx = dim_x
        dalle.ly = dim_y
    elif "Y" in s and "X" not in s:
        # Sens Y imposé : nervures portent dans Y
        dalle.lx = dim_y
        dalle.ly = dim_x
    else:
        # Auto ou XY : lx = plus petite dimension (BAEL)
        dalle.lx = min(dim_x, dim_y)
        dalle.ly = max(dim_x, dim_y)

    if dalle.ly > 0:
        dalle.rho = dalle.lx / dalle.ly
    else:
        dalle.rho = 1.0

    # Mode de travail
    if dalle.type_dalle == "Hourdis":
        dalle.mode = "1 sens (Hourdis)"
    elif dalle.rho <= 0.4:
        dalle.mode = "1 sens (Pleine)"
    else:
        dalle.mode = "2 sens (Pleine)"

    # Niveau depuis Z
    z_mean = sum(zs) / len(zs)
    dalle.niveau = niveau_depuis_z(z_mean, [])  # sera mis à jour dans calc_dalles


def calc_dalles(projet: Projet) -> None:
    """Calcule la géométrie de toutes les dalles et leur niveau."""
    noeud_map = {n.id: n for n in projet.noeuds}

    for d in projet.dalles:
        calc_geom_dalle(d, noeud_map)
        # Niveau depuis la cote Z moyenne des nœuds
        zs = [noeud_map[nid].z for nid in d.noeuds if nid in noeud_map]
        if zs:
            z_mean = sum(zs) / len(zs)
            d.niveau = niveau_depuis_z(round(z_mean, 3), projet.niveaux)


# ── Utilitaires géométrie ─────────────────────────────────────────────────────
def get_coords_noeud(nid: int, noeud_map: dict) -> Tuple[float, float, float]:
    """Retourne (x, y, z) d'un nœud."""
    n = noeud_map.get(nid)
    if n:
        return n.x, n.y, n.z
    return 0.0, 0.0, 0.0


def index_noeud(nid: int, noeuds: List[Noeud]) -> int:
    """Retourne l'index (1-based) d'un nœud par son ID."""
    for i, n in enumerate(noeuds, 1):
        if n.id == nid:
            return i
    return 0


def bord_est_appuye(ni: int, nj: int, barres: List[Barre]) -> bool:
    """
    Vérifie si le côté (ni, nj) d'une dalle est appuyé sur une poutre.
    """
    for bar in barres:
        if bar.type_elem == "poutre":
            if (bar.ni == ni and bar.nj == nj) or \
               (bar.ni == nj and bar.nj == ni):
                return True
    return False


def compter_bords_libres(dalle: Dalle, barres: List[Barre]) -> int:
    """
    Compte le nombre de bords libres (sans poutre d'appui) d'une dalle.
    Un bord libre → dalle en porte-à-faux.
    """
    nb = len(dalle.noeuds)
    libres = 0
    for i in range(nb):
        ni = dalle.noeuds[i]
        nj = dalle.noeuds[(i + 1) % nb]
        if not bord_est_appuye(ni, nj, barres):
            libres += 1
    return libres


def est_poutre_de_rive(barre: Barre, dalles: List[Dalle]) -> bool:
    """
    Une poutre est de rive si elle borde une seule dalle
    (elle est en façade du bâtiment).
    """
    count = 0
    for d in dalles:
        nb = len(d.noeuds)
        for i in range(nb):
            ni = d.noeuds[i]
            nj = d.noeuds[(i + 1) % nb]
            if (ni == barre.ni and nj == barre.nj) or \
               (ni == barre.nj and nj == barre.ni):
                count += 1
    return count == 1


# ── Validation topologie ──────────────────────────────────────────────────────
def valider_topologie(projet: Projet) -> List[str]:
    """
    Vérifie la cohérence de la topologie.
    Retourne une liste de messages d'erreur (vide = OK).
    """
    erreurs = []
    noeud_ids = {n.id for n in projet.noeuds}

    for bar in projet.barres:
        if bar.ni not in noeud_ids:
            erreurs.append(f"Barre {bar.id} : nœud Ni={bar.ni} inexistant")
        if bar.nj not in noeud_ids:
            erreurs.append(f"Barre {bar.id} : nœud Nj={bar.nj} inexistant")

    for d in projet.dalles:
        for nid in d.noeuds:
            if nid not in noeud_ids:
                erreurs.append(f"Dalle {d.id} : nœud {nid} inexistant")
        if len(d.noeuds) < 3:
            erreurs.append(f"Dalle {d.id} : moins de 3 nœuds")
        if d.type_dalle == "Hourdis":
            s = d.sens_lx.upper()
            if "X" in s and "Y" in s:
                erreurs.append(
                    f"Dalle {d.id} : Hourdis avec sens XY impossible — "
                    f"imposer Sens X ou Sens Y"
                )
        if d.type_dalle == "Pleine":
            if d.e_dalle <= 0:
                erreurs.append(
                    f"Dalle {d.id} : dalle pleine sans épaisseur"
                )
            elif d.e_dalle < 0.08:
                erreurs.append(
                    f"Dalle {d.id} : e={d.e_dalle*100:.0f}cm < 8cm (min BAEL)"
                )

    return erreurs
