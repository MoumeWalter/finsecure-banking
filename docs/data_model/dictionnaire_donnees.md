# Dictionnaire de données — FinSecure Banking

> Description exhaustive de chaque colonne du modèle relationnel Oracle.
> Légende des contraintes : **PK** = primary key, **FK** = foreign key, **U** = unique, **NN** = not null, **CK** = check constraint.

## Sommaire

1. [CLIENT](#1-client)
2. [CARTE](#2-carte)
3. [MCC](#3-mcc)
4. [MARCHAND](#4-marchand)
5. [TRANSACTION](#5-transaction)
6. [LABEL_FRAUDE](#6-label_fraude)
7. [ERREUR_TRANSACTION](#7-erreur_transaction)
8. [UTILISATEUR_SI](#8-utilisateur_si)
9. [JOURNAL_AUDIT](#9-journal_audit)

---

## 1. CLIENT

Référentiel des titulaires de comptes bancaires (données KYC).

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_client` | NUMBER(10) | PK, NN | Identifiant unique du client | `users_data.csv` (id) |
| `current_age` | NUMBER(3) | NN, CK > 0 et < 130 | Âge actuel au moment de l'ingestion | `users_data.csv` |
| `retirement_age` | NUMBER(3) | CK > 0 et < 130 | Âge de retraite prévu | `users_data.csv` |
| `birth_year` | NUMBER(4) | NN, CK >= 1900 | Année de naissance | `users_data.csv` |
| `birth_month` | NUMBER(2) | CK BETWEEN 1 AND 12 | Mois de naissance | `users_data.csv` |
| `gender` | VARCHAR2(10) | CK IN ('Male','Female','Other') | Genre du client | `users_data.csv` |
| `address` | VARCHAR2(255) | — | Adresse postale (chiffrée AES-256) | `users_data.csv` *sensible* |
| `latitude` | NUMBER(8,5) | CK BETWEEN -90 AND 90 | Latitude géographique | `users_data.csv` |
| `longitude` | NUMBER(9,5) | CK BETWEEN -180 AND 180 | Longitude géographique | `users_data.csv` |
| `per_capita_income` | NUMBER(12,2) | CK >= 0 | Revenu par tête (chiffré) | `users_data.csv` *sensible* |
| `yearly_income` | NUMBER(12,2) | CK >= 0 | Revenu annuel (chiffré) | `users_data.csv` *sensible* |
| `total_debt` | NUMBER(12,2) | CK >= 0 | Dette totale (chiffrée) | `users_data.csv` *sensible* |
| `credit_score` | NUMBER(4) | CK BETWEEN 300 AND 850 | Score de crédit FICO | `users_data.csv` |
| `num_credit_cards` | NUMBER(3) | NN, CK >= 0 | Nombre de cartes possédées | `users_data.csv` |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Date de création de la ligne | technique |
| `date_modification` | TIMESTAMP(0) | — | Dernière modification | technique (trigger) |

**Volumétrie cible** : 2 000 lignes.

---

## 2. CARTE

Cartes bancaires émises aux clients.

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_carte` | NUMBER(10) | PK, NN | Identifiant unique de la carte | `cards_data.csv` (id) |
| `id_client` | NUMBER(10) | FK → CLIENT, NN | Référence vers le titulaire | `cards_data.csv` (client_id) |
| `card_brand` | VARCHAR2(20) | NN, CK IN ('Visa','Mastercard','Amex','Discover') | Marque du réseau bancaire | `cards_data.csv` |
| `card_type` | VARCHAR2(20) | NN, CK IN ('Credit','Debit','Debit Prepaid') | Type de carte | `cards_data.csv` |
| `card_number_enc` | VARCHAR2(255) | NN | Numéro PAN chiffré AES-256 | `cards_data.csv` *sensible* |
| `expires` | VARCHAR2(7) | NN | Date d'expiration au format MM/YYYY | `cards_data.csv` |
| `cvv_enc` | VARCHAR2(255) | NN | CVV chiffré AES-256 | `cards_data.csv` *sensible* |
| `has_chip` | CHAR(1) | NN, CK IN ('Y','N') | Carte à puce | `cards_data.csv` (YES/NO converti) |
| `num_cards_issued` | NUMBER(3) | CK >= 0 | Nombre d'émissions de cette carte | `cards_data.csv` |
| `credit_limit` | NUMBER(12,2) | CK >= 0 | Plafond de crédit en USD | `cards_data.csv` |
| `acct_open_date` | DATE | NN | Date d'ouverture du compte carte | `cards_data.csv` |
| `year_pin_last_changed` | NUMBER(4) | CK >= 1900 | Année du dernier changement de PIN | `cards_data.csv` |
| `card_on_dark_web` | CHAR(1) | NN, CK IN ('Y','N') | Carte signalée sur le dark web | `cards_data.csv` |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Création de la ligne | technique |
| `date_modification` | TIMESTAMP(0) | — | Dernière modification | technique |

**Volumétrie cible** : 6 146 lignes.

---

## 3. MCC

Référentiel des codes de catégories de marchands (norme ISO 18245).

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `code_mcc` | NUMBER(4) | PK, NN | Code MCC à 4 chiffres | `mcc_codes.json` (clé) |
| `libelle_mcc` | VARCHAR2(255) | NN, U | Libellé de la catégorie | `mcc_codes.json` (valeur) |

**Volumétrie cible** : 109 lignes.

Exemple : `5814 → "Fast Food Restaurants"`.

---

## 4. MARCHAND

Référentiel des marchands. **Table dérivée par déduplication depuis TRANSACTION à l'ingestion.**

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_marchand` | NUMBER(10) | PK, NN | Identifiant unique du marchand | `transactions_data.csv` (merchant_id) |
| `code_mcc` | NUMBER(4) | FK → MCC, NN | Catégorie MCC | `transactions_data.csv` (mcc) |
| `merchant_city` | VARCHAR2(100) | — | Ville du marchand | `transactions_data.csv` |
| `merchant_state` | VARCHAR2(50) | — | État (US) du marchand | `transactions_data.csv` |
| `zip` | VARCHAR2(10) | — | Code postal | `transactions_data.csv` |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Création de la ligne | technique |

**Volumétrie cible** : ~10 000 lignes (déduit par `SELECT DISTINCT merchant_id`).

---

## 5. TRANSACTION

Table de faits principale. Partitionnée par mois sur `situation_date`.

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_transaction` | NUMBER(12) | PK, NN | Identifiant unique de transaction | `transactions_data.csv` (id) |
| `id_carte` | NUMBER(10) | FK → CARTE, NN | Carte utilisée | `transactions_data.csv` (card_id) |
| `id_marchand` | NUMBER(10) | FK → MARCHAND, NN | Marchand bénéficiaire | `transactions_data.csv` (merchant_id) |
| `date_transaction` | TIMESTAMP(0) | NN | Date et heure de la transaction | `transactions_data.csv` (date) |
| `amount` | NUMBER(12,2) | NN | Montant en USD (toujours positif, refunds négatifs convertis) | `transactions_data.csv` (amount) |
| `use_chip` | VARCHAR2(30) | CK IN ('Swipe Transaction','Chip Transaction','Online Transaction') | Mode de paiement | `transactions_data.csv` |
| `situation_date` | DATE | NN | Date d'ingestion (clé de partitionnement) | technique |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Création de la ligne | technique |

**Volumétrie cible** : 22 000 000 lignes + 4,5 M / jour entrants.

**Partitionnement** : RANGE par mois sur `situation_date` avec INTERVAL automatique.

---

## 6. LABEL_FRAUDE

Annotations de fraude pour le ML supervisé. La clé primaire est également une clé étrangère vers TRANSACTION.

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_transaction` | NUMBER(12) | PK, FK → TRANSACTION, NN | Référence vers la transaction | `train_fraud_labels.json` (clé) |
| `is_fraud` | CHAR(1) | NN, CK IN ('Y','N') | Indicateur de fraude | `train_fraud_labels.json` (valeur) |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Date d'étiquetage | technique |

**Volumétrie cible** : 8 900 000 lignes (sous-ensemble de TRANSACTION).

**Note** : seules ~40 % des transactions sont labellisées (jeu d'entraînement).

---

## 7. ERREUR_TRANSACTION

Erreurs survenues pendant une transaction. **Table issue de l'éclatement de la colonne multi-valuée `errors`.**

| Colonne | Type Oracle | Contraintes | Description | Source |
|---|---|---|---|---|
| `id_erreur` | NUMBER(12) | PK, NN | Identifiant technique généré par séquence | `seq_erreur` |
| `id_transaction` | NUMBER(12) | FK → TRANSACTION, NN | Référence vers la transaction | `transactions_data.csv` |
| `code_erreur` | VARCHAR2(100) | NN | Libellé de l'erreur | `transactions_data.csv` (errors, éclaté) |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Création de la ligne | technique |

**Volumétrie cible** : ~20 000 lignes (~0,1 % des transactions ont des erreurs).

**Codes d'erreur observés dans le dataset** :
- `Bad PIN`
- `Insufficient Balance`
- `Technical Glitch`
- `Bad CVV`
- `Bad Card Number`
- `Bad Expiration`
- `Bad Zipcode`

---

## 8. UTILISATEUR_SI

Utilisateurs applicatifs du système data (pour l'audit RGPD et ACPR).

| Colonne | Type Oracle | Contraintes | Description |
|---|---|---|---|
| `id_utilisateur` | NUMBER(8) | PK, NN | Identifiant unique |
| `login` | VARCHAR2(50) | NN, U | Identifiant de connexion |
| `nom_complet` | VARCHAR2(150) | NN | Nom et prénom |
| `role` | VARCHAR2(30) | NN, CK IN ('admin','etl','data_scientist','analyst','audit') | Rôle applicatif |
| `email` | VARCHAR2(150) | NN, U | Email de contact |
| `actif` | CHAR(1) | NN, CK IN ('Y','N'), DEFAULT 'Y' | Compte actif |
| `date_creation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Création du compte |
| `date_derniere_connexion` | TIMESTAMP(0) | — | Dernière connexion |

**Volumétrie cible** : ~20 lignes.

---

## 9. JOURNAL_AUDIT

Trace toutes les modifications sur les tables sensibles (CLIENT, CARTE, UTILISATEUR_SI). Alimentée automatiquement par des triggers.

| Colonne | Type Oracle | Contraintes | Description |
|---|---|---|---|
| `id_audit` | NUMBER(15) | PK, NN | Identifiant technique généré par séquence |
| `id_utilisateur` | NUMBER(8) | FK → UTILISATEUR_SI, NN | Utilisateur ayant effectué l'opération |
| `table_concernee` | VARCHAR2(50) | NN | Nom de la table modifiée |
| `id_ligne_concernee` | NUMBER(12) | NN | Clé primaire de la ligne modifiée |
| `operation` | VARCHAR2(10) | NN, CK IN ('INSERT','UPDATE','DELETE') | Type d'opération |
| `valeur_avant` | CLOB | — | Valeurs avant modification (JSON) |
| `valeur_apres` | CLOB | — | Valeurs après modification (JSON) |
| `date_operation` | TIMESTAMP(0) | NN, DEFAULT SYSTIMESTAMP | Horodatage de l'opération |
| `adresse_ip` | VARCHAR2(45) | — | IP source (IPv4 ou IPv6) |

**Volumétrie cible** : volumétrie ouverte, prévoir partitionnement futur si > 10 M lignes.

---

## Récapitulatif des contraintes globales

### Clés primaires (PK)

| Table | Clé primaire |
|---|---|
| CLIENT | `id_client` |
| CARTE | `id_carte` |
| MCC | `code_mcc` |
| MARCHAND | `id_marchand` |
| TRANSACTION | `id_transaction` |
| LABEL_FRAUDE | `id_transaction` (aussi FK) |
| ERREUR_TRANSACTION | `id_erreur` |
| UTILISATEUR_SI | `id_utilisateur` |
| JOURNAL_AUDIT | `id_audit` |

### Clés étrangères (FK)

| Table source | Colonne | Table cible | Colonne cible | Action ON DELETE |
|---|---|---|---|---|
| CARTE | `id_client` | CLIENT | `id_client` | RESTRICT |
| MARCHAND | `code_mcc` | MCC | `code_mcc` | RESTRICT |
| TRANSACTION | `id_carte` | CARTE | `id_carte` | RESTRICT |
| TRANSACTION | `id_marchand` | MARCHAND | `id_marchand` | RESTRICT |
| LABEL_FRAUDE | `id_transaction` | TRANSACTION | `id_transaction` | CASCADE |
| ERREUR_TRANSACTION | `id_transaction` | TRANSACTION | `id_transaction` | CASCADE |
| JOURNAL_AUDIT | `id_utilisateur` | UTILISATEUR_SI | `id_utilisateur` | RESTRICT |

**Justification ON DELETE** :
- `RESTRICT` (par défaut) sur les références métier : on n'efface pas un client tant qu'il a des cartes, pour préserver l'intégrité.
- `CASCADE` sur les enfants de TRANSACTION : si une transaction est supprimée (purge RGPD par exemple), ses labels et erreurs associés sont également supprimés.

### Séquences à créer

| Séquence | Pour table | Start | Increment |
|---|---|---|---|
| `seq_marchand` | MARCHAND | 1 | 1 |
| `seq_erreur` | ERREUR_TRANSACTION | 1 | 1 |
| `seq_utilisateur` | UTILISATEUR_SI | 1 | 1 |
| `seq_audit` | JOURNAL_AUDIT | 1 | 1 |

Les autres IDs (`id_client`, `id_carte`, `id_transaction`) viennent directement des sources et ne nécessitent pas de séquence.
