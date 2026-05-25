SELECT * FROM (
  SELECT id_carte, nb_transactions, nb_fraudes, taux_fraude_pct
  FROM mv_card_aggregates
  WHERE nb_transactions >= 100
  ORDER BY taux_fraude_pct DESC
) WHERE rownum <= 10;
