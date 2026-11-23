                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy : recherche d'emploi et scoring multi-moteurs</h1>

<p align="center">
<strong>Cherchez plus intelligemment, mieux, plus vite, plus fort.</strong><br>
Scraping d'offres en parallèle sur les principales plateformes, scoring automatisé des CV et rapports classés.
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 ou plus récent"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="Licence MIT"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="Score M8ven"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>Démarrage rapide</strong></a> ·
  <a href="#features">Fonctionnalités</a> ·
  <a href="#job-engines">Moteurs d'emploi</a> ·
  <a href="#portfolio-support">Prise en charge du portfolio</a> ·
  <a href="#documentation">Documentation</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">Signaler un problème</a>
</p>

<p align="center">
  <a href="../README.md">English</a> · <a href="README.es.md">Español</a> · <strong>Français</strong> · <a href="README.hi.md">हिन्दी</a> · <a href="README.ja.md">日本語</a> · <a href="README.ar.md">العربية</a> · <a href="README.zh.md">简体中文</a>
</p>

---

Sweepy est un outil gratuit qui parcourt les sites d'offres d'emploi et évalue chaque annonce par rapport à votre CV. Il lit les sites carrières des entreprises et les sites d'offres, écarte les annonces en double et expirées, puis rédige un rapport classé. Vous pouvez désactiver la vérification des doublons pour un seul sweep sans modifier votre profil. L'assistant de configuration ouvre un tableau de bord pour les recherches, la configuration du profil, le réglage des recherches et les tâches de la Boîte à outils Sweepy, comme la gestion des moteurs et des agrégateurs.

> Consultez **[CHANGELOG.md](../CHANGELOG.md)** pour la version actuelle et l'historique des versions.

## <a name="features"></a>Fonctionnalités

- **Cherche à de nombreux endroits à la fois.** Collecte les annonces de Greenhouse, Ashby, Lever, Workable, Built In NYC, LinkedIn, Indeed, Glassdoor et ZipRecruiter. Chacune de ces sources fonctionne sans clé API.
- **Exécute tous les moteurs en parallèle.** Les moteurs activés démarrent ensemble. Un sweep prend alors environ le temps du moteur le plus lent plutôt que leur somme.
- **Continue quand un site échoue.** Chaque moteur dispose d'un délai d'expiration et d'un disjoncteur. Un point de terminaison défaillant ne peut ni bloquer l'exécution ni répéter cinq fois la même requête.
- **Ajoute d'autres moteurs à la demande.** Installez HireHunt, openroles, jobdrop ou Apify depuis l'assistant sans quitter le terminal.
- **Évalue chaque annonce par rapport à votre CV.** Lit le texte de votre CV PDF ou Word et mesure la part qui correspond à l'annonce.
- **Écarte les liens expirés.** Vérifie chaque URL et supprime les annonces qui n'existent plus.
- **Détecte les annonces en double entre les sites.** Compare l'intitulé de poste normalisé, l'entreprise et le lieu, même quand les sites utilisent des URL différentes. Passez `--no-dedupe` pour conserver l'annonce de chaque site le temps d'une exécution.
- **Ignore les annonces que vous avez déjà vues.** Un sweep quotidien signale les nouveaux postes plutôt que la liste de la veille. Sweepy masque les annonces signalées pendant une fenêtre de quatre jours. Passez `--include-seen` pour les réafficher le temps d'une exécution.
- **Vous oriente vers le bon CV.** Envoie chaque offre vers la piste de CV que vous avez rédigée pour ce poste, puis étiquette la fiche avec un badge de couleur.
- **Intègre votre portfolio à chaque décision.** Indiquez à Sweepy un portfolio en ligne ou un fichier local PDF, Word, Markdown, texte ou HTML. Chaque fiche liste les pièces de ce portfolio. Quand vous postulez à plusieurs types de postes, gardez un portfolio par piste de CV.
- **Produit un rapport exploitable.** Génère un PDF avec une fiche par page et des liens cliquables, plus des fichiers CSV et JSON pour votre propre suivi.
- **Transforme le CSV en suivi de candidatures.** Le CSV se termine par `date_applied`, `status`, `interview_stage`, `offer_amount`, `offer_date`, `follow_up_date`, `contact` et `notes`. Remplissez-les dans Excel, Google Sheets ou Notion. Sweepy recopie vos saisies dans les sweeps suivants du même profil. Le PDF vous donne une liste de lecture classée avec des liens de candidature sur chaque fiche. Le tableur conserve les postes au-delà de la limite de fiches du PDF et note ce que vous avez fait pour chacun. Désactivez les colonnes avec `export.tracking: false`.

