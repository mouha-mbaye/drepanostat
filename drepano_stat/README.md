# DrepanoStat

DrepanoStat est une application web développée en Python pour automatiser l’analyse statistique des tests anti-falcémiants réalisés à partir de comptages microscopiques de globules rouges normaux et drépanocytaires.
L’application permet à l’utilisateur de générer un modèle Excel standardisé, d’importer les données de comptage, de vérifier automatiquement la qualité du fichier, de produire les tableaux statistiques, de générer des graphes prêts pour un rapport scientifique et d’exporter les résultats.
Elle est destinée aux étudiants, chercheurs et techniciens de laboratoire qui souhaitent réaliser une analyse reproductible sans écrire de code Python.

> Version stable actuelle : **v0.1.0**

## Fonctionnalités principales

- définition libre des groupes d’extraits, dilutions, témoins et répétitions ;
- génération d’un modèle Excel standardisé avec menus déroulants ;
- validation détaillée du fichier rempli et détection des répétitions manquantes ;
- calcul des proportions de globules rouges normaux et drépanocytaires ;
- tableaux descriptifs et classements par condition et par groupe ;
- GLM binomial comparant chaque extrait au Témoin véhicule ;
- comparaisons deux à deux entre groupes à dilution identique ;
- correction des p-values par la méthode de Holm ;
- figures statiques exportables en PNG 300 dpi et SVG ;
- rapport analytique Word et archive ZIP regroupant les résultats.

Les valeurs internes `Vehicle` et `Emmel` sont conservées pour les calculs. Elles
sont présentées à l’utilisateur sous les libellés « Témoin véhicule » et
« Témoin Emmel ».

## Installation

Python 3.11 ou une version plus récente est recommandé.

```bash
git clone <URL_DU_DEPOT>
cd drepano_stat
python -m venv .venv
```

Activation de l’environnement sous Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Sous macOS ou Linux :

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement de l’application

Depuis le dossier qui contient `app.py` :

```bash
streamlit run app.py
```

Streamlit indique ensuite l’adresse locale à ouvrir dans un navigateur,
généralement `http://localhost:8501`.

## Format des données

La feuille Excel `Données` contient les colonnes suivantes :

| Colonne | Description |
|---|---|
| `type_condition` | `Extrait` ou `Témoin` |
| `groupe` | Groupe expérimental pour un extrait |
| `dilution` | Dilution de l’extrait |
| `temoin` | Nom interne du témoin, par exemple `Vehicle` |
| `repetition` | Numéro entier positif de la répétition |
| `N` | Nombre de globules rouges normaux |
| `D` | Nombre de globules rouges drépanocytaires |
| `commentaire` | Observation facultative |

`N` et `D` doivent être des entiers positifs ou nuls et leur somme doit être
strictement supérieure à zéro. Un modèle prêt à remplir est disponible dans
[`examples/modele_exemple.xlsx`](examples/modele_exemple.xlsx).

## Workflow d’utilisation

1. Définir l’étude dans le premier onglet.
2. Télécharger le modèle Excel généré.
3. Renseigner uniquement les comptages `N`, `D` et les commentaires éventuels.
4. Réimporter le classeur rempli.
5. Corriger les éventuelles erreurs bloquantes signalées.
6. Examiner les tableaux descriptifs et les analyses statistiques.
7. Télécharger les tableaux, figures, le rapport Word ou l’archive ZIP.

## Méthodologie statistique

Pour chaque répétition, DrepanoStat calcule :

- `total = N + D` ;
- `prop_normal = N / total` ;
- `prop_drepano = D / total`.

Les comparaisons statistiques utilisent directement les comptages groupés
`[N, D]`, et non les proportions. Le modèle principal est un GLM binomial avec
lien logit et `Vehicle` comme modalité interne de référence. Un odds ratio
supérieur à 1 indique une augmentation des chances d’observer un globule rouge
normal relativement au Témoin véhicule.

Les groupes d’extraits sont également comparés deux à deux à dilution identique.
Les p-values sont corrigées par la méthode de Holm au sein de chaque famille de
comparaisons. Les odds ratios sont accompagnés de leurs intervalles de confiance
à 95 %.

## Limites

- Les résultats dépendent de la qualité des comptages et du protocole expérimental.
- Un faible nombre de répétitions limite la précision des estimations.
- Les répétitions techniques ne remplacent pas des répétitions biologiques indépendantes.
- La variabilité de l’observateur et le nombre total de cellules peuvent influencer les résultats.
- Les classements sont descriptifs et ne constituent pas une conclusion biologique à eux seuls.
- L’interprétation finale doit tenir compte du contexte expérimental et d’essais complémentaires.

## Technologies utilisées

- Python ;
- Streamlit ;
- pandas et NumPy ;
- statsmodels ;
- Matplotlib ;
- openpyxl ;
- python-docx.

## Statut du projet

La version **v0.1.0** constitue la première version stable locale. Elle couvre le workflow complet, de la création du fichier d’entrée jusqu’au rapport analytique et à l’archive des résultats.

## Auteur

Mbaye — Projet développé dans le cadre d’un outil d’appui à l’analyse statistique des tests anti-falcémiants en pharmacognosie.

## Licence

Ce projet est distribué sous licence MIT. Consultez le fichier [LICENSE](LICENSE).

