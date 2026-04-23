"""
fondations.py — Dimensionnement fondations BAEL 91
v2 : appel automatique de dim_longrine si ex>0 ou ey>0
"""
import math
from .declarations import Semelle, Materiaux


def dim_semelle_centree(s: Semelle, b_pot: float, h_pot: float,
                        mat: Materiaux) -> Semelle:
    q_adm = s.q_adm_loc if s.q_adm_loc > 0 else mat.q_adm
    Nu_ser = s.Nu_ser
    if Nu_ser <= 0:
        return s

    # Dimensions
    B = math.sqrt(Nu_ser * 1.10 / q_adm)
    B = _arr(B, 0.05)
    if B < b_pot + 0.10:
        B = _arr(b_pot + 0.10, 0.05)
    s.B = B; s.L_sem = B

    # Pression sol
    s.q_max = Nu_ser * 1.10 / (B * B)
    s.q_min = s.q_max

    # Hauteur par cisaillement (formule BAEL)
    d_deb   = (B - b_pot) / 2
    tau_lim = 0.07 * mat.fc28 / mat.gammab
    V       = s.q_max * d_deb
    d_u_min = V / (tau_lim * 1000)
    h_sem   = max(d_u_min + mat.c_fond, 0.20)
    s.e_sem = _arr(h_sem, 0.05)

    # Armatures
    d_u  = s.e_sem - mat.c_fond
    Mu_s = s.q_max * d_deb**2 / 2
    if Mu_s > 0 and d_u > 0:
        As      = Mu_s * 1e6 / (0.9 * d_u * 1000 * mat.fsu) / 100
        As_min  = 0.001 * s.e_sem * 1000
        s.Asx   = max(As, As_min)
        s.Asy   = s.Asx
    else:
        s.Asx = s.Asy = 0.5

    # Amorces — calculées dans calc_toutes_semelles depuis le ferraillage poteau

    s.alerte = (f"REVOIR q={s.q_max:.0f}>{q_adm:.0f}kN/m²"
                if s.q_max > q_adm * 1.01 else "")
    return s


def dim_semelle_excentrique(s: Semelle, b_pot: float, h_pot: float,
                             mat: Materiaux) -> Semelle:
    q_adm  = s.q_adm_loc if s.q_adm_loc > 0 else mat.q_adm
    Nu_ser = s.Nu_ser
    # Utiliser valeurs absolues pour le dimensionnement
    # Le signe est conservé dans s.ex et s.ey pour la visualisation
    ex, ey = abs(s.ex), abs(s.ey)
    if Nu_ser <= 0:
        return s

    # Prendre les valeurs absolues pour le dimensionnement
    ex_abs = abs(ex); ey_abs = abs(ey)

    B0 = math.sqrt(Nu_ser * 1.10 / q_adm)
    for _ in range(5):
        B  = _arr(B0, 0.05)
        ex_eff = min(ex_abs, B / 6) if ex_abs > 0 else 0
        ey_eff = min(ey_abs, B / 6) if ey_abs > 0 else 0
        q_m = Nu_ser / (B*B) * (1 + 6*ex_eff/B + 6*ey_eff/B)
        if q_m > q_adm:
            B0 = B0 * math.sqrt(q_m / q_adm)
        else:
            break

    s.B = _arr(B0, 0.05); s.L_sem = s.B
    d_deb   = (s.B - b_pot) / 2
    tau_lim = 0.07 * mat.fc28 / mat.gammab
    s.q_max = Nu_ser / (s.B*s.L_sem) * (1 + 6*min(ex_abs,s.B/6)/s.B
                                          + 6*min(ey_abs,s.L_sem/6)/s.L_sem)
    s.q_min = Nu_ser / (s.B*s.L_sem) * (1 - 6*min(ex_abs,s.B/6)/s.B
                                          - 6*min(ey_abs,s.L_sem/6)/s.L_sem)
    d_u_min  = s.q_max * d_deb / (tau_lim * 1000)
    s.e_sem  = _arr(max(d_u_min + mat.c_fond, 0.25), 0.05)

    d_u  = s.e_sem - mat.c_fond
    Mu_s = s.q_max * d_deb**2 / 2
    if Mu_s > 0 and d_u > 0:
        As     = Mu_s * 1e6 / (0.9 * d_u * 1000 * mat.fsu) / 100
        s.Asx  = max(As, 0.001 * s.e_sem * 1000)
        s.Asy  = s.Asx
    else:
        s.Asx = s.Asy = 0.5

    # Amorces — calculées dans calc_toutes_semelles depuis le ferraillage poteau
    s.alerte = (f"REVOIR q={s.q_max:.0f}>{q_adm:.0f}kN/m²"
                if s.q_max > q_adm * 1.01 else "")
    return s


