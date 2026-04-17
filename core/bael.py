"""
bael.py — Dimensionnement BAEL 91 révisé 99
v2 corrections :
  1. coeffs_bael() : table complète BAEL annexe E3 + interpolation linéaire
  2. dim_poteau()  : formule α exacte BAEL 99 (λ≤50 et λ>50)
  3. dim_poutre()  : As_min corrigé, espacement cadres st_max, flèche indicative
"""
import math
from .declarations import Materiaux, Dalle, ResultatDalle


# ── Catalogue hourdis ─────────────────────────────────────────────────────────
CATALOGUE_HOURDIS = [
    ("12+4", 0.16, 4.0),
    ("16+4", 0.20, 5.5),
    ("20+4", 0.24, 7.0),
    ("25+4", 0.29, 9.0),
]
ENTRAXE_NERV = 0.60
B_NERV       = 0.12


def choisir_hourdis(lx: float) -> tuple:
    for typ, h, lx_max in CATALOGUE_HOURDIS:
        if lx <= lx_max:
            return typ, h
    return "HORS CATALOGUE", 0.29


# ── Coefficients BAEL 91 Annexe E3 — TABLE COMPLÈTE avec interpolation ────────
# Valeurs officielles pour dalle simplement appuyée sur 4 côtés, ρ = lx/ly
# Source : BAEL 91 révisé 99, Annexe E3, tableau E.3.1
_TABLE_BAEL = [
    # (rho,  mux,    muy)
    (0.40,  0.1250, 0.0000),
    (0.45,  0.1180, 0.0000),
    (0.50,  0.1000, 0.0125),
    (0.55,  0.0930, 0.0175),
    (0.60,  0.0850, 0.0240),
    (0.65,  0.0790, 0.0290),
    (0.70,  0.0720, 0.0340),
    (0.75,  0.0660, 0.0390),
    (0.80,  0.0610, 0.0420),
    (0.85,  0.0560, 0.0460),
    (0.90,  0.0500, 0.0500),
    (0.95,  0.0460, 0.0530),
    (1.00,  0.0425, 0.0575),
]


def coeffs_bael(rho: float) -> tuple:
    """
    Retourne (mux, muy) par interpolation linéaire sur la table officielle BAEL.
    Pour rho ≤ 0.40 : dalle 1 sens (muy=0).
    Pour rho > 1.00  : extrapolation conservatrice.
    """
    if rho <= 0.40:
        return 0.125, 0.0

    # Interpolation linéaire
    for i in range(len(_TABLE_BAEL) - 1):
        r0, mx0, my0 = _TABLE_BAEL[i]
        r1, mx1, my1 = _TABLE_BAEL[i + 1]
        if r0 <= rho <= r1:
            t = (rho - r0) / (r1 - r0)
            return mx0 + t * (mx1 - mx0), my0 + t * (my1 - my0)

    # rho > 1.0 : retourner la dernière valeur
    return _TABLE_BAEL[-1][1], _TABLE_BAEL[-1][2]


# ── Dalle hourdis ─────────────────────────────────────────────────────────────
def dim_hourdis(lx, G, Q, mat: Materiaux) -> ResultatDalle:
    """
    Dimensionnement hourdis.
    G inclut le poids propre (saisi par l'utilisateur).
    qu = 1.35×G + 1.5×Q sans ajout automatique de rhoba×h.
    """
    typ, h_H = choisir_hourdis(lx)
    qu = 1.35 * G + 1.5 * Q
    qs = G + Q
    q_ELU = qu * ENTRAXE_NERV
    q_ELS = qs * ENTRAXE_NERV
    Mu    = q_ELU * lx**2 / 8
    Ms    = q_ELS * lx**2 / 8

    d_mm  = (h_H - mat.c_dalle) * 1000
    b_mm  = ENTRAXE_NERV * 1000
    bn_mm = B_NERV * 1000

    if d_mm <= 0:
        return ResultatDalle(0,"Hourdis",typ,h_H,Mu,0,0,0,"ERREUR d≤0","-",True)

    Mu_Nmm = Mu * 1e6
    mu_r   = min(max(Mu_Nmm / (b_mm * d_mm**2 * mat.fbu), 0.0), 0.392)
    z_mm   = d_mm * (1 - 0.4 * math.sqrt(max(1 - 2*mu_r, 0)))
    As_nerv = Mu_Nmm / (z_mm * mat.fsu) / 100 if z_mm > 0 else 0

    # As_min BAEL : max(0.23×bn×d×ftj/fe, 0.001×bn×h) [cm²]
    As_min1 = 0.23 * bn_mm * d_mm * mat.ftj / mat.fe / 100
    As_min2 = 0.001 * bn_mm * h_H * 1000 / 100
    As_nerv = max(As_nerv, As_min1, As_min2)

    As_rep = max(0.2 * As_nerv, 0.5)

    h_min = lx / 16
    vH = (f"{typ} OK (h={h_H*100:.0f}cm)" if h_H >= h_min
          else f"{typ} REVOIR h_min={h_min*100:.0f}cm")

    sig  = Ms * 1e6 / (0.348 * b_mm * d_mm**2)
    vELS = (f"ELS:OK sig={sig:.1f}MPa" if sig <= mat.sigmaBc
            else f"ELS:REVOIR sig={sig:.1f}/{mat.sigmaBc:.1f}")

    return ResultatDalle(
        dalle_id=0, type_dalle="Hourdis", typH=typ, h_out=h_H,
        Mu_x=Mu, Mu_y=0.0, As_nerv=As_nerv, As_rep=As_rep,
        vH=vH, vELS=vELS, alerte=("REVOIR" in vH or "REVOIR" in vELS)
    )


