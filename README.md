# BAEL 91 — Dimensionnement béton armé

Outil de calcul pour structures en béton armé selon la norme **BAEL 91 révisé 99**.  
Développé pour les bureaux d'études sénégalais.

## Fonctionnalités

- Dalles hourdis et pleines (coefficients BAEL Annexe E3)
- Poutres continues (méthode de Clapeyron)
- Poteaux avec flambement BAEL 99
- Descente de charges complète
- Semelles centrées et excentriques + longrines
- Export PDF et Excel
- Visualisation 3D interactive
- Import depuis fichier Excel de saisie

## Lancement en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Workflow

1. Télécharger `BAEL91_Saisie_v13.xlsx` depuis la page Accueil
2. Remplir vos données dans Excel
3. Importer le fichier dans l'application
4. Lancer le calcul
5. Consulter les résultats et exporter PDF/Excel

## Contexte

Adapté au marché sénégalais :
- Gamme de béton courant fc28 = 25 MPa
- Acier FeE400 (HA400)
- Classe d'exposition Normal / Côtier (littoral dakarois)
- Contrainte admissible sol typique Dakar : 150 kN/m²

  <!-- v3.4 -->