def dim_longrine(Nu_ser: float, e_exc: float, L_long: float,
                 b_long: float, h_long: float, mat: Materiaux) -> dict:
    """Dimensionnement longrine de redressement. M_red = Nu_ser × e_exc."""
    M_red = Nu_ser * e_exc
    d_mm  = (h_long - mat.c_fond) * 1000
    b_mm  = b_long * 1000
    if d_mm <= 0 or M_red <= 0:
        return {"As_long": 0.0, "As_chap": 0.0, "vM": "M=0", "Mu": 0.0}

    Mu_Nmm = M_red * 1e6
    mu     = min(Mu_Nmm / (b_mm * d_mm**2 * mat.fbu), 0.392)
    z      = d_mm * (1 - 0.4 * math.sqrt(max(1 - 2*mu, 0)))
    As     = Mu_Nmm / (z * mat.fsu) / 100 if z > 0 else 0
    As_min = max(0.23 * b_mm * d_mm * mat.ftj / mat.fe / 100,
                 0.001 * b_mm * h_long * 1000 / 100)
    As     = max(As, As_min)
    vM     = f"M={M_red:.1f}kN.m  As={As:.2f}cm²"
    return {"As_long": round(As, 2), "As_chap": round(As*0.5, 2),
            "vM": vM, "Mu": M_red}


