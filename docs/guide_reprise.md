# Guide de reprise — Pour la prochaine session

> À lire avant de reprendre le projet, pour repartir immédiatement.

## État actuel du projet (fin Phase 3)

### Ce qui marche

- ✅ **Oracle XE** : 22,5 M objets, partitionnement, chiffrement AES-256, audit ACPR
- ✅ **MongoDB** : 100k documents enrichis, 8 index dont TTL, 3 vues d'aggregation
- ✅ **Compass** connecté et fonctionnel
- ✅ **Documentation** : rapport technique, récap pédagogique, README opérationnel
- ✅ **Git** : tout poussé sur https://github.com/MoumeWalter/finsecure-banking

### Ce qui reste sur la to-do

Voir [`roadmap.md`](roadmap.md) pour la liste complète. Les prochaines phases dans l'ordre recommandé :

1. **Phase 5 — Conteneurisation Docker Compose** (recommandée pour la suite) — ~2-3h
2. **Phase 11 — API FastAPI enrichie** — ~4-5h
3. **Phase 6 — Streaming Kafka** — ~3-4h
4. **Phase 7 — Orchestration Airflow** — ~3h
5. **Phase 8 — Tests Pytest** — ~3h
6. **Phase 9 — CI/CD GitHub Actions** — ~2h
7. **Phase 10 — ML enrichi avec MLflow** — ~4h
8. **Phase 12 — Observabilité Prometheus/Grafana** — ~2h
9. **Phase 13 — Documentation finale et slides** — ~3h

## Pourquoi Phase 5 (Docker Compose) en priorité ?

Cette phase est **structurante** : tout le Sprint 2 en dépend.

Bénéfices :
- Un seul `docker compose up -d` démarre Oracle + MongoDB + (futur) Kafka + Airflow + FastAPI + Spark
- Networking automatique entre services
- Volumes persistants déclaratifs
- Healthchecks
- Variables d'environnement centralisées
- **Reproductibilité immédiate** chez tout évaluateur

Argument soutenance : "L'évaluateur peut faire `git clone && docker compose up && python -m src.migration.load_oracle --all && python -m src.migration.load_mongo --limit 1000000` et avoir l'intégralité de la stack."

## Avant de reprendre — Vérification rapide

Quand tu reviendras, lance ces 3 commandes dans l'ordre :

```powershell
# 1. Conteneurs Docker
docker ps
# Attendu : oracle_db (healthy) + mongo_db (Up)

# 2. Activer le venv
cd C:\Users\walte\Downloads\finsecure-banking
.\.venv\Scripts\Activate.ps1
# Attendu : (.venv) à gauche du prompt

# 3. Tester les connexions
python -c "from dotenv import load_dotenv; load_dotenv(); from src.migration.load_oracle import get_connection; get_connection(); print('Oracle OK')"
python -c "from dotenv import load_dotenv; load_dotenv(); from src.migration.load_mongo import get_mongo_client; get_mongo_client(); print('MongoDB OK')"
```

Si les 3 retournent OK, tu peux enchaîner.

## Optionnel : Tester l'optimisation de load_mongo.py

Avant d'attaquer la Phase 5, tu peux tester si l'optimisation Oracle accélère vraiment. Lance :

```powershell
python -m src.migration.load_mongo --limit 100000 --drop
```

Attendu : **3-10 minutes** au lieu des 40 minutes initiales. Si ça marche bien, tu peux ensuite monter à 1M :

```powershell
python -m src.migration.load_mongo --limit 1000000 --drop
```

Estimation : **30-90 minutes** pour 1M.

⚠️ Si la performance n'est pas meilleure, **ne perds pas de temps** à diagnostiquer. Reste sur 100k, ça suffit largement pour la soutenance. On a démontré tout ce qu'il faut.

## Si Docker a redémarré

Les conteneurs Oracle et MongoDB sont persistants (volumes Docker), donc ils survivent à un reboot. Mais ils peuvent être arrêtés :

```powershell
docker ps -a
# Si "Exited" ou rien :
docker start oracle_db
docker start mongo_db
# Attendre 30s à 2 min pour Oracle (le plus lent)
docker ps
```

## Documents clés à relire

| Document | Quand le relire |
|---|---|
| [`rapport_technique.md`](rapport_technique.md) | Avant la soutenance |
| [`recap_pedagogique.md`](recap_pedagogique.md) | Pour préparer le storytelling |
| [`phase3_mongodb.md`](phase3_mongodb.md) | Pour la partie NoSQL |
| [`README.md`](../README.md) | Pour rappel des commandes |

## Compte rendu — Ce qui sera à mettre à jour

Quand toutes les phases seront terminées :

- Section "Architecture" : ajouter MongoDB
- Section "Sécurité" : ajouter TTL MongoDB + minimisation données
- Section "Résultats" : ajouter chiffres MongoDB
- Section "Difficultés rencontrées" : ajouter la perf Oracle→Mongo
- Nouvelles sections : Docker Compose, Airflow, ML, etc. au fur et à mesure

---

**Bon courage pour la suite !** Tu as déjà couvert 100 % du Bloc 1 et tu attaques le Bloc 2.