## <a name="quick-start"></a>Démarrage rapide

Vous avez besoin de **Python 3.10 ou plus récent**. Sous Python 3.13, certains paquets se compilent depuis les sources. Il vous faut peut-être d'abord les Microsoft C++ Build Tools. Consultez [Installer Sweepy](https://pvega62.github.io/software/docs/sweepy/installation).

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` installe toutes les dépendances principales et enregistre la commande `sweepy` dans votre dossier Python Scripts. Rouvrez votre terminal une fois pour que votre shell prenne en compte ce dossier depuis PATH. Lancez `sweepy` pour démarrer l'assistant, ou ajoutez une option de commande comme `sweepy --run`. Vous pouvez aussi lancer le script directement avec `python swee.py`.

Cette seule commande vous donne les deux moteurs intégrés. L'assistant propose les quatre moteurs optionnels quand vous en avez besoin, et vous n'installez jamais à la main un second fichier requirements.

Pour récupérer tous les moteurs compatibles d'emblée, ajoutez plutôt un indicateur à la même commande :

```bash
pip install -e ".[all-engines]"
```

Cela ajoute HireHunt, openroles et Apify en une seule résolution. `jobdrop` reste à l'écart parce que ses métadonnées ne se résolvent pas à côté de JobSpy. Installez-le avec `sweepy --install-engines jobdrop --allow-engine-conflicts` quand vous voulez ses 33 sites d'offres. La section [Moteurs d'emploi](#job-engines) couvre les deux chemins.

Lancer `sweepy` ouvre le tableau de bord de l'assistant sous forme de tuiles. Utilisez les touches fléchées pour passer entre **Start Sweep**, **Build Profile**, **Load Profile**, **Sweep Settings**, **Sweepy's Toolbox** et **Exit Sweepy**, puis appuyez sur Entrée. Les sous-titres des tuiles énoncent l'action en mots simples, comme **Run your job search now** ou **Open a search you saved**. **Load Profile** vous laisse choisir un profil enregistré pour le prochain sweep. La boîte à outils contient la modification de profil, la gestion des moteurs, la journalisation de débogage, l'aide, les journaux récents, la conversion de documents et les mises à jour. **Build Profile** collecte votre nom, vos intitulés de poste cibles, votre lieu et le chemin de votre CV. L'assistant enregistre le profil quand vous avez terminé. Lancez `sweepy --setup --profile profiles/your_profile.yaml` pour modifier un profil directement.

Les sous-menus s'ouvrent avec **← Back**, qui revient au menu qui les a ouverts. Échap fait de même. À une question, Échap rouvre la réponse précédente. Dans un sous-menu, Échap remonte d'un niveau. Sur le tableau de bord, Échap quitte. Ctrl+C quitte depuis n'importe où.

Pour récupérer le nouveau code lors d'une nouvelle version, lancez :

```bash
sweepy --update
```

Sweepy vérifie votre dépôt Git distant et met le checkout à jour en fast-forward. Il réinstalle `requirements.txt` et les moteurs optionnels que vous avez déjà installés. Il refuse de modifier un checkout qui contient des changements non validés. Préférez `sweepy --check-update` pour vérifier une nouvelle version sans rien modifier.

Lancez ensuite votre premier sweep :

```bash
sweepy --run
```

`--run` effectue un sweep avec le dernier profil que vous avez enregistré. Pour nommer un autre profil, utilisez `sweepy --profile profiles/your_profile.yaml`.

Désactivez la vérification des doublons pour une exécution sans modifier un réglage de profil :

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

Par défaut, Sweepy conserve une seule annonce quand plusieurs sites listent le même intitulé normalisé, la même entreprise et le même lieu. L'outil `run_sweep` du Model Context Protocol (MCP) accepte `deduplicate=false` pour la même dérogation propre à l'exécution.

Sweepy masque aussi les annonces des sweeps précédents. Relisez-les ou repartez de zéro :

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

Créez ou mettez à jour un profil sans invites quand vous scriptez Sweepy :

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

Sweepy valide les moteurs activés avant d'écrire le fichier. Un champ obligatoire manquant échoue immédiatement avec la raison. Dans l'assistant interactif, laissez les slugs d'entreprise OpenRoles vides pour ignorer ce moteur. OpenRoles ne cherche que dans les sites d'entreprises nommées. Les profils non interactifs qui activent OpenRoles ont toujours besoin de `--openroles-companies`. Les indicateurs non interactifs couvrent `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, `--no-cache`, `--history-days`, `--no-history` et `--job-tracking` / `--no-job-tracking`.