# ── Dalle pleine ──────────────────────────────────────────────────────────────
def dim_dalle_pleine(Mux, Muy, e, mat: Materiaux) -> tuple:
    d_mm = (e - mat.c_dalle) * 1000
    if d_mm <= 0:
        return 0.0, 0.0, "ERREUR"

    def calc_as(Mu_kNm):
        if Mu_kNm <= 0: return 0.0
        Mu_Nmm = Mu_kNm * 1e6
        mu = min(max(Mu_Nmm / (d_mm**2 * mat.fbu), 0.0), 0.392)
        z  = d_mm * (1 - 0.4 * math.sqrt(max(1 - 2*mu, 0)))
        As = Mu_Nmm / (z * mat.fsu) / 100 if z > 0 else 0
        As_min1 = 0.23 * d_mm * mat.ftj / mat.fe / 100
        As_min2 = 0.001 * e * 1000 * d_mm / 100
        return max(As, As_min1, As_min2)

    Asx = calc_as(Mux)
    Asy = calc_as(Muy)
    sig  = Mux * 1e6 / (0.348 * d_mm**2) if d_mm > 0 else 0
    vELS = (f"ELS:OK sig={sig:.1f}MPa" if sig <= mat.sigmaBc
            else f"ELS:REVOIR sig={sig:.1f}/{mat.sigmaBc:.1f}")
    return Asx, Asy, vELS


def dim_dalle(dalle: Dalle, mat: Materiaux) -> ResultatDalle:
    if dalle.type_dalle == "Pleine":
        e = dalle.e_dalle if dalle.e_dalle > 0 else 0.15
        mux, muy = coeffs_bael(dalle.rho)
        qu   = 1.35 * dalle.G + 1.5 * dalle.Q
        Mu_x = mux * qu * dalle.lx**2
        Mu_y = (muy * qu * dalle.lx**2) if dalle.rho > 0.4 else 0.0
        Asx, Asy, vELS = dim_dalle_pleine(Mu_x, Mu_y, e, mat)
        h_min = dalle.lx / 35
        typH  = f"Pleine e={e*100:.0f}cm"
        vH    = (f"{typH} OK" if e >= h_min
                 else f"{typH} REVOIR e_min={h_min*100:.0f}cm")
        r = ResultatDalle(
            dalle_id=dalle.id, type_dalle="Pleine", typH=typH, h_out=e,
            Mu_x=Mu_x, Mu_y=Mu_y, As_nerv=Asx, As_rep=Asy,
            vH=vH, vELS=vELS,
            alerte=("REVOIR" in vH or "REVOIR" in vELS)
        )
    else:
        r = dim_hourdis(dalle.lx, dalle.G, dalle.Q, mat)
        r.dalle_id = dalle.id
    return r


