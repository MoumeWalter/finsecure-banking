# Modèle de données — FinSecure Banking

> Ce document décrit la modélisation complète de la base relationnelle Oracle XE
> du projet, en suivant la démarche Merise (MCD → MLD → MPD) et en justifiant chaque choix.

## Sommaire

1. [Démarche de modélisation](#1-démarche-de-modélisation)
2. [MCD — Modèle Conceptuel](#2-mcd--modèle-conceptuel-de-données)
3. [MLD — Modèle Logique](#3-mld--modèle-logique-de-données)
4. [MPD — Modèle Physique Oracle](#4-mpd--modèle-physique-oracle)
5. [Normalisation et choix de modélisation](#5-normalisation-et-choix-de-modélisation)
6. [Stratégie physique Oracle](#6-stratégie-physique-oracle)
7. [Dictionnaire de données](#7-dictionnaire-de-données)

---

## 1. Démarche de modélisation

Le modèle de données suit la démarche **Merise classique** en trois temps :

- **MCD** : représentation conceptuelle des entités métier et de leurs relations, indépendamment de toute technologie
- **MLD** : traduction du MCD en schéma relationnel normalisé (3NF), toujours indépendant du SGBD
- **MPD** : adaptation au SGBD cible (Oracle XE), avec types, contraintes physiques, index et partitionnement

Cette démarche garantit la séparation des préoccupations : le métier d'abord, la technique ensuite.

---

## 2. MCD — Modèle Conceptuel de Données

### Entités identifiées

Neuf entités sont identifiées, classées en trois catégories :

| Catégorie | Entités | Rôle |
|---|---|---|
| **Métier principal** | `CLIENT`, `CARTE` | Cœur du SI bancaire |
| **Référentiels et événements** | `MARCHAND`, `MCC`, `TRANSACTION`, `LABEL_FRAUDE`, `ERREUR_TRANSACTION` | Données de transactions et leur contexte |
| **Technique / audit** | `UTILISATEUR_SI`, `JOURNAL_AUDIT` | Traçabilité ACPR et RGPD |

### Relations et cardinalités

| Relation | Cardinalité côté A | Cardinalité côté B | Justification |
|---|---|---|---|
| CLIENT — possède — CARTE | (1,n) | (1,1) | Un client a au moins une carte ; une carte appartient à un seul client. |
| CARTE — effectue — TRANSACTION | (1,n) | (1,1) | Une carte active a au moins une transaction ; une transaction a une seule carte. |
| MARCHAND — accueille — TRANSACTION | (1,n) | (1,1) | Un marchand reçoit ≥1 transaction ; chaque transaction a un seul marchand. |
| MCC — classe — MARCHAND | (1,n) | (1,1) | Un MCC classe ≥1 marchand ; un marchand a une seule catégorie MCC. |
| TRANSACTION — est_labellisée — LABEL_FRAUDE | (1,1) | (0,1) | Toutes les transactions ne sont pas labellisées (jeu d'entraînement partiel). |
| TRANSACTION — génère — ERREUR_TRANSACTION | (1,n) | (0,n) | Une transaction peut générer 0 ou plusieurs erreurs (multi-valeurs). |
| UTILISATEUR_SI — trace — JOURNAL_AUDIT | (1,n) | (1,1) | Un utilisateur produit ≥1 entrée d'audit ; chaque entrée a un utilisateur. |

### Volumétries cibles

| Entité | Volumétrie |
|---|---|
| CLIENT | 2 000 |
| CARTE | 6 146 |
| MARCHAND | ~10 000 (déduit par DISTINCT) |
| MCC | 109 |
| TRANSACTION | 22 000 000 (puis +4,5 M/jour) |
| LABEL_FRAUDE | 8 900 000 |
| ERREUR_TRANSACTION | ~20 000 (~0,1 % des transactions) |
| UTILISATEUR_SI | ~20 |
| JOURNAL_AUDIT | volumétrie ouverte |

---

## 3. MLD — Modèle Logique de Données

### Règles de traduction MCD → MLD

Les règles classiques Merise ont été appliquées :

1. Chaque entité devient une table avec sa clé primaire
2. Chaque relation (1,n)—(1,1) devient une clé étrangère côté (1,1)
3. Aucune relation (n,m) dans ce schéma, donc pas de table d'association à créer
4. La relation (1,1)—(0,1) entre TRANSACTION et LABEL_FRAUDE est traduite par une clé primaire qui est aussi clé étrangère (PK_FK)

### Schéma relationnel résultant (en 3NF)

```
CLIENT(id_client, current_age, birth_year, birth_month, gender, address,
       latitude, longitude, per_capita_income, yearly_income, total_debt,
       credit_score, num_credit_cards)

CARTE(id_carte, #id_client, card_brand, card_type, card_number_enc,
      expires, cvv_enc, has_chip, num_cards_issued, credit_limit,
      acct_open_date, year_pin_last_changed, card_on_dark_web)

MCC(code_mcc, libelle_mcc)

MARCHAND(id_marchand, #code_mcc, merchant_city, merchant_state, zip)

TRANSACTION(id_transaction, #id_carte, #id_marchand, date_transaction,
            amount, use_chip, situation_date)

LABEL_FRAUDE(#id_transaction, is_fraud)
  -- PK = FK vers TRANSACTION

ERREUR_TRANSACTION(id_erreur, #id_transaction, code_erreur)

UTILISATEUR_SI(id_utilisateur, login, nom_complet, role, email, actif)

JOURNAL_AUDIT(id_audit, #id_utilisateur, table_concernee, id_ligne_concernee,
              operation, valeur_avant, valeur_apres, date_operation)
```

Légende : `#colonne` = clé étrangère.

---

## 4. MPD — Modèle Physique Oracle

### Choix de types Oracle

| Type Merise / logique | Type Oracle | Justification |
|---|---|---|
| Entier (clé) | `NUMBER(10)` | Capacité 10 chiffres = 10 Md de valeurs, largement suffisant |
| Entier (montant) | `NUMBER(12,2)` | Montant avec 2 décimales, max ~10 Md |
| Texte court (libellé) | `VARCHAR2(50)` à `VARCHAR2(255)` | Taille variable, économie d'espace |
| Texte chiffré (KYC) | `VARCHAR2(255)` | Chiffrement applicatif (AES-256), résultat base64 |
| Booléen | `CHAR(1)` avec CHECK | Oracle n'a pas de type booléen natif, convention `'Y'/'N'` |
| Date sans heure | `DATE` | Précision jour |
| Date avec heure | `TIMESTAMP(0)` | Précision seconde |

### Conventions de nommage

- Tables : `SINGULIER_MAJUSCULE` (ex. `CLIENT`, `TRANSACTION`)
- Colonnes : `snake_case_minuscule` (ex. `id_client`, `date_transaction`)
- Clés primaires : `pk_<table>` (ex. `pk_client`)
- Clés étrangères : `fk_<table>_<table_référencée>` (ex. `fk_carte_client`)
- Contraintes CHECK : `ck_<table>_<colonne>` (ex. `ck_carte_has_chip`)
- Contraintes UNIQUE : `uq_<table>_<colonnes>` (ex. `uq_utilisateur_login`)
- Index : `ix_<table>_<colonnes>` (ex. `ix_transaction_date`)
- Séquences : `seq_<table>` (ex. `seq_marchand`)
- Vues : `v_<nom>` (ex. `v_transactions_enrichies`)
- Vues matérialisées : `mv_<nom>` (ex. `mv_card_aggregates`)
- Procédures : `pr_<verbe>_<objet>` (ex. `pr_charger_marchands`)
- Fonctions : `fn_<verbe>_<objet>` (ex. `fn_calc_score_client`)
- Triggers : `tr_<table>_<événement>` (ex. `tr_client_audit`)
- Packages : `pkg_<domaine>` (ex. `pkg_datamart`)

---

## 5. Normalisation et choix de modélisation

### Vérification des formes normales

**1NF — Atomicité des attributs** ✅
- Toutes les colonnes contiennent des valeurs atomiques.
- Le champ `errors` brut (multi-valeurs) est **éclaté en table dédiée** `ERREUR_TRANSACTION`.

**2NF — Dépendance complète à la clé** ✅
- Toutes les clés primaires sont mono-colonne. Aucune dépendance partielle possible.

**3NF — Pas de dépendance transitive** ✅
- Aucun attribut non-clé ne dépend d'un autre attribut non-clé.
- Validation faite sur les cas potentiellement à risque : ville/zip du marchand → externalisés dans MARCHAND ; libellé MCC → externalisé dans MCC.

### Décisions de modélisation explicites

**Décision 1 — Table `ERREUR_TRANSACTION` dédiée**

*Alternative écartée* : garder une colonne texte `errors` dans TRANSACTION.

*Choix retenu* : table dédiée avec clé technique `id_erreur` et FK vers TRANSACTION.

*Justification* : conformité 1NF (un attribut atomique par cellule), possibilité d'agréger par code d'erreur, indexation possible sur `code_erreur` pour la cellule fraude.

**Décision 2 — Table `MARCHAND` dérivée par déduplication**

*Alternative écartée* : conserver `merchant_city`, `merchant_state`, `zip`, `code_mcc` directement dans TRANSACTION.

*Choix retenu* : table de dimension `MARCHAND` construite par `SELECT DISTINCT` sur les transactions à l'ingestion.

*Justification* : élimination de la redondance massive (10 000 marchands référencés 22 M fois), conformité 3NF, gain d'espace disque, cohérence référentielle (un changement d'adresse marchand = 1 UPDATE), démonstration de la compétence d'extraction de dimension à partir d'un fait.

**Décision 3 — Pas d'historisation SCD2 sur CLIENT**

*Alternative envisagée* : Slowly Changing Dimension Type 2 (clés techniques + dates de validité + flag `is_current`).

*Choix retenu* : table CLIENT simple (mise à jour en place).

*Justification* : le dataset ne contient pas d'historique multi-snapshots des clients, et l'âge est dérivable de `birth_year`. L'historisation est démontrée ailleurs (table TRANSACTION via `situation_date` + partitionnement RANGE). Le SCD2 reste une **évolution V2** documentée, triviale à ajouter grâce à la structure du PL/SQL.

**Décision 4 — Chiffrement applicatif des données KYC sensibles**

*Colonnes concernées* : `card_number`, `cvv`, `yearly_income`, `total_debt`, `per_capita_income`, `address`.

*Choix retenu* : chiffrement AES-256 côté application Python avant insertion (pas TDE Oracle, non disponible en XE).

*Justification* : conformité RGPD article 32 (sécurisation des données personnelles), conformité ACPR. Limitation acceptée : pas de recherche directe sur ces colonnes en clair.

**Décision 5 — `situation_date` matérialisée dans TRANSACTION**

*Alternative écartée* : calculer la date d'ingestion à la volée.

*Choix retenu* : colonne `situation_date` stockée, alimentée par le pipeline.

*Justification* : c'est la clé du **partitionnement RANGE par mois** en Phase 2. Sans cette colonne matérialisée, le partitionnement physique serait impossible.

---

## 6. Stratégie physique Oracle

### Partitionnement

Une seule table est partitionnée : `TRANSACTION`. Justification : c'est la seule à grosse volumétrie (22 M lignes + 4,5 M/jour).

**Type** : RANGE par mois sur `situation_date`
**Tablespace** : tablespace dédié `ts_transactions_<YYYY>` par année
**Maintenance** : ajout automatique des partitions futures via DBMS_SCHEDULER (Phase 2)

```sql
PARTITION BY RANGE (situation_date)
INTERVAL (NUMTOYMINTERVAL(1, 'MONTH'))
(
  PARTITION p_initial VALUES LESS THAN (TO_DATE('2024-01-01', 'YYYY-MM-DD'))
)
```

L'utilisation d'`INTERVAL` permet la création automatique des partitions au fur et à mesure des insertions. C'est une fonctionnalité Oracle moderne qui démontre la maîtrise du SGBD.

### Stratégie d'indexation

| Table | Type d'index | Colonne(s) | Justification |
|---|---|---|---|
| CARTE | B-tree | `id_client` (FK) | Jointures fréquentes client → cartes |
| MARCHAND | B-tree | `code_mcc` (FK) | Jointures avec MCC |
| TRANSACTION | B-tree | `id_carte` (FK) | Jointures avec CARTE (analyse par carte) |
| TRANSACTION | B-tree | `id_marchand` (FK) | Jointures avec MARCHAND |
| TRANSACTION | B-tree | `date_transaction` | Filtres temporels fréquents |
| TRANSACTION | composite | `(id_carte, situation_date)` | Requêtes datamart par carte sur une période |
| LABEL_FRAUDE | bitmap | `is_fraud` | Très faible cardinalité (Y/N), idéal bitmap |
| ERREUR_TRANSACTION | B-tree | `id_transaction` (FK) | Récupération erreurs d'une tx |
| ERREUR_TRANSACTION | B-tree | `code_erreur` | Agrégations par type d'erreur |
| JOURNAL_AUDIT | B-tree | `(table_concernee, date_operation)` | Recherche d'audit ciblée |

### Vues et vues matérialisées

Trois vues classiques pour simplifier l'écriture des requêtes utilisateurs :

- `v_transactions_enrichies` : jointure transactions + carte + client + marchand + MCC
- `v_clients_avec_cartes` : agrégat nombre de cartes / plafond total par client
- `v_marchands_par_volume` : top marchands par volume de transactions

Deux vues matérialisées pour les performances des datamarts (équivalent Gold dans Hive) :

- `mv_card_aggregates` : agrégats par carte (nb_transactions, montant_total, nb_fraudes)
- `mv_daily_aggregates` : agrégats par jour (mêmes métriques à l'échelle journalière)

Refresh : `REFRESH FAST ON DEMAND` (refresh incrémental, lancé par Airflow en Sprint 2).

### Sécurité et rôles

Cinq rôles applicatifs (cohérents avec le cadrage client) :

| Rôle | Tables / Vues accessibles | Droits |
|---|---|---|
| `role_admin` | Toutes | ALL (DBA) |
| `role_etl` | Toutes les tables métier | SELECT, INSERT, UPDATE, DELETE |
| `role_data_scientist` | Vues, vues matérialisées, TRANSACTION en lecture | SELECT |
| `role_analyst` | Vues matérialisées uniquement | SELECT |
| `role_audit` | JOURNAL_AUDIT, UTILISATEUR_SI | SELECT |

Schémas séparés :
- `FINSECURE` : tables et données métier
- `FINSECURE_AUDIT` : tables d'audit (séparation logique pour sécurité renforcée)

### Procédures, fonctions, triggers et packages

Anticipé pour la Phase 2, à titre indicatif :

**Package `pkg_datamart`** : encapsule la logique de calcul des datamarts.
- `pr_refresh_card_aggregates` : refresh de `mv_card_aggregates`
- `pr_refresh_daily_aggregates` : refresh de `mv_daily_aggregates`
- `fn_calc_fraud_ratio(p_id_carte)` : retourne le taux de fraude d'une carte

**Triggers d'audit** sur les tables sensibles :
- `tr_client_audit` : log toute modification sur CLIENT dans JOURNAL_AUDIT
- `tr_carte_audit` : idem sur CARTE

**Procédures d'ingestion** :
- `pr_charger_marchands` : déduplique les marchands depuis Bronze et insère dans MARCHAND
- `pr_charger_transactions` : insertion massive batch avec gestion d'erreurs

---

## 7. Dictionnaire de données

Voir le fichier dédié [`dictionnaire_donnees.md`](dictionnaire_donnees.md) pour la description colonne par colonne de toutes les tables.

---

## 8. Conformité aux exigences du Bloc 1 du RNCP36739

Cette modélisation démontre les compétences attendues du Bloc 1 :

| Compétence du Bloc 1 | Élément du présent document |
|---|---|
| Conception d'une BDR adaptée à un besoin client | Sections 1 à 4 (Merise, justification de chaque entité, rattachement explicite au cadrage) |
| Utilisation des technologies et langages adaptés | Section 4 (Oracle XE), section 6 (PL/SQL anticipé) |
| Modélisation conceptuelle, logique, physique | Sections 2, 3, 4 (la triplette Merise complète) |
| Normalisation et choix justifiés | Section 5 (vérification 3NF + 5 décisions explicites) |
| Stratégie d'indexation et de performance | Section 6 (index, partitionnement, vues matérialisées) |
| Sécurité et gouvernance | Section 6 (rôles, schémas, chiffrement KYC) |