Remplissez un fichier de profil quand vous préférez un éditeur aux invites et aux appels d'outils :

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

Le modèle documente chaque réglage avec sa valeur par défaut. Sweepy affiche votre nom, vos intitulés et votre lieu avant le début de la découverte. Une faute de frappe apparaît dès la première ligne de sortie.

Convertissez un CV ou un fichier de notes en PDF sans ouvrir l'assistant :

```bash
sweepy --convert path/to/resume.docx
```

`--convert` accepte les fichiers `.docx`, `.doc`, `.txt`, `.md` et `.pdf`. Il écrit le PDF à côté du fichier d'origine et affiche le chemin final.

Un sweep prend de 30 à 90 secondes. Sweepy affiche sa progression pendant qu'il travaille :

1. **Charge votre profil.**
2. **Découvre les offres** sur les plateformes que vous avez activées.
3. **Valide les liens** et écarte les liens expirés.
4. **Évalue chaque poste** par rapport à votre CV.
5. **Rédige votre rapport.**

## <a name="what-you-get"></a>Ce que vous obtenez

Chaque exécution écrit des fichiers horodatés dans le dossier `results/`. Les rapports précédents restent en place. Un sweep lancé via MCP ajoute `mcp` au nom de fichier, comme dans `paralegal_nyc_mcp_2026-10-27-223115.pdf`. L'horodatage suit l'horloge de votre machine. Définissez `export.timezone` pour nommer les fichiers dans un autre fuseau.

- **Un rapport PDF.** Une fiche par poste, triée par score de correspondance, avec le salaire, les avantages et un lien pour postuler.
- **Un fichier CSV.** Tous les champs de la fiche, le corps complet de l'annonce et huit colonnes de suivi des candidatures que Sweepy recopie dans les sweeps suivants. Ouvrez-le dans Excel, Google Sheets ou Notion. Définissez `export.description_chars` sur un nombre positif quand vous voulez des fichiers plus légers. Un corps tronqué se termine par une note qui compte les caractères omis.
- **Un fichier JSON.** Les mêmes données dans un format lisible par d'autres outils.