def calc_toutes_semelles(projet, charges_reportees: dict,
                        res_poteaux=None) -> None:
    """
    Dimensionne toutes les semelles.
    v3 : amorces calculées depuis le ferraillage réel du poteau niveau 1.
    """
    from .topologie import index_noeud
    poteaux_n1 = [b for b in projet.barres
                  if b.type_elem == "poteau" and b.niveau == 1]

    # Index As des poteaux niveau 1 depuis les résultats
    # res_poteaux : liste de ResultatPoteau
    as_poteaux_n1 = {}
    if res_poteaux:
        for rp in res_poteaux:
            b = next((b for b in poteaux_n1 if b.id == rp.barre_id), None)
            if b:
                as_poteaux_n1[b.id] = rp.As

    for sem in projet.semelles:
        pot = next((b for b in poteaux_n1 if b.id == sem.id_poteau), None)
        if pot is None:
            continue

        idx = index_noeud(pot.ni, projet.noeuds)
        Nu_ELU = charges_reportees.get(idx, 0.0) if idx else 0.0
        sem.Nu_ELU = Nu_ELU
        sem.Nu_ser = Nu_ELU / 1.35

        b_pot = pot.b if pot.b > 0 else 0.25
        h_pot = pot.h if pot.h > 0 else 0.25

        # Alerte 10 — valeur ex/ey invalide (doit être -1, 0 ou +1)
        if sem.ex not in (-1.0, 0.0, 1.0):
            if not hasattr(sem, 'alertes'): sem.alertes = []
            sem.alertes.append(
                f"❌ ex={sem.ex} invalide — saisir uniquement -1, 0 ou +1")
        if sem.ey not in (-1.0, 0.0, 1.0):
            if not hasattr(sem, 'alertes'): sem.alertes = []
            sem.alertes.append(
                f"❌ ey={sem.ey} invalide — saisir uniquement -1, 0 ou +1")

        if abs(sem.ex) == 0 and abs(sem.ey) == 0:
            dim_semelle_centree(sem, b_pot, h_pot, projet.materiaux)
            sem.ex_reel = 0.0
            sem.ey_reel = 0.0
        else:
            dim_semelle_excentrique(sem, b_pot, h_pot, projet.materiaux)
            # Convertir ex/ey en valeurs métriques réelles
            # Nouvelle convention : ex/ey ∈ {-1, 0, +1}
            #   → ex_reel = signe × (B/2 - b_pot/2)
            #   → poteau affleure exactement le bord de la semelle
            # Ancienne convention : ex/ey = valeur métrique directe
            #   → ex_reel = ex  (rétrocompatibilité)
            if sem.ex in (-1.0, 0.0, 1.0) and sem.ey in (-1.0, 0.0, 1.0):
                sem.ex_reel = sem.ex * (sem.B / 2 - b_pot / 2)
                sem.ey_reel = sem.ey * (sem.L_sem / 2 - h_pot / 2)
            else:
                # Ancien format métrique — utiliser directement
                sem.ex_reel = sem.ex
                sem.ey_reel = sem.ey

        # Amorces : ferraillage réel du poteau niveau 1
        As_pot = as_poteaux_n1.get(pot.id,
                 0.002 * b_pot*1000 * h_pot*1000 / 100)
        sem.phi_amorce, sem.nb_amorce = _choisir_amorces(As_pot, b_pot, h_pot)
        sem.ls_amorce = 40 * sem.phi_amorce / 1000

        # ── Longrines ─────────────────────────────────────────────────────────
        ids_poteaux = {b.id for b in projet.barres if b.type_elem == "poteau"}

        if abs(sem.ex) > 0 and sem.long_X_vers > 0:
            L_lX = _distance_poteaux(pot, sem.long_X_vers, projet)
            r = dim_longrine(sem.Nu_ser, abs(sem.ex_reel), L_lX,
                             sem.b_long_X, sem.h_long_X, projet.materiaux)
            sem.long_X_Mu = r["Mu"]
            sem.long_X_As = r["As_long"]
            sem.long_X_vM = r["vM"]

        if abs(sem.ey) > 0 and sem.long_Y_vers > 0:
            L_lY = _distance_poteaux(pot, sem.long_Y_vers, projet)
            r = dim_longrine(sem.Nu_ser, abs(sem.ey_reel), L_lY,
                             sem.b_long_Y, sem.h_long_Y, projet.materiaux)
            sem.long_Y_Mu = r["Mu"]
            sem.long_Y_As = r["As_long"]
            sem.long_Y_vM = r["vM"]

        # ── 9 ALERTES ─────────────────────────────────────────────────────────
        q_adm = sem.q_adm_loc if sem.q_adm_loc > 0 else projet.materiaux.q_adm
        # Initialiser depuis les alertes existantes (ex: alerte 10)
        alertes = list(getattr(sem, 'alertes', []))

        # --- GROUPE 1 : Géométrie ---
        # Alerte 6 — poteau déborde de la semelle
        if abs(sem.ex) > 0:
            debord_x = sem.B / 2 - b_pot / 2
            if abs(sem.ex_reel) > debord_x + 0.001:
                alertes.append(
                    f"❌ |ex_reel|={abs(sem.ex_reel):.3f}m > "
                    f"B/2-b/2={debord_x:.3f}m — poteau déborde de la semelle")
        if abs(sem.ey) > 0:
            debord_y = sem.L_sem / 2 - h_pot / 2
            if abs(sem.ey_reel) > debord_y + 0.001:
                alertes.append(
                    f"❌ |ey_reel|={abs(sem.ey_reel):.3f}m > "
                    f"L/2-h/2={debord_y:.3f}m — poteau déborde de la semelle")

        # --- GROUPE 2 : Sol ---
        # Alerte 1 — soulèvement
        if hasattr(sem, 'q_min') and sem.q_min is not None:
            if sem.q_min < -0.001:
                # Vérifier si des longrines sont présentes dans les directions excentriques
                long_X_ok = (abs(sem.ex) == 0 or sem.long_X_vers > 0)
                long_Y_ok = (abs(sem.ey) == 0 or sem.long_Y_vers > 0)
                longrines_ok = long_X_ok and long_Y_ok

                if longrines_ok:
                    # Soulèvement compensé par les longrines — avertissement seulement
                    alertes.append(
                        f"⚠ Soulèvement compensé par longrines "
                        f"(q_min={sem.q_min:.1f}kN/m²) "
                        f"— vérifier dimensionnement longrines")
                else:
                    # Soulèvement réel sans longrine — erreur bloquante
                    manquantes = []
                    if abs(sem.ex) > 0 and sem.long_X_vers <= 0:
                        manquantes.append("X")
                    if abs(sem.ey) > 0 and sem.long_Y_vers <= 0:
                        manquantes.append("Y")
                    dirs = "/".join(manquantes)
                    alertes.append(
                        f"❌ Soulèvement (q_min={sem.q_min:.1f}kN/m²<0) "
                        f"— ajouter longrine direction {dirs} "
                        f"ou réduire excentricité")
            elif abs(sem.q_min) < 0.001 and (abs(sem.ex)>0 or abs(sem.ey)>0):
                # Alerte 2 — limite soulèvement
                # Supprimer si convention -1/0/+1 car c'est le comportement attendu
                if sem.ex not in (-1.0, 0.0, 1.0) or sem.ey not in (-1.0, 0.0, 1.0):
                    alertes.append(
                        f"⚠ Semelle en limite de soulèvement (q_min≈0)")

        # Alerte 3 — pression sol dépassée
        if sem.q_max > q_adm * 1.01:
            alertes.append(
                f"❌ q_max={sem.q_max:.0f} > q_adm={q_adm:.0f}kN/m²")

        # --- GROUPE 3 : Longrines ---
        fc28  = projet.materiaux.fc28
        fbu   = 0.85 * fc28 / 1.5   # kN/cm²  ← attention unités
        fbu_MPa = 0.85 * fc28 / 1.5  # MPa

        for direc, b_l, h_l, As_l, Mu_l, vers in [
            ("X", sem.b_long_X, sem.h_long_X,
             sem.long_X_As, sem.long_X_Mu, sem.long_X_vers),
            ("Y", sem.b_long_Y, sem.h_long_Y,
             sem.long_Y_As, sem.long_Y_Mu, sem.long_Y_vers),
        ]:
            e_dir = sem.ex if direc == "X" else sem.ey
            if abs(e_dir) == 0:
                continue

            # Alerte 9 — poteau destination introuvable
            if vers > 0 and vers not in ids_poteaux:
                alertes.append(
                    f"⚠ Longrine {direc} : poteau destination C{vers} "
                    f"introuvable — vérifier l'ID dans l'Excel")
                continue

            # Alerte 8 — section non renseignée
            if b_l <= 0 or h_l <= 0:
                alertes.append(
                    f"⚠ Longrine {direc} : section non renseignée "
                    f"(b=0 ou h=0) — saisir b_l{direc} et h_l{direc} "
                    f"dans l'Excel")
                continue

            if Mu_l <= 0:
                continue

            c_env = projet.materiaux.c_poutre
            d_l   = h_l - c_env
            if d_l <= 0:
                continue

            # Alerte 4 — μ longrine > 0.392
            mu_l = Mu_l / (b_l*1000 * (d_l*1000)**2 * fbu_MPa / 1e6)
            if mu_l > 0.392:
                alertes.append(
                    f"❌ Longrine {direc} : μ={mu_l:.3f} > 0.392 "
                    f"— augmenter section "
                    f"({b_l*100:.0f}×{h_l*100:.0f}cm insuffisant)")

            # Alerte 5 — As longrine > As_max
            As_max_l = 0.05 * b_l*1000 * h_l*1000 / 100
            if As_l > As_max_l:
                alertes.append(
                    f"❌ Longrine {direc} : As={As_l:.2f} > "
                    f"As_max={As_max_l:.2f}cm² — augmenter section")

        sem.alertes = alertes
        # Rétrocompatibilité : sem.alerte = premier message ou vide
        sem.alerte = alertes[0] if alertes else ""


