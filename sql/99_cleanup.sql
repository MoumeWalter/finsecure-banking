-- Cleanup complet du schema finsecure
BEGIN
  FOR r IN (SELECT object_name, object_type FROM user_objects
            WHERE object_type IN ('TABLE','VIEW','MATERIALIZED VIEW',
                                  'SEQUENCE','PACKAGE','TRIGGER','FUNCTION','PROCEDURE')
            ORDER BY CASE object_type
              WHEN 'TRIGGER' THEN 1
              WHEN 'MATERIALIZED VIEW' THEN 2
              WHEN 'VIEW' THEN 3
              WHEN 'PACKAGE' THEN 4
              WHEN 'FUNCTION' THEN 5
              WHEN 'TABLE' THEN 6
              ELSE 7 END) LOOP
    BEGIN
      IF r.object_type = 'TABLE' THEN
        EXECUTE IMMEDIATE 'DROP TABLE "' || r.object_name || '" CASCADE CONSTRAINTS PURGE';
      ELSE
        EXECUTE IMMEDIATE 'DROP ' || r.object_type || ' "' || r.object_name || '"';
      END IF;
      DBMS_OUTPUT.PUT_LINE('Dropped ' || r.object_type || ' ' || r.object_name);
    EXCEPTION WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Skip ' || r.object_name || ' : ' || SQLERRM);
    END;
  END LOOP;
END;
/
EXIT;
