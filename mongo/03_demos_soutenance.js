// =============================================================================
// 03_demos_soutenance.js
// =============================================================================
// Requetes pretes a executer pour la soutenance.
// Demontre la puissance de MongoDB : documents auto-portants, aggregations
// puissantes, indexation flexible.
//
// Execution :
//   docker exec mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin" /tmp/mongo/03_demos_soutenance.js
// =============================================================================

use('finsecure');

print("=" .repeat(78));
print("DEMO MONGODB - FinSecure Banking");
print("=" .repeat(78));

// -----------------------------------------------------------------------------
// DEMO 1 : Un document enrichi (visualisation)
// -----------------------------------------------------------------------------
print("\n[DEMO 1] Visualisation d'un document enrichi");
print("(Une transaction = tout son contexte en un seul appel)");
printjson(db.transactions_enriched.findOne({ "fraude.is_fraud": true }));

// -----------------------------------------------------------------------------
// DEMO 2 : Bilan global de la collection
// -----------------------------------------------------------------------------
print("\n[DEMO 2] Bilan global");
const total = db.transactions_enriched.countDocuments();
const fraudes = db.transactions_enriched.countDocuments({ "fraude.is_fraud": true });
const cartes = db.transactions_enriched.distinct("carte.id_carte").length;
const clients = db.transactions_enriched.distinct("client.id_client").length;
const marchands = db.transactions_enriched.distinct("marchand.id_marchand").length;
print(`  Documents totaux       : ${total}`);
print(`  Transactions frauduleuses : ${fraudes} (${(100*fraudes/total).toFixed(3)}%)`);
print(`  Cartes distinctes      : ${cartes}`);
print(`  Clients distincts      : ${clients}`);
print(`  Marchands distincts    : ${marchands}`);

// -----------------------------------------------------------------------------
// DEMO 3 : Top 10 categories marchands (via la vue)
// -----------------------------------------------------------------------------
print("\n[DEMO 3] Top 10 categories marchands (via la vue v_mcc_aggregates)");
db.v_mcc_aggregates
  .find({}, { _id: 0 })
  .limit(10)
  .forEach((doc) => {
    print(`  ${doc.libelle_mcc.padEnd(40)} | ${String(doc.nb_transactions).padStart(8)} tx | ${doc.total_amount.toFixed(2).padStart(15)} $`);
  });

// -----------------------------------------------------------------------------
// DEMO 4 : Top 10 cartes a risque
// -----------------------------------------------------------------------------
print("\n[DEMO 4] Top 10 cartes a risque (taux de fraude le plus eleve, min 100 tx)");
db.v_card_aggregates
  .find({ nb_transactions: { $gte: 100 } }, { _id: 0 })
  .sort({ taux_fraude_pct: -1 })
  .limit(10)
  .forEach((doc) => {
    print(`  Carte ${String(doc.id_carte).padStart(5)} | ${String(doc.nb_transactions).padStart(5)} tx | ${String(doc.nb_fraudes).padStart(3)} fraudes | ${doc.taux_fraude_pct.toFixed(2).padStart(6)}%`);
  });

// -----------------------------------------------------------------------------
// DEMO 5 : Aggregation pipeline avancee - Fraudes par genre / age
// -----------------------------------------------------------------------------
print("\n[DEMO 5] Aggregation $facet : Fraudes par tranche d'age et genre");
// $facet permet de faire plusieurs aggregations en parallele dans une seule requete
db.transactions_enriched.aggregate([
  { $match: { "fraude.is_fraud": true } },
  {
    $facet: {
      "par_genre": [
        { $group: { _id: "$client.gender", count: { $sum: 1 } } },
        { $sort: { count: -1 } }
      ],
      "par_tranche_age": [
        {
          $bucket: {
            groupBy: "$client.current_age",
            boundaries: [0, 25, 35, 45, 55, 65, 130],
            default: "unknown",
            output: { count: { $sum: 1 } }
          }
        }
      ],
      "par_type_paiement": [
        { $group: { _id: "$use_chip", count: { $sum: 1 } } },
        { $sort: { count: -1 } }
      ]
    }
  }
]).forEach((doc) => printjson(doc));

// -----------------------------------------------------------------------------
// DEMO 6 : EXPLAIN d'une requete avec index
// -----------------------------------------------------------------------------
print("\n[DEMO 6] Plan d'execution d'une requete : transactions d'un client");
const plan = db.transactions_enriched
  .find({ "client.id_client": 1178 })
  .sort({ date_transaction: -1 })
  .limit(5)
  .explain("executionStats");

const stage = plan.executionStats;
print(`  Stage : ${plan.queryPlanner.winningPlan.inputStage?.stage || plan.queryPlanner.winningPlan.stage}`);
print(`  Index utilise : ${plan.queryPlanner.winningPlan.inputStage?.indexName || "(aucun ou collection scan)"}`);
print(`  Documents examines : ${stage.totalDocsExamined}`);
print(`  Documents retournes : ${stage.nReturned}`);
print(`  Temps execution : ${stage.executionTimeMillis} ms`);

print("\n" + "=".repeat(78));
print("FIN DE LA DEMO");
print("=" .repeat(78));
