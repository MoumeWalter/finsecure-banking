SET SERVEROUTPUT ON;
SET SERVEROUTPUT ON SIZE 1000000;
BEGIN
  DBMS_OUTPUT.PUT_LINE('=== Refresh des datamarts ===');
  pkg_datamart.pr_refresh_all_datamarts;
  DBMS_OUTPUT.PUT_LINE('=== Termine ===');
END;
/
EXIT;
