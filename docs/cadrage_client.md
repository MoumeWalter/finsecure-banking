# Document de cadrage — FinSecure Banking

## 1. Présentation du client

**FinSecure Banking** est une banque de détail française fictive opérant sur le territoire métropolitain :

- 1,2 million de clients actifs
- 4,5 millions de transactions traitées par jour
- 142 agences physiques et une application mobile
- Un réseau de partenaires bancaires (Visa, Mastercard, agrégateurs DSP2)

Le présent projet est commandité par la **Direction des Systèmes d'Information** en partenariat avec la **Direction des Risques** et le **Pôle Conformité**.

## 2. Contexte et enjeux

### Existant

Le système d'information actuel souffre de plusieurs limites :

- **Données éclatées** : transactions stockées dans un système legacy SQLite côté agences, données KYC dans une base oubliée d'un ancien core banking, codes MCC dans des fichiers JSON envoyés mensuellement par les réseaux Visa/MC, labels de fraude maintenus à la main dans Excel par la cellule Risque.
- **Détection de fraude tardive** : aujourd'hui, la fraude est détectée à J+1 par des batchs nocturnes. Le manque à gagner annuel est estimé à **3,2 millions d'euros**.
- **Pas de reporting consolidé** : les équipes métier reconstruisent manuellement leurs indicateurs depuis des extracts CSV. Délai moyen de production d'un rapport : **5 jours ouvrés**.
- **Risque réglementaire** : non-conformité partielle aux exigences ACPR (traçabilité, auditabilité) et RGPD (durée de conservation, droit à l'oubli).

### Cible

Une plateforme data unifiée, sécurisée, industrialisée et auditée.

## 3. Objectifs du projet

### Objectifs métier

| ID | Objectif | KPI cible |
|---|---|---|
| O1 | Consolider toutes les sources transactionnelles dans une source de vérité | 100 % des sources intégrées |
| O2 | Détecter la fraude en temps quasi-réel | Latence de détection ≤ 5 s (P95) |
| O3 | Réduire le délai de production des rapports métier | ≤ 4 h pour un rapport agrégé |
| O4 | Garantir la conformité RGPD | 100 % des données sensibles chiffrées + traçabilité complète |
| O5 | Améliorer la précision du modèle de détection | AUC-PR > 0,80, Rappel > 80 % à FPR ≤ 1 % |

### Objectifs techniques

| ID | Objectif | KPI cible |
|---|---|---|
| T1 | Stockage scalable à 22 M lignes historiques + 4,5 M/jour | OK jusqu'à 100 M lignes |
| T2 | API REST exposant les datamarts | Disponibilité > 99 %, latence P95 < 500 ms |
| T3 | Pipeline reproductible et ordonnancé | DAG Airflow vert ≥ 99 % des runs |
| T4 | Couverture de tests | ≥ 70 % du code applicatif |
| T5 | CI/CD opérationnelle | Tests + build sur chaque PR, < 10 min |

## 4. Périmètre

### Inclus dans le projet

- Ingestion des 5 sources de données identifiées
- Modélisation Merise complète (MCD / MLD / MPD)
- Implémentation Oracle XE (DDL, vues, PL/SQL, partitionnement, sécurité)
- Implémentation MongoDB (modélisation documents, index, aggregation)
- Datalake médaillon Bronze / Silver / Gold en Parquet sur Hive
- API REST FastAPI avec authentification JWT
- Modèle ML supervisé de détection de fraude (3 algorithmes comparés)
- Pipeline streaming Kafka + Spark Streaming
- Orchestration Airflow
- Tests unitaires, d'intégration et qualité de données
- CI/CD GitHub Actions
- Documentation technique complète

### Exclus de la V1

- Déploiement cloud (AWS / Azure / GCP) — prévu en V2
- Application mobile cliente — hors périmètre
- Kubernetes — prévu en V2 (V1 reste sur Docker Compose)
- Modèles ML non-supervisés (clustering, anomaly detection avancée) — exploration future
- Intégration avec le SI agences en temps réel — V2

## 5. Sources de données

| Source | Format | Volumétrie | Description |
|---|---|---|---|
| `transactions_data.csv` | CSV | 22 M lignes | Transactions bancaires historiques |
| `users_data.csv` | CSV | 2 000 lignes | Données KYC clients |
| `cards_data.csv` | CSV | 6 146 lignes | Référentiel cartes bancaires |
| `mcc_codes.json` | JSON | 109 entrées | Libellés des catégories de marchands |
| `train_fraud_labels.json` | JSON | 8,9 M labels | Étiquettes Yes/No pour le ML |
| `legacy_db.sqlite` | SQLite | Extracts variés | Système historique des agences |

## 6. Acteurs et droits d'accès

| Rôle | Description | Périmètre d'accès |
|---|---|---|
| `role_admin` | Data Engineer / DBA | Lecture + écriture sur toutes les couches |
| `role_etl` | Compte technique pipeline | Lecture sources, écriture Bronze/Silver/Gold |
| `role_data_scientist` | Équipe modélisation ML | Lecture Silver/Gold, écriture artefacts ML |
| `role_analyst` | Risque / Conformité / Marketing | Lecture seule sur datamarts Gold |
| `role_audit` | Auditeurs internes et CAC | Lecture sur tables d'audit uniquement |

## 7. Contraintes

- **Sécurité** : chiffrement at-rest des données KYC, JWT pour l'API, secrets dans `.env` jamais commit
- **Réglementaire** : conformité RGPD (durée de conservation paramétrable, droit à l'oubli implémenté), traçabilité ACPR via tables d'audit
- **Performance** : 22 M lignes en ingestion < 30 min, scoring ML < 100 ms par transaction
- **Budget** : pas d'engagement cloud public en V1, infrastructure on-premise conteneurisée
- **Délais** : MVP en 4 mois (équivalent durée formation M2)

## 8. Livrables attendus

| Livrable | Description |
|---|---|
| Code source | Repository Git complet, structuré, testé |
| Documentation | Cadrage, architecture, veille techno, modèle de données |
| Schémas | MCD, MLD, MPD, architecture cible, DAG Airflow |
| Démo fonctionnelle | Stack Docker complète lançable en une commande |
| Rapport technique | Document final pour la soutenance certifiante |
| Présentation orale | Slides + démonstration en direct |

## 9. Indicateurs de réussite globaux du projet

- Tous les KPIs O1 à O5 et T1 à T5 atteints
- Toutes les compétences des Blocs 1 et 2 du RNCP36739 démontrables
- Stack reproductible chez n'importe quel évaluateur en moins de 15 minutes
- Documentation suffisante pour qu'un nouveau développeur soit autonome en 1 journée
