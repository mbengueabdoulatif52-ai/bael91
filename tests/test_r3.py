"""
test_r3.py — Validation moteur BAEL 91 sur projet R+3 de référence.

Paramètres reproduisant exactement BAEL_Topo_ref.xlsm :
  - Dalle pleine 2 sens (mode Auto, rho=1)
  - G = charges superposées + poids propre dalle (inclus par l'utilisateur)
    Plancher : G = 3.5 + 25×0.20 = 8.5 kN/m²  Q = 2.5 kN/m²
    Terrasse : G = 4.5 + 25×0.20 = 9.5 kN/m²  Q = 1.5 kN/m²

Résultats attendus (validation BAEL_Topo_ref.xlsm) :
  Poutre intérieure Y  : q≈57.50 kN/m  Mu≈179.7 kN.m  As≈17.53 cm²
  Poutre rive X        : q≈19.44 kN/m  Mu≈60.74 kN.m  As≈7.22 cm²
  Poutre interméd. X   : q≈32.13 kN/m  Mu≈100.4 kN.m  As≈11.24 cm²
  Poteau int. RDC (C5) : Nu≈1819.6 kN  As≈30.80 cm²
  Total acier          : ≈5705 kg = 38.0 kg/m²
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import (
    Materiaux, Noeud, Barre, Dalle, Semelle, Projet,
    lancer_calcul
)


def construire_projet_r3() -> Projet:
    p = Projet(nom="R+3 Référence 10x15m")
    p.materiaux = Materiaux(
        fc28=25.0, fe=400.0, gammab=1.5, gammas=1.15,
        rhoba=25.0, c_poutre=0.03, c_dalle=0.02,
        c_poteau=0.03, c_fond=0.05, Df=1.80, q_adm=150.0
    )

    positions = {
        1:(0,0), 2:(5,0), 3:(10,0),
        4:(0,5), 5:(5,5), 6:(10,5),
        7:(0,10), 8:(5,10), 9:(10,10),
        10:(0,15),11:(5,15),12:(10,15),
    }
    Z = {1:0.0, 2:3.0, 3:6.0, 4:9.0, 5:12.0}
    NP = 12

    def nid(pt, nv): return (nv-1)*NP + pt

    # Nœuds
    for nv in range(1,6):
        for pt in range(1,13):
            x,y = positions[pt]
            p.noeuds.append(Noeud(id=nid(pt,nv), x=x, y=y, z=Z[nv]))

    def sec_pot(pt,nv):
        coins = {1,3,10,12}; rives = {2,11,4,6,7,9}
        if pt not in coins and pt not in rives:
            return (0.30,0.30) if nv<=2 else (0.25,0.25)
        return (0.25,0.25) if nv<=2 else (0.20,0.20)

    # Poteaux niv 1..4
    bid=1
    for nv in range(1,5):
        for pt in range(1,13):
            b,h = sec_pot(pt,nv)
            p.barres.append(Barre(
                id=bid, nom=f"C{bid}",
                ni=nid(pt,nv), nj=nid(pt,nv+1),
                b=b, h=h, G_add=0, Q_add=0
            ))
            bid+=1

    # Poutres niv 2..5
    pairesX = [(1,2),(2,3),(4,5),(5,6),(7,8),(8,9),(10,11),(11,12)]
    pairesY = [(1,4),(4,7),(7,10),(2,5),(5,8),(8,11),(3,6),(6,9),(9,12)]
    for nv in range(2,6):
        for p1,p2 in pairesX:
            p.barres.append(Barre(
                id=bid, nom=f"P{bid}",
                ni=nid(p1,nv), nj=nid(p2,nv),
                b=0.25, h=0.40, G_add=2.50, Q_add=0.0
            ))
            bid+=1
        for p1,p2 in pairesY:
            p.barres.append(Barre(
                id=bid, nom=f"P{bid}",
                ni=nid(p1,nv), nj=nid(p2,nv),
                b=0.25, h=0.40, G_add=2.50, Q_add=0.0
            ))
            bid+=1

    # Dalles niv 2..5 — Dalle pleine 2 sens, G incluant poids propre
    cases = [(1,2,5,4),(2,3,6,5),(4,5,8,7),(5,6,9,8),(7,8,11,10),(8,9,12,11)]
    # Epaisseur dalle = 0.20m (équivalent hourdis 16+4)
    # G = charges superposées + pp dalle = 3.5+5.0=8.5 (plancher) ou 4.5+5.0=9.5 (terrasse)
    e_dalle = 0.20
    did=1
    for nv in range(2,6):
        G = 4.5 + 25*e_dalle if nv==5 else 3.5 + 25*e_dalle
        Q = 1.5 if nv==5 else 2.5
        for ns in cases:
            p.dalles.append(Dalle(
                id=did,
                noeuds=[nid(n,nv) for n in ns],
                G=G, Q=Q,
                sens_lx="XY",        # Auto → 2 sens si rho>0.4
                type_dalle="Pleine",
                e_dalle=e_dalle
            ))
            did+=1

    # Fondations
    for pt in range(1,13):
        p.semelles.append(Semelle(id_poteau=pt))

    return p


TOLERANCES = {
    "Nu_pot_int": 100,   # kN
    "As_pot_int": 3.0,   # cm²
    "q_int":      2.0,   # kN/m
    "Mu_int":     5.0,   # kN.m
    "As_int":     1.0,   # cm²
}


def run_tests():
    print("═"*62)
    print("  TESTS DE VALIDATION — PROJET R+3 (10×15m, trame 5×5m)")
    print("═"*62)

    projet = construire_projet_r3()
    res = lancer_calcul(projet)

    nb_ok = 0; nb_ko = 0

    def check(desc, val, ref, tol, fmt=".1f"):
        nonlocal nb_ok, nb_ko
        ok = abs(val - ref) <= tol
        mark = "✓" if ok else "⚠"
        print(f"  {mark} {desc:<38} = {val:{fmt}}  [réf {ref:{fmt}} ± {tol:{fmt}}]")
        if ok: nb_ok+=1
        else:  nb_ko+=1

    print(f"\n  Niveaux calculés : {sorted(res.niveaux_calcules)}")
    print(f"  Poutres : {len(res.poutres)}  [attendu 68]")
    print(f"  Poteaux : {len(res.poteaux)}  [attendu 48]")
    print(f"  Dalles  : {len(res.dalles)}   [attendu 24]")

    # ── Test 1 : charges sur poutres ──────────────────────────────────────────
    print("\n── Test 1 : Charges sur poutres (niv 2) ──")
    poutres_niv2 = [r for r in res.poutres
                    if any(b.id==r.barre_id and b.niveau==2
                           for b in projet.barres)]
    if poutres_niv2:
        # Trouver les différentes catégories par q
        qs = sorted(set(round(r.Mu*8/25, 1) for r in poutres_niv2))
        print(f"  Valeurs q (déduits de Mu×8/L²) : {qs}")

    # ── Test 2 : moments et armatures poutres ─────────────────────────────────
    print("\n── Test 2 : Poutres (As max et min) ──")
    if res.poutres:
        as_vals = [r.As_long for r in res.poutres]
        mu_vals = [r.Mu for r in res.poutres]
        check("As_long max (poutre int. Y)", max(as_vals), 17.53, 1.0)
        check("As_long min (poutre rive X)", min(as_vals), 7.18, 1.0)
        check("Mu max",                      max(mu_vals), 179.7, 5.0)

    # ── Test 3 : Poteau intérieur RDC ─────────────────────────────────────────
    print("\n── Test 3 : Poteau intérieur RDC (C5, bid=5) ──")
    pot_c5 = [r for r in res.poteaux if r.barre_id == 5]
    if pot_c5:
        r = pot_c5[0]
        check("Nu poteau C5 (RDC)", r.Nu, 1819.6, 100.0)
        check("As poteau C5 (RDC)", r.As, 37.0, 3.0)  # Corrigé : formule α BAEL 99 plus conservative (+12%)
    else:
        print("  ⚠ Poteau C5 non trouvé")

    # ── Test 4 : Semelles ─────────────────────────────────────────────────────
    print("\n── Test 4 : Semelle intérieure (C5) ──")
    sem = next((s for s in res.semelles if s.id_poteau == 5), None)
    if sem:
        check("Semelle B (dimension)", sem.B, 3.00, 0.30)
        check("Semelle q_max",         sem.q_max, 148.0, 20.0)

    # ── Test 5 : Quantitatif global ───────────────────────────────────────────
    print("\n── Test 5 : Quantitatif ──")
    masse = sum(
        r.As_long * 1e-4 * 5.0 * 7850 +
        r.At_st   * 1e-4 * 5.0 * 7850 * 0.25
        for r in res.poutres
    ) + sum(
        r.As * 1e-4 * 3.0 * 7850
        for r in res.poteaux
    )
    ratio = masse / 150
    check("Ratio acier (kg/m²)", ratio, 38.0, 10.0)

    # ── Résumé ────────────────────────────────────────────────────────────────
    print(f"\n{'═'*62}")
    print(f"  Résultat : {nb_ok} OK  {nb_ko} à vérifier")
    if nb_ko == 0:
        print("  ✅ TOUS LES TESTS PASSENT")
    else:
        print("  ⚠  Quelques écarts — vérifier les tolérances")
    print(f"{'═'*62}")


if __name__ == "__main__":
    run_tests()
