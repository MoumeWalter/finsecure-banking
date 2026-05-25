EXPLAIN PLAN FOR
SELECT t.id_transaction, t.amount, cl.id_client, mcc.libelle_mcc, lf.is_fraud
FROM transaction t
INNER JOIN carte c ON t.id_carte = c.id_carte
INNER JOIN client cl ON c.id_client = cl.id_client
INNER JOIN marchand m ON t.id_marchand = m.id_marchand
INNER JOIN mcc ON m.code_mcc = mcc.code_mcc
LEFT JOIN label_fraude lf ON t.id_transaction = lf.id_transaction
WHERE t.id_transaction = 12345678;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC +PARTITION +PREDICATE'));
