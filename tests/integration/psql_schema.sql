-- Drop all tables in the database
DO $$ DECLARE
	r RECORD;
BEGIN
	FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
		EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
	END LOOP;
END $$;

-- TODO: update to match schema changes made in setupconfig.py

-- Create new ones
CREATE TABLE iwkspc_main(rowid SERIAL PRIMARY KEY, wid char(36) NOT NULL, 
	friendly_address VARCHAR(48), password VARCHAR(128) NOT NULL, 
	status VARCHAR(16) NOT NULL);

CREATE TABLE iwkspc_folders(rowid SERIAL PRIMARY KEY, wid char(36) NOT NULL, 
	enc_name VARCHAR(128) NOT NULL, enc_key VARCHAR(64) NOT NULL);

CREATE TABLE iwkspc_devices(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL,
	devid CHAR(36) NOT NULL, keytype VARCHAR(16) NOT NULL,
	devkey VARCHAR(1000) NOT NULL, status VARCHAR(16) NOT NULL);

CREATE TABLE failure_log(rowid SERIAL PRIMARY KEY, type VARCHAR(16) NOT NULL,
	id VARCHAR(36), source VARCHAR(36) NOT NULL, count INTEGER,
	last_failure TIMESTAMP NOT NULL, lockout_until TIMESTAMP);

CREATE TABLE prereg(rowid SERIAL PRIMARY KEY, wid VARCHAR(36) NOT NULL UNIQUE,
	uid VARCHAR(128) NOT NULL, regcode VARCHAR(128));
