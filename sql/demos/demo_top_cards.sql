SELECT * FROM (
  SELECT id_carte, nb_transactions, total_amount, nb_fraudes, taux_fraude_pct
  FROM mv_card_aggregates
  ORDER BY nb_transactions DESC
) WHERE rownum <= 10;
