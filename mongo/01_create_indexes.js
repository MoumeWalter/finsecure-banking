// =============================================================================
// 01_create_indexes.js
// =============================================================================
// Strategie d'indexation MongoDB selon les patterns d'acces previs :
//   - Lookup par id_transaction (unique)
//   - Filtrage par client / carte
//   - Recherche temporelle (situation_date)
//   - Filtrage par fraude
//   - TTL pour archivage automatique
//
// Execution :
//   docker exec mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin" /tmp/mongo/01_create_indexes.js
// =============================================================================

use('finsecure');

print("=== Creation des index sur transactions_enriched ===");

// -----------------------------------------------------------------------------
// 1. Index unique sur id_transaction
// -----------------------------------------------------------------------------
// Garantit l'unicite metier (pas de doublon de transaction)
db.transactions_enriched.createIndex(
  { id_transaction: 1 },
  { unique: true, name: "ux_id_transaction" }
);
print("OK ux_id_transaction (UNIQUE)");

// -----------------------------------------------------------------------------
// 2. Index sur carte.id_carte (acces frequent par carte)
// -----------------------------------------------------------------------------
db.transactions_enriched.createIndex(
  { "carte.id_carte": 1 },
  { name: "ix_carte_id" }
);
print("OK ix_carte_id");

// -----------------------------------------------------------------------------
// 3. Index sur client.id_client (acces frequent par client)
// -----------------------------------------------------------------------------
db.transactions_enriched.createIndex(
  { "client.id_client": 1 },
  { name: "ix_client_id" }
);
print("OK ix_client_id");

// -----------------------------------------------------------------------------
// 4. Index sur date_transaction (filtres temporels)
// -----------------------------------------------------------------------------
db.transactions_enriched.createIndex(
  { date_transaction: -1 },
  { name: "ix_date_desc" }
);
print("OK ix_date_desc");

// -----------------------------------------------------------------------------
// 5. Index sur fraude.is_fraud (filtre booleen)
// -----------------------------------------------------------------------------
// Partial index : seulement les transactions reellement frauduleuses
// Beaucoup plus compact qu'un index complet (utile car ~0.1% sont frauduleuses)
db.transactions_enriched.createIndex(
  { "fraude.is_fraud": 1 },
  {
    name: "ix_fraude_partial",
    partialFilterExpression: { "fraude.is_fraud": true }
  }
);
print("OK ix_fraude_partial (partial sur is_fraud=true)");

// -----------------------------------------------------------------------------
// 6. Index compose : (client.id_client, date_transaction)
// -----------------------------------------------------------------------------
// Patterns : "toutes les transactions d'un client triees par date"
db.transactions_enriched.createIndex(
  { "client.id_client": 1, date_transaction: -1 },
  { name: "ix_client_date" }
);
print("OK ix_client_date (composite)");

// -----------------------------------------------------------------------------
// 7. Index sur mcc.code (agregations par categorie)
// -----------------------------------------------------------------------------
db.transactions_enriched.createIndex(
  { "mcc.code": 1 },
  { name: "ix_mcc_code" }
);
print("OK ix_mcc_code");

// -----------------------------------------------------------------------------
// 8. Index TTL sur _ingested_at (archivage automatique)
// -----------------------------------------------------------------------------
// MongoDB supprime automatiquement les documents apres N secondes.
// Ici on met 2 ans (730 jours) pour la conformite RGPD.
// MongoDB scrute toutes les 60 secondes et purge les documents expires.
db.transactions_enriched.createIndex(
  { _ingested_at: 1 },
  {
    name: "ttl_archivage_2ans",
    expireAfterSeconds: 60 * 60 * 24 * 730  // 2 ans
  }
);
print("OK ttl_archivage_2ans (purge automatique RGPD apres 2 ans)");

// -----------------------------------------------------------------------------
// Bilan
// -----------------------------------------------------------------------------
print("\n=== Bilan des index crees ===");
db.transactions_enriched.getIndexes().forEach((idx) => {
  print(`  - ${idx.name} : ${JSON.stringify(idx.key)}`);
});

print("\n=== Statistiques collection ===");
const stats = db.transactions_enriched.stats();
print(`  - Documents : ${stats.count}`);
print(`  - Taille moyenne par document : ${(stats.avgObjSize || 0).toFixed(0)} bytes`);
print(`  - Taille totale : ${((stats.size || 0) / 1024 / 1024).toFixed(2)} MB`);
print(`  - Nombre d'index : ${stats.nindexes}`);
print(`  - Taille des index : ${((stats.totalIndexSize || 0) / 1024 / 1024).toFixed(2)} MB`);
