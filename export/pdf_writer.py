"""
export/pdf_writer.py — Rapport PDF BAEL 91
v2.1 : police DejaVu Unicode (résout l'erreur caractères hors plage Helvetica)
"""
import io
import os

# Chemins polices DejaVu (disponibles sur Windows, Linux, macOS)
# Dossier fonts/ embarqué dans le projet (prioritaire)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONTS_DIR = os.path.join(_BASE_DIR, "fonts")

_FONT_PATHS = {
    "regular": [
        os.path.join(_FONTS_DIR, "DejaVuSans.ttf"),          # local (Cloud-ready)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",   # Linux système
        "C:/Windows/Fonts/DejaVuSans.ttf",                   # Windows
        "/Library/Fonts/DejaVuSans.ttf",                     # macOS
    ],
    "bold": [
        os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        "/Library/Fonts/DejaVuSans-Bold.ttf",
    ],
    "italic": [
        os.path.join(_FONTS_DIR, "DejaVuSans-Oblique.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "C:/Windows/Fonts/DejaVuSans-Oblique.ttf",
        "/Library/Fonts/DejaVuSans-Oblique.ttf",
    ],
}


def _find_font(style: str) -> str | None:
    """Cherche une police DejaVu sur le système."""
    for path in _FONT_PATHS.get(style, []):
        if os.path.exists(path):
            return path
    return None


def exporter_pdf(res, projet) -> bytes:
    try:
        from fpdf import FPDF
        r = _find_font("regular")
        b = _find_font("bold")
        i = _find_font("italic")
        if r and b:
            return _pdf_dejavu(res, projet, r, b, i or r)
        else:
            # Fallback : Helvetica avec nettoyage des caractères
            return _pdf_helvetica(res, projet)
    except ImportError:
        return _pdf_texte(res, projet)


# ── PDF avec police DejaVu (Unicode complet) ───────────────────────────────────
def _pdf_dejavu(res, projet, font_r, font_b, font_i) -> bytes:
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("DejaVu", "B", 10)
            self.set_fill_color(31, 56, 100)
            self.set_text_color(255, 255, 255)
            self.cell(0, 8, f"  RAPPORT BAEL 91 \u2014 {projet.nom}",
                      new_x="LMARGIN", new_y="NEXT", fill=True)
            self.set_text_color(0, 0, 0)
            self.set_font("DejaVu", "", 7)
            self.cell(0, 4,
                      "  Outil de dimensionnement b\u00e9ton arm\u00e9 "
                      "\u2014 BAEL 91 r\u00e9vis\u00e9 99",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        def footer(self):
            self.set_y(-10)
            self.set_font("DejaVu", "I", 7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5,
                      f"Page {self.page_no()} \u2014 R\u00e9sultats indicatifs, "
                      "\u00e0 v\u00e9rifier par un ing\u00e9nieur responsable",
                      align="C")

    pdf = PDF()
    pdf.add_font("DejaVu",  "",  font_r)
    pdf.add_font("DejaVu",  "B", font_b)
    pdf.add_font("DejaVu",  "I", font_i)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    mat = projet.materiaux

    # ── Hypothèses ────────────────────────────────────────────────────────────
    _titre(pdf, "HYPOTH\u00c8SES DE CALCUL")
    _sous_titre(pdf, "Mat\u00e9riaux")
    _t2(pdf, [
        ("B\u00e9ton",
         f"fc28 = {mat.fc28:.0f} MPa  |  \u03b3b = {mat.gammab:.2f}  "
         f"|  fbu = {mat.fbu:.2f} MPa  |  Ec = {mat.Ec:.0f} MPa"),
        ("Acier",
         f"fe = {mat.fe:.0f} MPa  |  \u03b3s = {mat.gammas:.2f}  "
         f"|  fsu = {mat.fsu:.2f} MPa"),
        ("Enrobages",
         f"Poutres {mat.c_poutre*100:.0f} cm  |  Dalles {mat.c_dalle*100:.0f} cm  "
         f"|  Poteaux {mat.c_poteau*100:.0f} cm  |  Fondations {mat.c_fond*100:.0f} cm"),
        ("Classe exposition", mat.classe_exposition),
        ("Sol",
         f"q_adm = {mat.q_adm:.0f} kN/m\u00b2  |  Df = {mat.Df:.2f} m"),
    ])

    # Note G poids propre (encadrée)
    pdf.set_font("DejaVu", "I", 8)
    pdf.set_fill_color(255, 235, 156)
    pdf.set_draw_color(200, 150, 0)
    pdf.set_line_width(0.5)
    pdf.multi_cell(
        0, 5,
        "\u26a0  HYPOTH\u00c8SE IMPORTANTE : Les charges permanentes G "
        "saisies pour les dalles INCLUENT le poids propre de la dalle "
        "(\u03c1ba \u00d7 \u00e9paisseur). Le moteur de calcul n'ajoute "
        "aucun poids propre automatique.\n"
        "Exemple hourdis 16+4 : G_saisi = G_superpos\u00e9 + 25\u00d70.20 "
        "= G_superpos\u00e9 + 5.0 kN/m\u00b2",
        border=1, fill=True
    )
    pdf.set_line_width(0.2)
    pdf.ln(2)

    _sous_titre(pdf, "Normes et m\u00e9thodes appliqu\u00e9es")
    normes = [
        "- Dimensionnement selon BAEL 91 r\u00e9vis\u00e9 99",
        "- Dalles : coefficients \u03bcx/\u03bcy selon Annexe E3 BAEL "
          "(interpolation lin\u00e9aire sur 13 valeurs)",
        "- Poutres continues : m\u00e9thode des trois moments (Clapeyron)",
        "- Poteaux : flambement BAEL 99 : "
          "\u03bb\u226450 \u2192 \u03b1=0.85/(1+0.2(\u03bb/35)\u00b2)  |  "
          "\u03bb>50 \u2192 \u03b1=0.6\u00d7(50/\u03bb)\u00b2",
        "- Fl\u00e8che : indicative sur section brute \u2014 "
          "crit\u00e8re principal : h \u2265 L/16",
        "- Cisaillement semelles : \u03c4_lim = 0.07\u00d7fc28/\u03b3b",
        "- Descente de charges : du niveau le plus haut vers le bas",
    ]
    pdf.set_font("DejaVu", "", 8)
    for n in normes:
        pdf.cell(0, 5, n, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Résumé quantités ──────────────────────────────────────────────────────
    _titre(pdf, "R\u00c9SUM\u00c9 DES QUANTIT\u00c9S")
    nb_ap = sum(1 for r in res.poutres if r.alerte)
    nb_ac = sum(1 for r in res.poteaux if r.alerte_am)
    nb_as = sum(1 for s in res.semelles if s.alerte)
    _t2(pdf, [
        ("Poutres calcul\u00e9es",  str(len(res.poutres))),
        ("Poteaux calcul\u00e9s",   str(len(res.poteaux))),
        ("Dalles calcul\u00e9es",   str(len(res.dalles))),
        ("Semelles calcul\u00e9es", str(len(res.semelles))),
        ("Alertes poutres",  f"{nb_ap} {'!' if nb_ap else 'OK'}"),
        ("Alertes poteaux",  f"{nb_ac} {'!' if nb_ac else 'OK'}"),
        ("Alertes semelles", f"{nb_as} {'!' if nb_as else 'OK'}"),
    ])

    # ── Dalles ────────────────────────────────────────────────────────────────
    if res.dalles:
        pdf.add_page()
        _titre(pdf, "DALLES")
        _tab(pdf,
             ["ID", "Type", "h/e", "Mu_x kN.m", "Mu_y kN.m",
              "As_nerv cm2", "As_rep cm2", "ELU", "ELS"],
             [[str(r.dalle_id), r.type_dalle, r.typH,
               f"{r.Mu_x:.2f}", f"{r.Mu_y:.2f}" if r.Mu_y > 0 else "-",
               f"{r.As_nerv:.2f}", f"{r.As_rep:.2f}",
               "OK" if "REVOIR" not in r.vH else "!",
               "OK" if "REVOIR" not in r.vELS else "!"]
              for r in res.dalles],
             [10, 14, 16, 16, 16, 16, 16, 10, 10])

    # ── Poutres par niveau ────────────────────────────────────────────────────
    niveaux_p = sorted(
        {b.niveau for b in projet.barres if b.type_elem == "poutre"},
        reverse=True)
    for niv in niveaux_p:
        bids = {b.id for b in projet.barres
                if b.type_elem == "poutre" and b.niveau == niv}
        poutres_niv = [r for r in res.poutres if r.barre_id in bids]
        if not poutres_niv:
            continue
        pdf.add_page()
        _titre(pdf, f"POUTRES \u2014 NIVEAU {niv}")
        _tab(pdf,
             ["El\u00e9ment", "Section", "Mu kN.m", "Tu kN",
              "As_l cm2", "As_ch cm2", "At/st cm2/m",
              "st_max cm", "ELU", "Fl\u00e8che"],
             [[r.etiq, r.section,
               f"{r.Mu:.1f}", f"{r.Tu:.1f}",
               f"{r.As_long:.2f}",
               f"{r.As_chap:.2f}" if r.As_chap else "-",
               f"{r.At_st:.2f}", f"{r.st_max:.0f}",
               "OK" if "REVOIR" not in r.vFlex else "!",
               (r.vFleche[:18] if r.vFleche else "-")]
              for r in poutres_niv],
             [22, 14, 14, 10, 12, 12, 14, 12, 8, 18])

    # ── Poteaux par niveau ────────────────────────────────────────────────────
    niveaux_c = sorted(
        {b.niveau for b in projet.barres if b.type_elem == "poteau"},
        reverse=True)
    for niv in niveaux_c:
        bids = {b.id for b in projet.barres
                if b.type_elem == "poteau" and b.niveau == niv}
        pots_niv = [r for r in res.poteaux if r.barre_id in bids]
        if not pots_niv:
            continue
        if niv == max(niveaux_c):
            pdf.add_page()
            _titre(pdf, "POTEAUX")
        _sous_titre(pdf, f"Niveau {niv}")
        _tab(pdf,
             ["El\u00e9ment", "Section", "Nu kN", "As cm2",
              "\u03b1", "\u03bb", "V\u00e9rif"],
             [[r.etiq, r.section,
               f"{r.Nu:.0f}", f"{r.As:.2f}",
               f"{r.alpha:.3f}", f"{r.lam:.0f}",
               "OK" if "REVOIR" not in r.vL else "!"]
              for r in pots_niv],
             [26, 14, 14, 12, 12, 10, 18])

    # Dictionnaire nom poteau (tous niveaux)
    noms_pots_pdf = {b.id: b.nom for b in projet.barres
                     if b.type_elem == "poteau"}
    def _np_pdf(bid): return noms_pots_pdf.get(bid, f"C{bid}") if bid else "—"

    # ── Fondations ────────────────────────────────────────────────────────────
    if res.semelles:
        pdf.add_page()
        _titre(pdf, "FONDATIONS \u2014 SEMELLES ISOL\u00c9ES")
        _tab(pdf,
             ["Poteau", "Type", "B\u00d7L m", "e cm",
              "Nu kN", "q_max kN/m2", "Asx cm2/m", "Statut"],
             [[_np_pdf(s.id_poteau),
               "Centr\u00e9e" if s.ex == 0 and s.ey == 0 else "Excentr.",
               f"{s.B:.2f}\u00d7{s.L_sem:.2f}",
               f"{s.e_sem*100:.0f}",
               f"{s.Nu_ser:.0f}",
               f"{s.q_max:.0f}",
               f"{s.Asx:.2f}",
               "OK" if not s.alerte else "!"]
              for s in res.semelles],
             [16, 14, 18, 10, 14, 18, 16, 12])

        # Longrines
        long_sems = [s for s in res.semelles
                     if s.long_X_As > 0 or s.long_Y_As > 0]
        if long_sems:
            _sous_titre(pdf, "Longrines de redressement")
            pdf.set_font("DejaVu", "I", 8)
            pdf.multi_cell(0, 5,
                "M_redressement = Nu_ser x excentricite  |  "
                "As chap. = 50% As long. (chapeau sur appuis)  |  "
                "NOTE : G dalles INCLUT le poids propre de la dalle.",
                new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            rows_l = []
            for s in long_sems:
                if s.long_X_As > 0:
                    rows_l.append([
                        _np_pdf(s.id_poteau),
                        "X",
                        f"vers C{s.long_X_vers}",
                        f"{s.b_long_X*100:.0f}x{s.h_long_X*100:.0f}cm",
                        f"{s.ex:.3f}",
                        f"{s.long_X_Mu:.1f}",
                        f"{s.long_X_As:.2f}",
                        f"{s.long_X_As*0.5:.2f}",
                    ])
                if s.long_Y_As > 0:
                    rows_l.append([
                        _np_pdf(s.id_poteau),
                        "Y",
                        f"vers C{s.long_Y_vers}",
                        f"{s.b_long_Y*100:.0f}x{s.h_long_Y*100:.0f}cm",
                        f"{s.ey:.3f}",
                        f"{s.long_Y_Mu:.1f}",
                        f"{s.long_Y_As:.2f}",
                        f"{s.long_Y_As*0.5:.2f}",
                    ])
            _tab(pdf,
                 ["Poteau", "Dir.", "Vers", "Section",
                  "e (m)", "M kN.m", "As long. cm2", "As chap. cm2"],
                 rows_l, [14, 10, 16, 18, 14, 18, 22, 22])
        else:
            # Avertissement semelles excentriques sans longrine
            exc_sans = [s for s in res.semelles
                        if (s.ex > 0 or s.ey > 0)
                        and s.long_X_vers == 0 and s.long_Y_vers == 0]
            if exc_sans:
                ids = ", ".join(_np_pdf(s.id_poteau) for s in exc_sans)
                pdf.set_font("DejaVu", "I", 8)
                pdf.set_fill_color(255, 220, 180)
                pdf.multi_cell(0, 5,
                    f"! Semelles excentriques ({ids}) sans longrine definie. "
                    "Renseigner Long_X_vers ou Long_Y_vers dans le fichier de saisie.",
                    border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read()


# ── PDF Helvetica avec nettoyage caractères (fallback) ────────────────────────
def _pdf_helvetica(res, projet) -> bytes:
    """Fallback si DejaVu non disponible : remplace les caractères spéciaux."""
    from fpdf import FPDF

    def clean(s: str) -> str:
        return (s.replace("\u2014", "-").replace("\u2013", "-")
                 .replace("\u00d7", "x").replace("\u2265", ">=")
                 .replace("\u2264", "<=").replace("\u03b1", "alpha")
                 .replace("\u03bb", "lambda").replace("\u03bc", "mu")
                 .replace("\u03c1", "rho").replace("\u03b3", "gamma")
                 .replace("\u00e9", "e").replace("\u00e8", "e")
                 .replace("\u00ea", "e").replace("\u00e0", "a")
                 .replace("\u00e2", "a").replace("\u00ee", "i")
                 .replace("\u00f4", "o").replace("\u00fb", "u")
                 .replace("\u00c9", "E").replace("\u00c8", "E")
                 .replace("\u00c0", "A").replace("\u00ce", "I")
                 .replace("\u00d4", "O").replace("\u00bb", ">")
                 .replace("\u00ab", "<").replace("\u00b2", "2")
                 .replace("\u00b0", "deg").replace("\u26a0", "!")
                 .replace("\u00b3", "3").replace("\u00b7", "."))

    # Patcher les fonctions pour nettoyer
    import types

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 10)
            self.set_fill_color(31, 56, 100)
            self.set_text_color(255, 255, 255)
            self.cell(0, 8, clean(f"  RAPPORT BAEL 91 - {projet.nom}"),
                      new_x="LMARGIN", new_y="NEXT", fill=True)
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-10)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5,
                      clean(f"Page {self.page_no()} - Resultats indicatifs"),
                      align="C")

    # Wrapper qui nettoie tous les textes
    orig_cell = FPDF.cell
    orig_multi = FPDF.multi_cell

    def cell_clean(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (clean(args[0]),) + args[1:]
        if 'txt' in kwargs:
            kwargs['txt'] = clean(kwargs['txt'])
        if 'text' in kwargs:
            kwargs['text'] = clean(kwargs['text'])
        return orig_cell(self, *args, **kwargs)

    def multi_clean(self, w, h, txt="", **kwargs):
        return orig_multi(self, w, h, clean(str(txt)), **kwargs)

    PDF.cell = cell_clean
    PDF.multi_cell = multi_clean

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, clean(f"RAPPORT BAEL 91 - {projet.nom}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    mat = projet.materiaux
    pdf.cell(0, 6,
             clean(f"fc28={mat.fc28:.0f}MPa  fe={mat.fe:.0f}MPa  "
                   f"q_adm={mat.q_adm:.0f}kN/m2  "
                   f"Classe: {mat.classe_exposition}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5,
                   clean("IMPORTANT : G dalles INCLUT le poids propre "
                         "(rho x epaisseur). Pas d'ajout automatique."))
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, clean("POTEAUX RDC"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    for r in res.poteaux:
        b = next((b for b in projet.barres if b.id == r.barre_id), None)
        if b and b.niveau == 1:
            pdf.cell(0, 5,
                     f"  {r.etiq:20s}  Nu={r.Nu:7.0f}kN  "
                     f"As={r.As:5.2f}cm2  alpha={r.alpha:.3f}  lam={r.lam:.0f}",
                     new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read()


# ── Fallback texte ─────────────────────────────────────────────────────────────
def _pdf_texte(res, projet) -> bytes:
    mat = projet.materiaux
    lines = [
        f"RAPPORT BAEL 91 - {projet.nom}", "=" * 60,
        f"fc28={mat.fc28:.0f}MPa  fe={mat.fe:.0f}MPa  "
        f"q_adm={mat.q_adm:.0f}kN/m2",
        "NOTE : G dalles INCLUT le poids propre.", "",
        f"Poutres:{len(res.poutres)}  Poteaux:{len(res.poteaux)}  "
        f"Dalles:{len(res.dalles)}", "",
        "POTEAUX RDC :",
    ]
    for r in res.poteaux:
        b = next((b for b in projet.barres if b.id == r.barre_id), None)
        if b and b.niveau == 1:
            lines.append(f"  {r.etiq}  Nu={r.Nu:.0f}kN  As={r.As:.2f}cm2")
    return "\n".join(lines).encode("utf-8")


# ── Helpers mise en page ───────────────────────────────────────────────────────
def _titre(pdf, txt):
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_fill_color(31, 56, 100)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, f"  {txt}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _sous_titre(pdf, txt):
    pdf.set_font("DejaVu", "B", 9)
    pdf.set_fill_color(68, 114, 196)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, f"  {txt}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _t2(pdf, lignes):
    for lab, val in lignes:
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_fill_color(240, 244, 250)
        pdf.cell(55, 5, f"  {lab}", border=1, fill=True)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(0, 5, f"  {val}", border=1, fill=True,
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _tab(pdf, hdrs, rows, widths):
    pdf.set_font("DejaVu", "B", 7)
    pdf.set_fill_color(46, 117, 182)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(hdrs, widths):
        pdf.cell(w, 6, f" {h}", border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    for i, row in enumerate(rows):
        alerte = any(str(c).strip() in ("!", "REVOIR") for c in row)
        if alerte:
            pdf.set_fill_color(255, 220, 220)
        elif i % 2 == 0:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("DejaVu", "", 7)
        for val, w in zip(row, widths):
            pdf.cell(w, 5, f" {val}", border=1, fill=True)
        pdf.ln()
    pdf.ln(2)
