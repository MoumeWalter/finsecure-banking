SELECT table_concernee, operation, COUNT(*) AS nb
FROM journal_audit
GROUP BY table_concernee, operation
ORDER BY 1, 2;
