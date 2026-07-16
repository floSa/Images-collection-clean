# Extracteur de cartes Pokémon gradées

Ce programme prend des photos/scans de cartes Pokémon gradées (dans leur
coque PSA, PCA, ...) et en extrait **uniquement la carte** : il détecte
ses contours, redresse la perspective, recadre au format officiel d'une
carte (ratio 63×88 mm) et enregistre le résultat en **PNG sans perte de
qualité** dans un dossier de sortie.

- **Entrée** : le dossier `input`, avec vos images (`.webp`, `.png`,
  `.jpg`, `.jpeg`, `.bmp`, `.tif`)
- **Sortie** : le dossier `output`, avec un fichier `<nom>_carte.png`
  par image (coins arrondis transparents, comme la vraie carte)

Aucune connaissance en informatique n'est requise : ce document vous guide
pas à pas, depuis le téléchargement du projet jusqu'à l'obtention de vos
premières cartes extraites.

## Aperçu

| Avant (scan de la carte gradée) | Après (carte extraite) |
|:---:|:---:|
| ![Photo brute d'une carte gradée dans sa coque](docs/exemple_avant.jpg) | ![Carte extraite, recadrée et détourée](docs/exemple_apres.png) |

---

## 1. Télécharger le projet

Si vous lisez ce fichier directement sur GitHub, commencez par récupérer
le projet sur votre ordinateur.

### Option A — sans rien installer (le plus simple)

1. Sur la page GitHub du projet, cliquez sur le bouton vert **« Code »**.
2. Cliquez sur **« Download ZIP »**.
3. Une fois le fichier `.zip` téléchargé, **faites un clic droit dessus**
   puis **« Extraire tout... »** (Windows) ou double-cliquez dessus
   (macOS). Choisissez un dossier facile à retrouver, par exemple votre
   Bureau.
4. Vous obtenez un dossier contenant `extract_cards.py`, `README.md`,
   etc. C'est ce dossier que vous utiliserez à la partie « 3. Utilisation »
   ci-dessous.

### Option B — avec Git (si vous savez déjà vous en servir)

```bash
git clone https://github.com/floSa/Images-collection-clean.git
cd Images-collection-clean
```

---

## 2. Installation (à faire une seule fois)

Le programme utilise **uv**, un outil qui installe tout seul Python et
les bibliothèques nécessaires. Vous n'avez **pas besoin d'installer
Python vous-même** : le projet est figé sur la version **Python 3.12**
(fichier `.python-version` fourni dans le dossier), et uv installera
exactement cette version, automatiquement, à l'étape 2 ci-dessous.

### Windows

1. Ouvrez le menu Démarrer, tapez `PowerShell` et ouvrez-le.
2. Copiez-collez cette commande puis appuyez sur Entrée (installe `uv`) :

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Fermez puis rouvrez** PowerShell (important, sinon la commande
   `uv` ne sera pas reconnue).
4. Vérifiez que ça a marché en tapant :

   ```powershell
   uv --version
   ```

   Si un numéro de version s'affiche, c'est bon !

5. Installez la version de Python utilisée par le projet (**3.12**) :

   ```powershell
   uv python install 3.12
   ```

6. Vérifiez que c'est bien cette version qui sera utilisée :

   ```powershell
   uv run python --version
   ```

   Doit afficher `Python 3.12.x`.

### macOS / Linux

1. Ouvrez le Terminal.
2. Copiez-collez cette commande puis appuyez sur Entrée (installe `uv`) :

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Fermez puis rouvrez le Terminal, et vérifiez avec `uv --version`.
4. Installez la version de Python utilisée par le projet (**3.12**), puis
   vérifiez-la :

   ```bash
   uv python install 3.12
   uv run python --version
   ```

   Doit afficher `Python 3.12.x`.

---

## 3. Utilisation

### Étape 1 — Ouvrir un terminal DANS le bon dossier

C'est **l'étape la plus importante** : presque tous les problèmes viennent
d'un terminal ouvert au mauvais endroit. Le « bon dossier » est celui qui
contient le fichier `extract_cards.py` (ainsi que `README.md`, `input`,
`output`...).

**Méthode recommandée (Windows) — sans jamais taper de chemin :**

1. Ouvrez l'**Explorateur de fichiers** et allez jusqu'au dossier du
   programme. Vous êtes au bon endroit quand vous **voyez le fichier
   `extract_cards.py`** dans la liste.
2. Cliquez **dans une zone vide** de la fenêtre (pas sur un fichier).
3. **Clic droit** → **« Ouvrir dans le Terminal »**
   (sur Windows 10 : tapez `cmd` dans la barre d'adresse de l'Explorateur,
   puis Entrée — ça ouvre un terminal déjà placé dans ce dossier).

Un terminal s'ouvre, déjà positionné au bon endroit. Vous n'avez aucun
chemin à taper : passez directement à l'étape 2.

**Méthode macOS :** clic droit sur le dossier → **Services** → **Nouveau
terminal au dossier**.

> ✅ **Comment vérifier que vous êtes au bon endroit ?** Le début de ligne
> du terminal doit se terminer par le nom du dossier du programme
> (par exemple `...\Images-collection-clean-main>`). S'il affiche juste
> `C:\Users\VotreNom>`, vous n'êtes **pas** dans le bon dossier : refaites
> la méthode ci-dessus. Lancer le programme depuis le mauvais dossier
> donne l'erreur `No such file or directory`.

<details>
<summary>Si vous tenez à vous déplacer à la main avec <code>cd</code></summary>

Mettez **toujours** le chemin entre guillemets `"..."` : sinon, dès qu'il
contient un espace (comme « Nouveau dossier »), vous obtenez l'erreur
`Impossible de trouver un paramètre positionnel...`.

```powershell
cd "C:\Users\VotreNom\Desktop\Nouveau dossier\Images-collection-clean-main"
```

</details>

### Étape 2 — Mettre vos images dans `input`

Le dossier `input` est déjà présent dans le programme. Placez-y vos
scans/photos de cartes gradées (il contient un fichier `LISEZ-MOI.txt`
que vous pouvez ignorer ou supprimer).

### Étape 3 — Lancer le programme

```bash
uv run python extract_cards.py
```

> La **première fois**, uv télécharge Python et les bibliothèques :
> c'est normal que ça prenne une à deux minutes. Les fois suivantes,
> c'est instantané.

Le programme affiche une ligne par image traitée :

```
5 image(s) à traiter -> C:\...\output
  [OK] 001_NeoG.webp -> 001_NeoG_carte.png (1005x1404)
  ...
Terminé sans erreur.
```

Les cartes extraites sont dans le dossier `output`, créé automatiquement.

### Remarques

- Pour utiliser d'autres dossiers que `input`/`output` :
  `uv run python extract_cards.py --src "C:\Mes Scans" --out "C:\Mes Cartes"`
  (guillemets nécessaires si le chemin contient des espaces).
- Vous pouvez relancer le programme sans risque : les images déjà
  traitées sont simplement régénérées.

---

## 4. En cas de problème

| Symptôme | Solution |
|---|---|
| `uv : terme non reconnu` / `command not found` | Fermez et rouvrez le terminal après l'installation de uv. |
| `No such file or directory` / `[Errno 2]` en lançant `extract_cards.py` | Le terminal n'est pas ouvert dans le bon dossier. Vérifiez que la ligne au-dessus de votre curseur montre bien le chemin du dossier contenant `extract_cards.py` (sinon, voir étape 1 de la partie « 3. Utilisation »). |
| `Set-Location : Impossible de trouver un paramètre positionnel...` (PowerShell, en tapant `cd ...`) | Le chemin contient un espace (ex. « Nouveau dossier ») : mettez-le entre guillemets, ex. `cd "C:\Users\VotreNom\Desktop\Nouveau dossier\..."`. |
| `Aucune image trouvée dans ...` | Vérifiez que vos images sont bien dans le dossier `input` et au format `.webp`, `.png`, `.jpg`, `.jpeg`, `.bmp` ou `.tif`. |
| `[ECHEC] Carte non détectée : ...` | La photo est probablement trop sombre, floue ou la carte est coupée. Reprenez une photo bien cadrée, de face, sur fond contrasté. |
| La carte extraite garde un bord de coque | Relancez avec `uv run python extract_cards.py --debug` : les images dans `output/debug/` montrent le contour détecté en rouge, pratique pour comprendre ce qui se passe. |

---

## 5. Comment ça marche (pour les curieux)

1. **Détection** : le programme cherche des quadrilatères ayant les
   proportions d'une carte, via plusieurs analyses combinées (contours,
   saturation des couleurs — la carte est colorée alors que la coque est
   grise —, luminosité).
2. **Raffinement** : si une marge de coque subsiste autour de la carte,
   le cadrage est resserré par passes successives, puis chaque bord est
   calé au pixel près sur la frontière carte/coque, repérée par la
   montée de chroma (le plastique de la coque est gris/noir, le bord
   imprimé de la carte est coloré). Chaque bord est mesuré en 6 points
   et la ligne de coupe passe à l'intérieur de toutes les mesures, pour
   qu'une carte légèrement bombée dans sa coque ne laisse aucun biseau.
3. **Export** : la perspective est corrigée en une seule transformation
   depuis l'image d'origine (aucune perte cumulée), au ratio exact
   63:88, puis enregistrée en PNG (format sans perte). La résolution de
   la photo d'origine est conservée telle quelle, et les coins sont
   rendus transparents suivant l'arrondi officiel de la carte (3 mm).