# ── Utilitaires ────────────────────────────────────────────────────────────────
def _arr(val: float, pas: float) -> float:
    return math.ceil(val / pas) * pas

def _choisir_amorces(As_poteau_cm2, b_pot, h_pot):
    """
    Choisit phi et nb_barres tels que nb × As_barre >= As_poteau.
    Les amorces = continuité des barres du poteau (même section totale).
    Gamme disponible à Dakar : HA8, HA10, HA12, HA14, HA16, HA20, HA25.
    On commence par 4 barres (barres d'angle) et on augmente si nécessaire.
    """
    gamme = [8, 10, 12, 14, 16, 20, 25]
    As_min = max(As_poteau_cm2,
                 0.002 * b_pot * 1000 * h_pot * 1000 / 100)

    for nb in [4, 6, 8]:
        for p in gamme:
            As_tot = nb * math.pi * (p / 20) ** 2
            if As_tot >= As_min:
                return p, nb

    return 25, 8  # fallback : 8HA25

def _distance_poteaux(pot_base, id_vers: int, projet) -> float:
    """Distance entre deux poteaux (longueur de la longrine)."""
    noeud_map = {n.id: n for n in projet.noeuds}
    pot_vers  = next((b for b in projet.barres
                      if b.id == id_vers and b.type_elem == "poteau"), None)
    if pot_vers is None:
        return 3.0
    n1 = noeud_map.get(pot_base.ni)
    n2 = noeud_map.get(pot_vers.ni)
    if n1 and n2:
        return math.sqrt((n2.x-n1.x)**2 + (n2.y-n1.y)**2)
    return 3.0