Ouvrez le [PDF d'exemple](../docs/sample_report.pdf) ou consultez [la page 1 en image](../docs/sample_report.png).

## <a name="job-engines"></a>Moteurs d'emploi

Sweepy inclut deux moteurs et peut en télécharger quatre autres. Le moteur `ats` lit directement les systèmes de suivi des candidatures (ATS). Chaque moteur s'exécute derrière le même adaptateur. Les profils se présentent de la même façon, quel que soit le moteur qui a trouvé l'annonce.

| Moteur | Disponibilité | Ce qu'il scrape | Proxies | User-Agent | Descriptions |
|---|---|---|---|---|---|
| `jobspy` | Intégré | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | Oui | Oui | Activable |
| `ats` | Intégré | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | Non | Non | Toujours |
| `hirehunt` | Téléchargement | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop et six sites d'entreprises (Google Careers, Amazon, Meta, Apple, Netflix, Microsoft) | Non | Non | Toujours |
| `openroles` | Téléchargement | Sites Greenhouse, Lever, Ashby, Workday que vous nommez | Non | Non | Toujours |
| `jobdrop` | Téléchargement | 33 sites dont Google, Wellfound, Workday, iCIMS, Dice, USAJobs | Oui | Oui | Activable |
| `apify` | Téléchargement | Acteurs gérés, LinkedIn par défaut | Géré par l'acteur | Géré par l'acteur | Selon l'acteur |

`jobdrop` signale un conflit de métadonnées avec JobSpy : il épingle `curl-cffi<0.8`, alors que JobSpy exige `curl_cffi>=0.16.2`. L'épinglage est obsolète. `jobdrop` fonctionne très bien avec la bibliothèque plus récente, qui contient encore tous les profils d'usurpation qu'il utilise (`safari17_2_ios`, `chrome120`, `chrome124`).

Un `pip install` simple des deux échoue toujours. `--install-engines all` laisse `jobdrop` de côté. Ajoutez `--allow-engine-conflicts` pour l'installer de la façon prise en charge. Sweepy installe `jobdrop` avec `--no-deps`, puis résout ses autres dépendances, si bien que `curl_cffi` reste à la version de JobSpy et que les deux moteurs fonctionnent.

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

`pip check` signale toujours la borne supérieure obsolète de `jobdrop` après cette installation. L'avertissement décrit les métadonnées, pas le code en cours d'exécution.

Ou ouvrez l'assistant et choisissez **Sweepy's Toolbox** puis **Download job engines**. Cet écran liste les sites d'offres et l'état d'installation de chaque moteur. Il demande confirmation avant de lancer `pip`. Choisissez un moteur manquant pendant la création d'un profil et l'assistant propose le même téléchargement. Sweepy ne lance jamais une installation sans votre confirmation.

### <a name="disk-footprint"></a>Empreinte disque

Mesurée sous Windows avec Python 3.13 :

| Installation | Paquets sur disque | Notes |
|---|---|---|
| Cœur (`requirements.txt`) | 283 Mo | 53 paquets, dont pandas, pymupdf et le SDK MCP |
| `hirehunt` | +13 Mo | Ajoute rich et markdown-it-py |
| `openroles` | +0,3 Mo | Bibliothèque standard Python uniquement |
| `apify-client` | +14 Mo | Ajoute impit et more-itertools |
| `jobdrop` | +406 Mo | Dominé par scipy (134 Mo), playwright (113 Mo), tls-client (93 Mo) et selenium (34 Mo) |

Une installation complète des moteurs compatibles prend environ **310 Mo**. L'ajout de `jobdrop` porte le total à environ **716 Mo** avant le téléchargement d'un navigateur.

Les binaires de navigateur vivent en dehors de l'environnement Python et arrivent à la première utilisation :

- La version Chromium de Playwright fait environ **710 Mo** (Chromium plus son shell headless).
- Un ensemble Playwright complet, Firefox et WebKit compris, représente environ **1,2 Go**.
- Camoufox, que `jobdrop` utilise pour son chemin furtif, télécharge un Firefox modifié au premier lancement.

Sweepy exécute tous les moteurs intégrés sans navigateur. L'installation de base n'utilise rien de cet espace.

Listez les moteurs et leur état d'installation à tout moment :

```bash
sweepy --list-engines
```

`openroles` lit les sites d'offres que vous nommez et exige des slugs d'entreprise. `apify` lit une variable d'environnement `APIFY_TOKEN` et facture sur votre compte Apify.

Installer un moteur ne l'active pas. Ajoutez-le à un profil de l'une des trois façons suivantes :

1. **Assistant.** Lancez `sweepy`, choisissez **Sweepy's Toolbox**, puis **Manage job engines**, puis **Choose engines and settings**. Les moteurs installés affichent un tag `[installed]`. Cochez-en un et l'assistant demande ses réglages.
2. **Modification de profil.** Chargez le profil, puis choisissez **Manage job engines** dans l'écran de récapitulatif.
3. **Ligne de commande.** Nommez le moteur dans `--sources` et fournissez ses réglages :

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

Chaque chemin valide les réglages du moteur avant d'écrire le fichier. Une valeur manquante, comme les slugs d'entreprise `openroles`, échoue avec la raison au lieu d'enregistrer un profil cassé.

### <a name="choosing-boards"></a>Choix des sites

L'étape des plateformes de l'assistant de profil liste tous les sites d'offres que Sweepy peut parcourir, regroupés sous le moteur qui les lit. Les 63 sites apparaissent au même endroit au lieu de seulement les 13 sites intégrés.

| Groupe | Sites | Tag |
|---|---|---|
| `jobspy` (8) | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | `built in` |
| `ats` (5) | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | `built in` |
| `hirehunt` (12) | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, Google Careers, Amazon, Meta, Apple, Netflix, Microsoft | `needs download` jusqu'à l'installation |
| `openroles` (4) | Greenhouse, Lever, Ashby, Workday | `needs download`, et exige des slugs d'entreprise |
| `jobdrop` (33) | Google, Wellfound, Workday, iCIMS, Dice, USAJobs, Handshake et plus | `needs download`, et entre en conflit avec JobSpy |
| `apify` (1) | LinkedIn via un acteur Apify | `needs download`, et exige un `APIFY_TOKEN` |

Chaque ligne affiche son moteur et son état d'installation, par exemple `Indeed  [jobspy · built in]` ou `Wellfound  [jobdrop · needs download]`. Vous voyez le tag avant de valider le choix. Cochez un site d'un moteur sans installation locale et l'assistant affiche la commande qui l'installe. Un moteur installé affiche `installed` à la place. Rouvrir un profil enregistré montre ses sites actuels déjà cochés. Sweepy conserve dans le profil un site d'un moteur non installé, et le sweep ignore ce moteur avec un avertissement jusqu'à la fin de l'installation.

### <a name="engine-settings"></a>Réglages des moteurs

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  greenhouse:
    discovery: broad
    concurrency: 20
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

Les profils plus anciens continuent de fonctionner. Les booléens de site sous `sources.jobspy` activent et désactivent toujours chaque site JobSpy. Tout profil sans liste `sources.enabled` prend par défaut JobSpy plus les lecteurs ATS intégrés.

- **Les descriptions restent activées par défaut.** Le scoring compare le texte de l'annonce à votre CV. Désactivez `fetch_descriptions` seulement si vous acceptez des correspondances plus faibles pour un sweep plus rapide.
- **Greenhouse lit une liste de sites plus large sur demande.** `sources.greenhouse.boards` nomme les sites que vous voulez. Définissez `sources.greenhouse.discovery: broad` pour parcourir aussi la liste groupée de 619 slugs dans `data/sources/greenhouse_slugs_broad.txt`, et Sweepy ajoute tout site que votre profil nomme déjà. `sources.greenhouse.concurrency` définit combien de sites Sweepy lit à la fois : 20 en mode broad, 1 sinon. Une sonde broad génère beaucoup de réponses HTTP 404 par conception. Sweepy signale le nombre d'échecs et les dix premiers slugs dans un seul avertissement au lieu d'une ligne par site.
- **Les proxies restent sur activation explicite, moteur par moteur.** L'assistant les lit dans un fichier ou en accepte un en ligne, masque le mot de passe pendant la saisie et n'affiche jamais le contenu. `hirehunt` n'offre pas d'option proxy, donc Sweepy journalise un avertissement quand un profil en configure un.
- **Le cache démarre activé.** Une requête répétée avec les mêmes moteurs et réglages renvoie les résultats précédents pendant une heure. Videz-le avec `cache.enabled: false`, ou raccourcissez `ttl_seconds`.
- **Les délais d'expiration s'arrêtent à la frontière.** Python ne peut pas arrêter un thread déjà bloqué dans un appel de bibliothèque. Sweepy cesse d'attendre et passe à la suite, et chaque bibliothèque applique ses propres délais HTTP en dessous.
- **Le disjoncteur ignore un moteur défaillant.** Après cinq échecs consécutifs, Sweepy cesse d'appeler ce moteur pendant 30 secondes et le signale dans `skipped_sources`.

### <a name="reported-postings"></a>Annonces signalées

Sweepy enregistre chaque annonce qu'il signale et ignore la même annonce au sweep suivant. Sweepy stocke l'enregistrement dans `~/.sweepy/history.db`, avec une portée par profil. Définissez `SWEEPY_HISTORY_PATH` pour le stocker ailleurs. L'écran **Sweep Settings** de l'assistant expose l'interrupteur d'activation et la fenêtre de rétention.

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **La rétention est une cadence de re-signalement.** Sweepy masque une annonce jusqu'à ce que `retention_days` s'écoule, puis la signale de nouveau. Une annonce toujours active revient au plus tous les quatre jours.
- **La correspondance est tolérante par défaut.** Sweepy compare les URL canoniques après avoir retiré les paramètres de suivi et les fragments. Il se rabat ensuite sur l'intitulé normalisé, l'entreprise et le lieu, si bien qu'une republication sur un autre site compte comme le même poste. Définissez `match: url` pour exiger une correspondance d'URL canonique.
- **Seules les annonces actives comptent.** Une annonce entre dans l'historique une fois son URL validée. Les liens expirés ne deviennent jamais invisibles.
- **Les appelants MCP obtiennent le même défaut.** `run_sweep` signale `previously_seen_count` et `new_count`. Passez `include_seen=true` pour relire les annonces précédentes, ou appelez `clear_history` pour les oublier. `create_profile` accepte `history_config`.

### <a name="adding-another-engine"></a>Ajouter un autre moteur

1. Créez `engine/adapters/<name>_adapter.py` et héritez de `ScraperAdapter`.
2. Définissez `name`, les trois indicateurs `supports_*`, `default_concurrency` et `library`.
3. Écrivez `preflight()` pour vérifier la configuration et `scrape()` pour renvoyer un DataFrame.
4. Enregistrez-le dans `engine/adapters/__init__.py`.
5. Décrivez-le dans `engine/engines.py` pour que l'assistant puisse l'afficher et l'installer.
6. Ajoutez un bloc de configuration à `engine/sweep_config.py` et une invite à `_ENGINE_PROMPTS` dans `engine/config.py`.
7. Ajoutez le paquet à `requirements-engines.txt` et aux extras pyproject.
8. Testez l'adaptateur seul, puis activez-le seul pendant un sweep.

L'orchestrateur gère le reste. Il distribue par nom et applique le délai d'expiration. Il normalise chaque trame qui revient.

## <a name="agent-judgment"></a>Jugement de l'agent

Sweepy évalue les annonces par vocabulaire partagé, et ce scoring n'appelle pas de modèle et n'utilise pas le réseau. Les mêmes entrées produisent le même score, qui mesure la formulation, pas l'adéquation. Le serveur MCP considère une évaluation par agent comme le chemin attendu.

`run_sweep` n'appelle pas de modèle. Il renvoie `assessment_mode: "agent"`, `assessment_required: true` et `assessed_count: 0`. Le flux de travail se poursuit avec `get_jobs`, une évaluation indépendante de chaque poste par rapport au CV, `submit_judgments` et `render_report`. Passez chaque jugement dans une seule liste `judgments` pour qu'une évaluation de 24 postes tienne en un appel. Les fiches évaluées affichent `NN% MATCH`. Les fiches non évaluées conservent `NN% KEYWORD OVERLAP`.

`get_jobs` renvoie `resume_documents` avec le texte analysé de chaque piste de CV. Jugez ce texte, pas les `must_have_skills` et `synonyms` du profil, qui alimentent seulement la passe de mots-clés déterministe. Lisez le document comme un recruteur le lit : compétences transférables, portée et ancienneté derrière chaque puce, domaine, outils et résultats démontrés. Évaluez-le ensuite de la façon dont le système de suivi des candidatures de l'annonce l'analyse. Un terme que l'analyseur trouve dans une section Experience ou Skills standard compte comme une preuve. Le même terme dans un tableau, un en-tête, un pied de page, une image ou une barre latérale à deux colonnes peut ne jamais atteindre une personne : il pèse donc moins. Sweepy nomme la famille ATS quand l'URL de candidature le révèle, et le jugement note ce qu'un analyseur perdrait.

`match_pct` mesure les qualifications, donc la logistique d'emploi en reste exclue. Les horaires à temps partiel, le statut de contrat et le lieu relèvent de `concerns`. Un poste que le candidat peut tenir ne perd des points que si les compétences ou l'expérience ne correspondent pas aux exigences énoncées dans l'annonce. Le classement mesure alors l'adéquation plutôt que la disponibilité.

Évaluez les deux côtés du dossier. `alignment` énonce le point fort, la preuve la plus solide que le candidat convient. `concerns` énonce ce qui joue contre le candidat. Parmi les exemples figurent une qualification manquante, un écart d'ancienneté, des horaires à temps partiel, un contrat à durée déterminée, un lieu qui impose un déménagement ou une rémunération sous le plancher. Le rapport imprime la paire sur une ligne sous la ligne des exigences, et le CSV gagne une colonne `concerns`. Une exécution par mots-clés seulement remplit `concerns` avec les mots-clés de l'annonce que le CV ne contient pas.

`submit_judgments` accepte aussi `portfolio_highlight`. Passez les pièces du portfolio pour cette annonce, et la fiche les imprime sous **Highlight**. Une fiche sans highlight fourni liste les pièces que Sweepy a trouvées.

## <a name="portfolio-support"></a>Prise en charge du portfolio

Sweepy lit un portfolio une fois par sweep et liste ses pièces sur chaque fiche. Il collecte le portfolio avant de construire le profil. Donnez-lui une URL en ligne ou un fichier local `.pdf`, `.docx`, `.md`, `.txt` ou `.html`. Passez une entrée par piste de CV quand vous ciblez plus d'une famille de postes.

```yaml
portfolio:
  # One entry per resume track. An entry without `track` serves every track.
  sources:
    - track: "UX Writer Resume"
      url: "https://example.com/work"
    - track: "Technical Writer Resume"
      path: "C:/portfolios/technical-writing.pdf"
  pieces_per_card: 3
```

Sweepy récupère un portfolio en ligne pour lire ses titres et ses liens. Quand une page bloque la requête, la fiche garde le lien et saute la liste des pièces. La fiche PDF montre le portfolio et ses pièces. Les exports CSV et JSON ajoutent `portfolio_url`, `portfolio_pieces` et `portfolio_highlight`.

Pour attacher un portfolio à un profil enregistré, appelez `set_portfolio` depuis le MCP ou répondez à l'étape portfolio de l'assistant. Une configuration headless accepte `--portfolio` et `--portfolio-track`.

`render_report` prend un argument `playbook` pour l'encadré de stratégie de clôture. Écrivez de la prose simple. Sweepy échappe les esperluettes et transforme les sauts de ligne en retours à la ligne. `**bold**` s'affiche en gras, et les chevrons deviennent du texte brut. Sweepy stocke le playbook avec la session, et un rendu ultérieur le réutilise au lieu de celui qu'il a généré. Un nouveau sweep l'efface.

En mode `agent`, `render_report` refuse de construire un rapport mixte. Il renvoie une erreur qui liste les identifiants de postes non évalués. L'assistant lit cette liste et soumet des jugements pour les identifiants manquants. Les profils qui veulent des rapports par mots-clés seulement définissent `report.assessment: "keyword"`. Une exécution en ligne de commande signale aussi le chevauchement de mots-clés, puisqu'aucun agent ne fournit de jugements. Définissez `SWEEPY_REQUIRE_JUDGMENTS=1` quand le garde-fou doit s'appliquer à chaque profil et aussi à `export_report`.

Un sweep en direct scrape les sites pendant une minute ou plus. Le serveur MCP l'exécute en arrière-plan. `run_sweep` attend au plus 45 secondes puis renvoie `sweep_status: "running"` avec un `job_id`. Interrogez `get_sweep_status` jusqu'à ce qu'il signale `completed`. Le sweep continue de tourner si le client se déconnecte. Définissez `SWEEPY_MCP_WAIT_SECONDS` pour réduire l'attente sur les hôtes aux délais d'outil plus serrés.

- Les profils créés via MCP utilisent les moteurs intégrés ainsi que les moteurs optionnels installés qui réussissent leurs vérifications de configuration par défaut.
- Fournissez `sources_config` pour choisir les moteurs explicitement.
- OpenRoles a besoin d'un slug pour chaque entreprise.
- Apify nécessite un accord explicite, car il peut entraîner des frais.

L'assistant peut vérifier les résultats et combler les lacunes avec ses outils de recherche. Il doit confronter les sources ignorées et les annonces aux pages carrières des employeurs. Il doit ajouter les omissions vérifiées et étiqueter les annonces inaccessibles comme non vérifiées. Il doit signaler quand il ne peut pas confirmer une couverture complète.

Lisez [Intégration MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) pour les étapes de configuration.

Chaque outil MCP publie quatre indicateurs : lecture seule, destructif, idempotent et open-world. Les hôtes compatibles lisent ces indicateurs avant d'appeler l'outil.

## <a name="before-you-upload-your-resume"></a>Avant de téléverser votre CV

Votre mise en page décide de la quantité de texte que Sweepy peut lire. Une mise en page à deux colonnes, un tableau ou une page numérisée brouille le texte que le moteur lit et fait baisser vos scores. Une seule colonne propre de texte réel s'extrait le plus sûrement, et les systèmes de suivi des candidatures la lisent de la même façon.

Lisez [Conseils de mise en forme du CV](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) avant votre premier sweep.

## <a name="documentation"></a>Documentation

### <a name="getting-started"></a>Prise en main

- [Introduction](https://pvega62.github.io/software/docs/sweepy/intro)
- [Installation](https://pvega62.github.io/software/docs/sweepy/installation)
- [Configuration](https://pvega62.github.io/software/docs/sweepy/setup)
- [Lancer votre premier sweep](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [Comprendre vos résultats](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>CV et scores de correspondance

- [Conseils de mise en forme du CV](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [Scoring et limites](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>Référence des commandes et de la configuration

- [Commandes et indicateurs](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [Référence de configuration](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [Sources d'offres et plateformes](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [Intégration MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [Référence des outils MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [Référence développeur](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>Aspects juridiques et utilisation responsable

Sweepy scrape des sites d'offres publics et des API de sites d'offres. Le scraping peut enfreindre les conditions d'utilisation de certaines plateformes. Vérifiez ces conditions avant de vous fier à l'outil.

- Utilisez-le pour **votre recherche d'emploi personnelle**. Ne l'utilisez pas pour collecter en masse ou redistribuer.
- Respectez les limites de débit. Sweepy envoie un User-Agent courtois et un court délai entre les requêtes. Augmentez le délai avec la variable d'environnement `SWEEPY_SOURCE_DELAY`.
- Sweepy ne fournit pas de conseil juridique.

Le scraping passe par [`python-jobspy`](https://github.com/Bunsly/JobSpy) et, quand vous les installez, [`hirehunt`](https://pypi.org/project/hirehunt/), [`openroles`](https://pypi.org/project/openroles/), [`jobdrop`](https://pypi.org/project/jobdrop/) et [Apify](https://apify.com/). Chaque projet publie ses propres notes d'utilisation. Le scraping de Google Jobs, LinkedIn, Indeed et Glassdoor peut enfreindre les conditions d'utilisation de ces plateformes. Apify déplace la requête vers un service géré. Cela ne change pas le risque juridique.

## <a name="license"></a>Licence

Sweepy est publié sous la [Licence MIT](../LICENSE).
