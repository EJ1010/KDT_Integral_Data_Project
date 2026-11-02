/*===============================================================
	데이터베이스 생성
===============================================================*/

-- 데이터베이스 daewon 생성
CREATE DATABASE IF NOT EXISTS daewon
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
  
-- daewon이라는 데이터 베이스 확인
SHOW DATABASES LIKE 'daewon';

-- 데이터베이스 사용
USE daewon;



/*===============================================================
	권한 설정
===============================================================*/
-- 권한 부여
GRANT
		SELECT,
		INSERT,
		UPDATE,
		DELETE,
		CREATE,
		DROP,
		ALTER,
		INDEX,
		REFERENCES,
		CREATE TEMPORARY TABLES,
		LOCK TABLES,
		EXECUTE,
		CREATE VIEW,
		SHOW VIEW,
		TRIGGER,
		EVENT
ON 	daewon.*
TO
    'integral_gy'@'%',
    'integral_jn'@'%',
    'integral_sj'@'%',
    'integral_yr'@'%';
    
    
GRANT
		SELECT,
		INSERT,
		UPDATE,
		DELETE,
		CREATE,
		DROP,
		ALTER,
		INDEX,
		REFERENCES,
		CREATE TEMPORARY TABLES,
		LOCK TABLES,
		EXECUTE,
		CREATE VIEW,
		SHOW VIEW,
		TRIGGER,
		EVENT
ON 	daewon.*
TO	'integral_ej'@'%';
    
    
-- 권한 확인
SHOW GRANTS FOR 'integral_gy'@'%';
SHOW GRANTS FOR 'integral_jn'@'%';
SHOW GRANTS FOR 'integral_sj'@'%';
SHOW GRANTS FOR 'integral_yr'@'%';
SHOW GRANTS FOR 'integral_ej'@'%';



-- 권한 삭제
REVOKE ALL PRIVILEGES
ON daewon.*
FROM
    'integral_gy'@'%',
    'integral_jn'@'%',
    'integral_sj'@'%',
    'integral_yr'@'%';