# ── Poutre ─────────────────────────────────────────────────────────────────────
def dim_poutre(Mu, Tu, Ms, b, h, L, mat: Materiaux, M_appui=0.0) -> dict:
    """
    Dimensionnement poutre BAEL 91.
    Corrections v2 :
    - As_min = max(0.23×b×d×ftj/fe, 0.001×b×h)
    - Espacement cadres : st_max = min(0.9×d, 0.40m) + vérification
    - Flèche : indicative (sur section brute), h≥L/16 = critère principal
    """
    d     = h - mat.c_poutre
    d_mm  = d * 1000
    b_mm  = b * 1000

    # ── Vérif géométrique h ≥ L/16 (critère principal BAEL) ──────────────────
    h_min = L / 16
    vH = (f"h/L:OK(1/{L/h:.0f})" if h >= h_min
          else f"REVOIR h_min={h_min*100:.0f}cm")

    # ── Flexion ELU ───────────────────────────────────────────────────────────
    As_long = 0.0; mu_r = 0.0; vFlex = ""
    if Mu > 0 and d_mm > 0:
        Mu_Nmm = Mu * 1e6
        mu_r   = Mu_Nmm / (b_mm * d_mm**2 * mat.fbu)
        if mu_r > 0.392:
            vFlex = "REVOIR mu>0.392"
        else:
            mu_r  = max(mu_r, 0.0)
            z_mm  = d_mm * (1 - 0.4 * math.sqrt(max(1 - 2*mu_r, 0)))
            As_long = Mu_Nmm / (z_mm * mat.fsu) / 100 if z_mm > 0 else 0
            # As_min : max(0.23×b×d×ftj/fe, 0.001×b×h)  — correction v2
            As_min1 = 0.23 * b_mm * d_mm * mat.ftj / mat.fe / 100
            As_min2 = 0.001 * b_mm * h * 1000 / 100
            As_long = max(As_long, As_min1, As_min2)
            vFlex   = "OK"

    # ── Chapeau ───────────────────────────────────────────────────────────────
    As_chap = 0.0
    if M_appui > 0.01 and d_mm > 0:
        Ma_Nmm = M_appui * 1e6
        mu_a   = min(max(Ma_Nmm / (b_mm * d_mm**2 * mat.fbu), 0.0), 0.392)
        z_a    = d_mm * (1 - 0.4 * math.sqrt(max(1 - 2*mu_a, 0)))
        As_chap = Ma_Nmm / (z_a * mat.fsu) / 100 if z_a > 0 else 0

    # ── Cisaillement ELU ──────────────────────────────────────────────────────
    At_st = 0.0; st_max = 0.40; st_ok = True; vCis = ""
    if Tu > 0 and b_mm > 0 and d_mm > 0:
        tau_u   = Tu * 1000 / (b_mm * d_mm)        # MPa
        tau_lim = min(0.2 * mat.fc28 / mat.gammab, 5.0)
        if tau_u > tau_lim:
            vCis  = f"REVOIR tau={tau_u:.2f}>{tau_lim:.2f}MPa"
        else:
            # At/st en cm²/m
            At_st   = max(Tu * 1000 / (d_mm * mat.fsu * 0.9) * 10,
                          0.4 * b_mm / mat.fe * 100)
            # Espacement maximal — correction v2 : st_max = min(0.9×d, 40cm)
            st_max  = min(0.9 * d * 100, 40.0)      # cm
            # Espacement réel déduit de At_st (cm²/m) avec HA8 (0.503 cm²) :
            phi_cad = 8 if b < 0.30 else 10          # mm cadre courant
            As_cad  = math.pi * (phi_cad/20)**2      # cm² par barre
            st_reel_cm = (2 * As_cad / At_st) * 100  # cm (2 branches)
            st_ok   = st_reel_cm <= st_max
            vCis    = (f"OK  HA{phi_cad} st={st_reel_cm:.0f}cm≤{st_max:.0f}cm"
                       if st_ok
                       else f"REVOIR st={st_reel_cm:.0f}cm>{st_max:.0f}cm")

    # ── ELS sigma_bc ──────────────────────────────────────────────────────────
    vELS = ""
    if Ms > 0 and d_mm > 0:
        sig_bc = Ms * 1e6 / (0.348 * b_mm * d_mm**2)
        vELS   = (f"sig={sig_bc:.1f}MPa OK" if sig_bc <= mat.sigmaBc
                  else f"REVOIR sig={sig_bc:.1f}>{mat.sigmaBc:.1f}MPa")

    # ── Flèche — indicative sur section brute (critère h≥L/16 prioritaire) ────
    vFleche = ""
    if L > 0 and As_long > 0 and d > 0:
        I_brute = b * h**3 / 12           # m4
        f_mm    = (5/384) * (Ms * 1e3) * L**3 / (mat.Ec * 1e3 * I_brute) * 1e3
        f_lim   = max(L * 1000 / 500, 10.0)
        if f_mm <= f_lim:
            vFleche = f"f≈{f_mm:.1f}/{f_lim:.0f}mm (ind.)"
        else:
            vFleche = f"REVOIR f≈{f_mm:.1f}>{f_lim:.0f}mm (ind.)"

    alerte = any("REVOIR" in v for v in [vH, vFlex, vCis, vELS, vFleche])

    return {
        "As_long": round(As_long, 2),
        "As_chap": round(As_chap, 2),
        "At_st":   round(At_st,  2),
        "st_max":  round(st_max, 1),
        "st_ok":   st_ok,
        "mu_r":    round(mu_r,   4),
        "vH":      vH,
        "vFlex":   vFlex,
        "vCis":    vCis,
        "vELS":    vELS,
        "vFleche": vFleche,
        "alerte":  alerte,
        "section": f"{b*100:.0f}x{h*100:.0f}cm",
    }


