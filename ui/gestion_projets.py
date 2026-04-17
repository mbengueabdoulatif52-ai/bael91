"""
ui/gestion_projets.py
Chargement, sauvegarde et sérialisation des projets JSON
"""
import json
import os
from pathlib import Path
from dataclasses import asdict
from typing import List
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import Projet, Materiaux, Noeud, Barre, Dalle, Semelle


PROJECTS_DIR = Path(__file__).parent.parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)


def charger_projets() -> List[dict]:
    """Retourne la liste des projets sauvegardés."""
    projets = []
    for f in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
                projets.append({"nom": data.get("nom", f.stem), "fichier": str(f)})
        except Exception:
            pass
    return projets


def sauvegarder_projet(projet: Projet) -> str:
    """Sauvegarde un projet en JSON. Retourne le chemin du fichier."""
    nom_safe = "".join(c if c.isalnum() or c in "_ -" else "_" for c in projet.nom)
    fichier = PROJECTS_DIR / f"{nom_safe}.json"

    data = serialiser_projet(projet)
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(fichier)


def charger_projet(fichier: str) -> Projet:
    """Charge un projet depuis un fichier JSON."""
    with open(fichier, encoding="utf-8") as f:
        data = json.load(f)
    return deserialiser_projet(data)


def nouveau_projet(nom: str = "Nouveau projet") -> Projet:
    """Crée un projet vide avec les matériaux par défaut."""
    return Projet(
        nom=nom,
        materiaux=Materiaux(),
        noeuds=[],
        barres=[],
        dalles=[],
        semelles=[],
    )


def serialiser_projet(projet: Projet) -> dict:
    """Convertit un Projet en dict JSON-serializable."""
    return {
        "nom":        projet.nom,
        "description": projet.description,
        "materiaux": {
            "fc28":     projet.materiaux.fc28,
            "gammab":   projet.materiaux.gammab,
            "fe":       projet.materiaux.fe,
            "gammas":   projet.materiaux.gammas,
            "rhoba":    projet.materiaux.rhoba,
            "c_poutre": projet.materiaux.c_poutre,
            "c_dalle":  projet.materiaux.c_dalle,
            "c_poteau": projet.materiaux.c_poteau,
            "c_fond":   projet.materiaux.c_fond,
            "Df":       projet.materiaux.Df,
            "q_adm":    projet.materiaux.q_adm,
        },
        "noeuds": [
            {"id": n.id, "x": n.x, "y": n.y, "z": n.z}
            for n in projet.noeuds
        ],
        "barres": [
            {"id": b.id, "nom": b.nom, "ni": b.ni, "nj": b.nj,
             "b": b.b, "h": b.h, "G_add": b.G_add, "Q_add": b.Q_add}
            for b in projet.barres
        ],
        "dalles": [
            {"id": d.id, "noeuds": d.noeuds, "G": d.G, "Q": d.Q,
             "sens_lx": d.sens_lx, "type_dalle": d.type_dalle, "e_dalle": d.e_dalle}
            for d in projet.dalles
        ],
        "semelles": [
            {"id_poteau": s.id_poteau, "ex": s.ex, "ey": s.ey,
             "q_adm_loc": s.q_adm_loc,
             "long_X_vers": s.long_X_vers, "long_Y_vers": s.long_Y_vers,
             "b_long_X": s.b_long_X, "h_long_X": s.h_long_X,
             "b_long_Y": s.b_long_Y, "h_long_Y": s.h_long_Y}
            for s in projet.semelles
        ],
    }


def deserialiser_projet(data: dict) -> Projet:
    """Reconstruit un Projet depuis un dict JSON."""
    p = Projet(
        nom=data.get("nom", "Projet"),
        description=data.get("description", ""),
    )
    m = data.get("materiaux", {})
    for k, v in m.items():
        if hasattr(p.materiaux, k):
            setattr(p.materiaux, k, v)

    for nd in data.get("noeuds", []):
        p.noeuds.append(Noeud(
            id=nd["id"], x=nd["x"], y=nd["y"], z=nd["z"]
        ))
    for b in data.get("barres", []):
        p.barres.append(Barre(
            id=b["id"], nom=b.get("nom", f"B{b['id']}"),
            ni=b["ni"], nj=b["nj"],
            b=b["b"], h=b["h"],
            G_add=b.get("G_add", 0), Q_add=b.get("Q_add", 0)
        ))
    for d in data.get("dalles", []):
        p.dalles.append(Dalle(
            id=d["id"], noeuds=d["noeuds"],
            G=d["G"], Q=d["Q"],
            sens_lx=d.get("sens_lx", "X"),
            type_dalle=d.get("type_dalle", "Hourdis"),
            e_dalle=d.get("e_dalle", 0.0)
        ))
    for s in data.get("semelles", []):
        p.semelles.append(Semelle(
            id_poteau=s["id_poteau"],
            ex=s.get("ex", 0), ey=s.get("ey", 0),
            q_adm_loc=s.get("q_adm_loc", 0),
            long_X_vers=s.get("long_X_vers", 0),
            long_Y_vers=s.get("long_Y_vers", 0),
            b_long_X=s.get("b_long_X", 0.25), h_long_X=s.get("h_long_X", 0.40),
            b_long_Y=s.get("b_long_Y", 0.25), h_long_Y=s.get("h_long_Y", 0.40),
        ))
    return p
