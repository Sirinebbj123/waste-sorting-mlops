# 0004 · Monitoring avec Prometheus et Grafana

- Date : 2026-11-05
- Statut : accepté
- Autrice : Syrine

## Contexte

L'API tourne dans Docker (tâche 8) et chaque version est testée par la CI (tâche 9).
Mais une fois lancée, on ne sait pas ce qu'elle fait : combien de photos, en combien de
temps, avec quelles erreurs, et surtout si le **modèle** se comporte toujours bien
(une baisse de confiance peut vouloir dire que les photos ne ressemblent plus aux
données d'entraînement : c'est la *dérive*).

## Décision

- **L'API expose `/metrics`** au format Prometheus, avec la bibliothèque officielle
  `prometheus-client` (version figée) :
  - fonctionnement : `ecotri_requetes_total` (méthode, route, code), `ecotri_duree_requete_secondes` ;
  - métier et modèle : `ecotri_predictions_total` (mode), `ecotri_dechets_total` (matière, poubelle),
    `ecotri_confiance_matiere`, `ecotri_duree_inference_secondes`, `ecotri_modele_info`
    (fichiers et md5 DVC des modèles en service).
- **Prometheus** (`prom/prometheus:v3.5.0`) lit `/metrics` toutes les 5 secondes,
  garde 7 jours d'historique et évalue 4 règles d'alerte (`monitoring/prometheus/alertes.yml`) :
  API injoignable, prédictions lentes, confiance du modèle en baisse, trop d'erreurs 5xx.
- **Grafana** (`grafana/grafana:12.2.0`) affiche le tableau de bord « EcoTri · Tri des déchets ».
  La source de données et le tableau de bord sont **provisionnés** (fichiers dans
  `monitoring/grafana/`) : rien à configurer à la main, le même tableau de bord chez tout le monde.
- Les trois services démarrent ensemble avec `docker compose up --build -d`.

## Pourquoi ces choix

- **Prometheus + Grafana** : le duo standard, gratuit, qui tourne en local dans Docker.
- **`prometheus-client` plutôt qu'une bibliothèque toute faite** : peu de code, et on choisit
  nous-mêmes des métriques utiles pour le tri (bacs, matières, confiance).
- **Étiquette `route` = le modèle de route** (`/predict`, `/static`) et pas l'adresse complète :
  le nombre de séries reste petit.
- **Tableau de bord en JSON dans Git** : il est versionné et relu en PR comme le code.
- **Ports 9090 et 3000 limités à `127.0.0.1`**, Grafana en lecture seule sans connexion,
  mot de passe admin par variable d'environnement (`GRAFANA_PASSWORD`, jamais dans Git).

## Conséquences

- Les compteurs repartent de zéro quand l'API redémarre ; Prometheus garde l'historique
  (volume `prometheus-data`), et les graphiques utilisent `rate()` qui gère ces remises à zéro.
- Les alertes sont visibles dans Prometheus (onglet *Alerts*) mais ne sont envoyées nulle part
  (pas d'Alertmanager) : suffisant pour le projet, à ajouter pour une vraie mise en production.
- `docker compose up` télécharge deux images de plus (environ 330 Mo compressés).