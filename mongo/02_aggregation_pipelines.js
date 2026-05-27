// =============================================================================
// 02_aggregation_pipelines.js
// =============================================================================
// Reproduit en MongoDB les 3 datamarts Oracle (mv_card / mv_daily / mv_mcc).
//
// Strategie : on cree des vues MongoDB (db.createView) qui sont l'equivalent
// des vues materialisees Oracle. Difference notable : les vues MongoDB sont
// recalculees a la volee. Pour materialiser, utiliser $merge ou $out.
//
// Execution :
//   docker exec mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin" /tmp/mongo/02_aggregation_pipelines.js
// =============================================================================

use('finsecure');

print("=== Creation des vues d'aggregation ===");

// -----------------------------------------------------------------------------
// VUE 1 : aggregats par carte (equivalent mv_card_aggregates)
// -----------------------------------------------------------------------------
try { db.v_card_aggregates.drop(); } catch (e) {}

db.createView(
  "v_card_aggregates",
  "transactions_enriched",
  [
    {
      $group: {
        _id: "$carte.id_carte",
        nb_transactions: { $sum: 1 },
        total_amount: { $sum: "$amount" },
        avg_amount: { $avg: "$amount" },
        nb_fraudes: {
          $sum: { $cond: [{ $eq: ["$fraude.is_fraud", true] }, 1, 0] }
        }
      }
    },
    {
      $project: {
        _id: 0,
        id_carte: "$_id",
        nb_transactions: 1,
        total_amount: { $round: ["$total_amount", 2] },
        avg_amount: { $round: ["$avg_amount", 2] },
        nb_fraudes: 1,
        taux_fraude_pct: {
          $cond: [
            { $eq: ["$nb_transactions", 0] },
            0,
            { $round: [{ $multiply: [{ $divide: ["$nb_fraudes", "$nb_transactions"] }, 100] }, 4] }
          ]
        }
      }
    }
  ]
);
print("OK vue v_card_aggregates creee");

// -----------------------------------------------------------------------------
// VUE 2 : aggregats journaliers (equivalent mv_daily_aggregates)
// -----------------------------------------------------------------------------
try { db.v_daily_aggregates.drop(); } catch (e) {}

db.createView(
  "v_daily_aggregates",
  "transactions_enriched",
  [
    {
      $group: {
        _id: "$situation_date",
        nb_tx: { $sum: 1 },
        total_amount: { $sum: "$amount" },
        avg_amount: { $avg: "$amount" },
        nb_fraudes: {
          $sum: { $cond: [{ $eq: ["$fraude.is_fraud", true] }, 1, 0] }
        }
      }
    },
    {
      $project: {
        _id: 0,
        situation_date: "$_id",
        nb_tx: 1,
        total_amount: { $round: ["$total_amount", 2] },
        avg_amount: { $round: ["$avg_amount", 2] },
        nb_fraudes: 1
      }
    },
    { $sort: { situation_date: -1 } }
  ]
);
print("OK vue v_daily_aggregates creee");

// -----------------------------------------------------------------------------
// VUE 3 : aggregats par categorie marchand (equivalent mv_mcc_aggregates)
// -----------------------------------------------------------------------------
try { db.v_mcc_aggregates.drop(); } catch (e) {}

db.createView(
  "v_mcc_aggregates",
  "transactions_enriched",
  [
    {
      $group: {
        _id: { code: "$mcc.code", libelle: "$mcc.libelle" },
        nb_transactions: { $sum: 1 },
        total_amount: { $sum: "$amount" },
        avg_amount: { $avg: "$amount" },
        nb_cartes_uniques: { $addToSet: "$carte.id_carte" }
      }
    },
    {
      $project: {
        _id: 0,
        code_mcc: "$_id.code",
        libelle_mcc: "$_id.libelle",
        nb_transactions: 1,
        total_amount: { $round: ["$total_amount", 2] },
        avg_amount: { $round: ["$avg_amount", 2] },
        nb_cartes_uniques: { $size: "$nb_cartes_uniques" }
      }
    },
    { $sort: { nb_transactions: -1 } }
  ]
);
print("OK vue v_mcc_aggregates creee");

// -----------------------------------------------------------------------------
// Bilan
// -----------------------------------------------------------------------------
print("\n=== Test des vues ===");

print("\nTop 5 cartes les plus actives :");
db.v_card_aggregates
  .find({}, { id_carte: 1, nb_transactions: 1, total_amount: 1, nb_fraudes: 1, _id: 0 })
  .sort({ nb_transactions: -1 })
  .limit(5)
  .forEach((doc) => printjson(doc));

print("\nAggregats journaliers :");
db.v_daily_aggregates.find().limit(3).forEach((doc) => printjson(doc));

print("\nTop 5 categories marchands :");
db.v_mcc_aggregates.find().limit(5).forEach((doc) => printjson(doc));
