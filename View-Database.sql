USE labour_connect;
SHOW TABLES;

-- Main project records (omit account password hashes).
SELECT id, username, first_name, last_name, email, role, is_active
FROM accounts_user ORDER BY id;

SELECT * FROM core_servicecategory ORDER BY id;
SELECT * FROM workers_workerprofile ORDER BY id;
SELECT * FROM jobs_booking ORDER BY id;
SELECT * FROM jobs_job ORDER BY id;
SELECT * FROM payments_payment ORDER BY id;
SELECT * FROM reviews_review ORDER BY id;
