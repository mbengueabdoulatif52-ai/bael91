"""
declarations.py — Types de données BAEL 91
v2 : ajout classe_exposition (Normal / Côtier)
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Materiaux:
    fc28:              float = 25.0
    gammab:            float = 1.50
    fe:                float = 400.0
    gammas:            float = 1.15
    rhoba:             float = 25.0
    # Enrobages — ajustés automatiquement selon classe_exposition
    c_poutre:          float = 0.03   # m
    c_dalle:           float = 0.02
    c_poteau:          float = 0.03
    c_fond:            float = 0.05
    Df:                float = 1.80
    q_adm:             float = 150.0
    # Classe d'exposition : "Normal" ou "Cotier"
    classe_exposition: str   = "Normal"

    def appliquer_classe(self):
        """Ajuste les enrobages selon la classe d'exposition."""
        if self.classe_exposition == "Cotier":
            self.c_poutre = 0.04
            self.c_dalle  = 0.03
            self.c_poteau = 0.04
            self.c_fond   = 0.06
        else:
            self.c_poutre = 0.03
            self.c_dalle  = 0.02
            self.c_poteau = 0.03
            self.c_fond   = 0.05

    @property
    def fbu(self)   -> float: return 0.85 * self.fc28 / self.gammab
    @property
    def fsu(self)   -> float: return self.fe / self.gammas
    @property
    def ftj(self)   -> float: return 0.6 + 0.06 * self.fc28
    @property
    def sigmaBc(self) -> float: return 0.6 * self.fc28
    @property
    def Ec(self)    -> float: return 11000 * (self.fc28 ** (1/3))


@dataclass
class Noeud:
    id: int; x: float; y: float; z: float; niveau: int = 0


@dataclass
class Barre:
    id: int; nom: str; ni: int; nj: int
    b: float; h: float
    G_add: float = 0.0; Q_add: float = 0.0
    type_elem: str = ""; longueur: float = 0.0; niveau: int = 0


@dataclass
class Dalle:
    id: int
    noeuds:     List[int] = field(default_factory=list)
    G:          float = 0.0
    Q:          float = 0.0
    sens_lx:    str   = "X"
    type_dalle: str   = "Hourdis"
    e_dalle:    float = 0.0
    lx:         float = 0.0
    ly:         float = 0.0
    rho:        float = 0.0
    mode:       str   = ""
    niveau:     int   = 0


@dataclass
class Semelle:
    id_poteau:    int
    ex:           float = 0.0
    ey:           float = 0.0
    q_adm_loc:    float = 0.0
    long_X_vers:  int   = 0
    long_Y_vers:  int   = 0
    b_long_X:     float = 0.25
    h_long_X:     float = 0.40
    b_long_Y:     float = 0.25
    h_long_Y:     float = 0.40
    Nu_ELU:       float = 0.0
    Nu_ser:       float = 0.0
    B:            float = 0.0
    L_sem:        float = 0.0
    e_sem:        float = 0.0
    Asx:          float = 0.0
    Asy:          float = 0.0
    phi_amorce:   int   = 8
    nb_amorce:    int   = 4
    ls_amorce:    float = 0.0
    q_max:        float = 0.0
    q_min:        float = 0.0
    alerte:       str   = ""
    # Longrine X (si ex>0)
    long_X_Mu:    float = 0.0
    long_X_As:    float = 0.0
    long_X_vM:    str   = ""
    # Longrine Y (si ey>0)
    long_Y_Mu:    float = 0.0
    long_Y_As:    float = 0.0
    long_Y_vM:    str   = ""


@dataclass
class Travee:
    ni: int; nj: int; L: float; q: float
    Mu_span: float; Mu_appui_i: float; Mu_appui_j: float
    Tu_i: float; Tu_j: float


@dataclass
class ResultatPoutre:
    barre_id: int; travee: int; etiq: str
    Mu: float; Tu: float
    As_long: float; As_chap: float; As_chaine: float
    At_st: float; st_max: float; st_ok: bool
    mu_r: float
    vH: str; vFlex: str; vCis: str; vELS: str; vFleche: str
    section: str; alerte: bool = False


@dataclass
class ResultatPoteau:
    barre_id: int; etiq: str; Nu: float
    As: float; alpha: float; lam: float
    phi_am: int; ls_am: float
    vL: str; vS: str; section: str; alerte_am: bool = False


@dataclass
class ResultatDalle:
    dalle_id: int; type_dalle: str; typH: str; h_out: float
    Mu_x: float; Mu_y: float
    As_nerv: float; As_rep: float
    vH: str; vELS: str; alerte: bool = False


@dataclass
class Projet:
    nom:         str       = "Nouveau projet"
    description: str       = ""
    materiaux:   Materiaux = field(default_factory=Materiaux)
    noeuds:      List[Noeud]   = field(default_factory=list)
    barres:      List[Barre]   = field(default_factory=list)
    dalles:      List[Dalle]   = field(default_factory=list)
    semelles:    List[Semelle] = field(default_factory=list)
    niveaux:     List[float]   = field(default_factory=list)
    nb_niveaux:  int = 0
    charges_reportees: dict    = field(default_factory=dict)
