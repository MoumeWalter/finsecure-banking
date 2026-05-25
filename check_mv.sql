SELECT 'mv_card_aggregates' AS mv, COUNT(*) AS nb FROM mv_card_aggregates UNION ALL
SELECT 'mv_daily_aggregates', COUNT(*) FROM mv_daily_aggregates UNION ALL
SELECT 'mv_mcc_aggregates', COUNT(*) FROM mv_mcc_aggregates
ORDER BY 1;