# ── Poteau ─────────────────────────────────────────────────────────────────────
def dim_poteau(Nu, b, h, lf, mat: Materiaux) -> dict:
    """
    Dimensionnement poteau centré BAEL 91 révisé 99.
    Correction v2 :
    - λ ≤ 50 : α = 0.85 / (1 + 0.2×(λ/35)²)   [BAEL 99 formule exacte]
    - λ > 50 : α = 0.6 × (50/λ)²               [méthode forfaitaire BAEL]
    - λ > 70 : REVOIR (hors domaine méthode forfaitaire)
    """
    Br_m2 = (b - 0.02) * (h - 0.02) if b > 0.02 and h > 0.02 else b * h

    # Élancement
    i_min = min(b, h) / math.sqrt(12)
    lam   = lf / i_min if i_min > 0 else 0

    # Coefficient de flambement — correction v2
    if lam <= 50:
        alpha = 0.85 / (1 + 0.2 * (lam / 35)**2)
    elif lam <= 70:
        alpha = 0.6 * (50 / lam)**2
    else:
        alpha = 0.6 * (50 / lam)**2   # extrapolation conservatrice
        alpha = max(alpha, 0.20)

    vL = (f"lam={lam:.0f} OK" if lam <= 70
          else f"lam={lam:.0f} REVOIR (>70, hors méthode forfaitaire)")

    # Section acier
    Nu_N    = Nu * 1000
    fbc     = 0.85 * mat.fc28 / mat.gammab
    Br_mm2  = Br_m2 * 1e6
    As_num  = Nu_N / alpha - fbc * Br_mm2
    denom   = mat.fsu - fbc
    As      = As_num / denom / 100 if denom > 0 and As_num > 0 else 0.0

    # As_min : max(0.2% de Br, 4HA8)
    As_min1 = 0.002 * b * 1000 * h * 1000 / 100
    As_min2 = 4 * math.pi * (8/20)**2
    As      = max(As, As_min1, As_min2)

    # As_max BAEL Art. A.8.1 : 5% de la section béton (zone courante)
    As_max = 0.05 * b * 1000 * h * 1000 / 100   # cm²
    alerte_as_max = As > As_max

    # Vérif section
    sigma_b = Nu_N / (alpha * Br_mm2) if Br_mm2 > 0 else 0
    vS_base = ("Sect:OK" if sigma_b <= fbc * 1.05
               else f"REVOIR sig={sigma_b:.1f}>{fbc:.1f}MPa")
    if alerte_as_max:
        vS = (f"REVOIR As={As:.1f}cm²>As_max={As_max:.1f}cm² "
              f"(5% section) — augmenter b ou h")
    else:
        vS = vS_base

    # Amorces
    phi_am = 8
    As_p   = As / 4
    for phi in [20, 16, 12]:
        if As_p > math.pi * (phi/20)**2:
            phi_am = phi; break
    ls_am = 40 * phi_am / 1000

    return {
        "As":           round(As, 2),
        "As_max":       round(As_max, 2),
        "alerte_as_max": alerte_as_max,
        "alpha":        round(alpha, 3),
        "lam":          round(lam, 1),
        "phi_am":       phi_am,
        "ls_am":        round(ls_am, 3),
        "vL":           vL,
        "vS":           vS,
        "alerte":       ("REVOIR" in vL or "REVOIR" in vS),
        "section":      f"{b*100:.0f}x{h*100:.0f}cm",
    }
