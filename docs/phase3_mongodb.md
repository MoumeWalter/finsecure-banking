# Phase 3 — MongoDB (Bloc 1, brique NoSQL)

> Cette phase complète le Bloc 1 du RNCP36739 en ajoutant la **brique NoSQL** à la plateforme.

## Sommaire

1. [Pourquoi MongoDB dans cette architecture](#1-pourquoi-mongodb)
2. [Modélisation : documents auto-portants](#2-modélisation)
3. [Pipeline de migration Oracle → MongoDB](#3-pipeline-de-migration)
4. [Stratégie d'indexation](#4-stratégie-dindexation)
5. [Aggregation pipelines vs vues matérialisées Oracle](#5-aggregation-pipelines)
6. [Démos pour la soutenance](#6-démos-pour-la-soutenance)

---

## 1. Pourquoi MongoDB

### 1.1 Contexte

Oracle XE est la **source de vérité** : intégrité référentielle stricte, contraintes métier fortes, transactions ACID, audit ACPR. C'est parfait pour le système d'information opérationnel.

Mais deux familles d'usages ne sont pas optimales en relationnel :

- **Usages analytiques** : data scientists, analystes risque/marketing veulent récupérer une transaction avec **tout son contexte** (carte, client, marchand, MCC, label) en un seul appel. En SQL, ça veut dire 5 jointures à chaque requête.
- **Usages ML** : le scoring de fraude temps réel doit être < 100 ms. Une requête multi-jointures sur 13M de lignes est trop lente, même avec index.

D'où le **polyglot persistence** : Oracle pour le transactionnel, MongoDB pour l'analytique et le ML.

### 1.2 Pourquoi MongoDB plutôt qu'une autre NoSQL ?

Voir [`docs/veille_technologique.md`](veille_technologique.md) section "Base de données NoSQL".

Résumé :

| Critère | MongoDB ✅ | Cassandra | Elasticsearch |
|---|---|---|---|
| Modèle adapté à notre cas | Document → idéal pour transaction enrichie | Wide-column, surdimensionné | Document indexé, mais orienté search |
| Aggregation framework | Très riche (`$lookup`, `$facet`, `$bucket`) | CQL limité, pas de JOIN | DSL puissant mais complexe |
| Schema flexibility | Native, sans migration | Schema declared | Native via mapping |
| Connector PySpark | Officiel et mature | Bon | Bon |
| Adoption France | Standard de fait NoSQL document | Plus rare | Limité à la recherche |
| Courbe d'apprentissage | Faible | Élevée | Moyenne |

---

## 2. Modélisation

### 2.1 Stratégie : documents auto-portants (denormalized embedding)

Chaque document MongoDB embarque la transaction et **tout son contexte**. Pas de référence cross-collection. C'est le pattern idiomatique de MongoDB.

Exemple simplifié de document :

```json
{
  "_id": ObjectId("..."),
  "id_transaction": 12345,
  "date_transaction": ISODate("2026-05-25T14:30:00Z"),
  "amount": 42.50,
  "use_chip": "Online Transaction",
  "situation_date": ISODate("2026-05-25"),
  "carte": {
    "id_carte": 4938,
    "card_brand": "Visa",
    "card_type": "Credit",
    "has_chip": true,
    "credit_limit": 5000.0,
    "card_on_dark_web": false
  },
  "client": {
    "id_client": 1178,
    "current_age": 59,
    "gender": "Female",
    "credit_score": 720,
    "num_credit_cards": 3
  },
  "marchand": {
    "id_marchand": 2503,
    "ville": "Paris",
    "etat": "Ile-de-France",
    "zip": "75001"
  },
  "mcc": {
    "code": 5814,
    "libelle": "Fast Food Restaurants"
  },
  "fraude": {
    "is_fraud": false,
    "labelled": true
  },
  "_ingested_at": ISODate("2026-05-26T10:00:00Z")
}
```

### 2.2 Justification du choix

| Aspect | Embedding (choix) | Référencement (écarté) |
|---|---|---|
| Lecture | 1 disk seek | N disk seeks (N = nombre de collections jointes) |
| Cohérence | Snapshot au moment de l'ingestion (lecture cohérente) | Référence vivante (peut diverger) |
| Schema | Flexible, évolutif | Plus rigide |
| Espace disque | +30 % de redondance | Optimal |
| ML temps réel | ✅ idéal | ❌ trop lent |

**Trade-off accepté** : redondance des libellés MCC et infos marchand dans chaque document. Compensée par la performance lecture et la clarté.

### 2.3 Sécurité et RGPD

**Choix volontaire** : les colonnes chiffrées d'Oracle (`yearly_income`, `total_debt`, `address`, `card_number_enc`, `cvv_enc`) **ne sont PAS ramenées** dans MongoDB.

Justification :
- **Principe de minimisation des données** (RGPD article 5.1.c)
- MongoDB sert l'analytique, pas le KYC
- Les analystes n'ont pas besoin du PAN ni du revenu détaillé
- Évite un risque de fuite par exfiltration MongoDB

Seules les données pseudonymisées (id_client) et les attributs non sensibles (current_age, gender, credit_score) traversent vers MongoDB.

---

## 3. Pipeline de migration

### 3.1 Architecture

```
Oracle XE                MongoDB
   │                        │
   │   SELECT + JOIN        │   insert_many()
   │   (vue dénormalisée)   │   (batchs de 5000)
   │                        │
   ▼                        ▼
   ├── transaction          │
   ├── carte           ──→  └── transactions_enriched
   ├── client                    (collection unique)
   ├── marchand
   ├── mcc
   └── label_fraude
```

### 3.2 Flux Python (`src/migration/load_mongo.py`)

1. Connexion Oracle (oracledb thin) + MongoDB (pymongo)
2. Requête SELECT avec 4 INNER JOIN + 1 LEFT JOIN (vue assemblée)
3. Curseur Oracle server-side avec `arraysize = 5000` (lecture par paquets)
4. Pour chaque ligne : construction du document JSON imbriqué
5. Batchs de 5 000 documents → `insert_many(ordered=False)`
6. Progress bar `tqdm`
7. Logs structurés + bilan final

### 3.3 Performances mesurées (échantillon 100k)

- Lecture Oracle : ~5 000 lignes/sec via curseur
- Insertion MongoDB : ~50 000 doc/sec en mode batch unordered
- **Goulot d'étranglement** : Oracle (jointures + chiffrement non requis ralentit)
- Durée typique : **~3 minutes pour 100 000 transactions**

### 3.4 Estimations volumétrie complète

| Volume | Durée estimée | Taille MongoDB | RAM |
|---|---|---|---|
| 100k | 3 min | ~150 Mo | 500 Mo |
| 1M | 30 min | ~1,5 Go | 1 Go |
| 13M | ~6 h | ~20 Go | 2 Go |

---

## 4. Stratégie d'indexation

Voir [`mongo/01_create_indexes.js`](../mongo/01_create_indexes.js) pour le script complet.

8 index créés :

| Index | Type | Cas d'usage | Justification |
|---|---|---|---|
| `ux_id_transaction` | UNIQUE | Lookup ponctuel | Unicité métier |
| `ix_carte_id` | Simple | Filtre par carte | Cas d'usage analyste |
| `ix_client_id` | Simple | Filtre par client | Cas d'usage support |
| `ix_date_desc` | Simple DESC | Historique temporel | Tri par date |
| `ix_fraude_partial` | Partial | Filtre `is_fraud=true` | Compact car ~0,1 % seulement |
| `ix_client_date` | Composite | Transactions d'un client triées | Pattern fréquent |
| `ix_mcc_code` | Simple | Agrégations par catégorie | Datamart marketing |
| `ttl_archivage_2ans` | TTL | Purge automatique RGPD | Conformité durée de conservation |

### Point fort à mentionner au jury : le TTL

L'index TTL `ttl_archivage_2ans` configure MongoDB pour **supprimer automatiquement** les documents 2 ans après leur insertion. Aucune intervention humaine n'est nécessaire.

C'est la **conformité RGPD article 5.1.e** (durée de conservation) implémentée au niveau du stockage. Très valorisé.

### Index Partial : économie d'espace

L'index `ix_fraude_partial` n'indexe **que les documents frauduleux** (`partialFilterExpression`). Sur 100 000 docs avec ~100 fraudes, l'index pèse 100x moins qu'un index complet. C'est la même logique que les index bitmap d'Oracle, mais en plus économe.

---

## 5. Aggregation pipelines

Voir [`mongo/02_aggregation_pipelines.js`](../mongo/02_aggregation_pipelines.js) pour les pipelines complets.

### Équivalence Oracle ↔ MongoDB

| Oracle (Phase 2) | MongoDB (Phase 3) | Pattern utilisé |
|---|---|---|
| `mv_card_aggregates` (vue matérialisée) | `v_card_aggregates` (vue) | `$group` + `$project` |
| `mv_daily_aggregates` | `v_daily_aggregates` | `$group` par `situation_date` |
| `mv_mcc_aggregates` | `v_mcc_aggregates` | `$group` avec `$addToSet` pour le distinct |

### Différence pédagogique notable

- **Oracle vue matérialisée** : résultat stocké physiquement, refresh manuel ou automatique
- **MongoDB vue** : recalculée à la volée à chaque requête

**Quand matérialiser en MongoDB ?** Utiliser `$merge` ou `$out` à la fin d'un pipeline pour persister le résultat dans une collection. Faisable mais pas nécessaire ici vu la volumétrie de 100k.

### Aggregation avancée : `$facet` pour les dashboards

Le script `03_demos_soutenance.js` démontre `$facet` qui permet d'exécuter **plusieurs aggregations en parallèle dans une seule requête**. C'est extrêmement puissant pour les tableaux de bord.

Exemple : "Combien de fraudes par genre ET par tranche d'âge ET par type de paiement", en une seule requête.

---

## 6. Démos pour la soutenance

Voir [`mongo/03_demos_soutenance.js`](../mongo/03_demos_soutenance.js).

6 démos prêtes à dérouler en direct :

1. **Visualisation d'un document enrichi** : montrer la richesse en un seul appel
2. **Bilan global** : compte total, taux de fraude, distincts
3. **Top 10 catégories marchands** : via la vue
4. **Top 10 cartes à risque** : via la vue + tri par taux de fraude
5. **`$facet` multi-aggregation** : démonstration de la puissance pipeline
6. **`explain()` avec index** : preuve de l'utilisation des index MongoDB

### Storytelling pour le jury

> "J'ai implémenté MongoDB en complément d'Oracle pour deux raisons. Premièrement, les analystes et le futur modèle ML ont besoin de transactions auto-portantes pour des accès en moins de 100 ms : MongoDB offre un disk seek unique grâce à l'embedding. Deuxièmement, j'ai appliqué le principe de minimisation des données RGPD en ne ramenant aucune donnée chiffrée vers MongoDB — seules les données pseudonymisées et non sensibles y figurent. Cela démontre la cohérence sécurité de bout en bout de l'architecture."

---

## Conformité au Bloc 1

Cette phase complète la couverture du Bloc 1 — compétence "BDR non-relationnelle" :

> *"Concevoir et développer une base de données non-relationnelle en vue de la mise à disposition des données semi-structurées et non-structurées pour un traitement analytique ou d'intelligence artificielle tout en utilisant les technologies et les langages de requêtes adaptés"*

| Exigence | Démonstration |
|---|---|
| BDD non-relationnelle | MongoDB 7.0 (document store) |
| Données semi-structurées | Documents JSON imbriqués (carte, client, marchand, mcc, fraude embedded) |
| Adaptée à un traitement analytique/IA | Choix d'embedding justifié par les usages, aggregation pipelines, TTL |
| Langage de requêtes adapté | MongoDB Query Language + Aggregation Framework + mongosh |
| Conformité RGPD | TTL d'archivage automatique + minimisation des données sensibles |
