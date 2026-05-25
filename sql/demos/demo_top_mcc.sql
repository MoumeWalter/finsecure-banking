SELECT * FROM (
  SELECT libelle_mcc, nb_transactions, total_amount, nb_cartes_uniques
  FROM mv_mcc_aggregates
  ORDER BY nb_transactions DESC
) WHERE rownum <= 10;
