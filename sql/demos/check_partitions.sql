SELECT partition_name, partition_position FROM user_tab_partitions WHERE table_name = 'TRANSACTION' ORDER BY partition_position;
