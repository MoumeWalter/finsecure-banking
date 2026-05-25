EXPLAIN PLAN FOR
SELECT mcc.libelle_mcc, COUNT(*) AS nb_fraudes
FROM label_fraude lf
INNER JOIN transaction t ON lf.id_transaction = t.id_transaction
INNER JOIN marchand m ON t.id_marchand = m.id_marchand
INNER JOIN mcc ON m.code_mcc = mcc.code_mcc
WHERE lf.is_fraud = 'Y'
GROUP BY mcc.libelle_mcc
ORDER BY nb_fraudes DESC
FETCH FIRST 10 ROWS ONLY;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC +PARTITION +PREDICATE'));
