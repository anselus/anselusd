#!/usr/bin/env python3


import argparse
import array
import base64
import diceware
import nacl.public
import nacl.pwhash
import nacl.secret
import nacl.utils
import os.path
import psycopg2
import secrets
import string
import sys
import toml
import uuid


# Function definitions
def generate_password():
	# Diceware module isn't very friendly as a module. :/
	options = argparse.Namespace()
	options.num = 3
	options.caps = True
	options.specials = 0
	options.delimiter = ''
	options.randomsource = 'system'
	options.wordlist = 'en_eff'
	options.infile = None
	return diceware.get_passphrase(options)


def generate_unid(length):
	if length < 50:
		length = 50
	
	try:
		get_char = unichr
	except NameError:
		get_char = chr

	include_ranges = [
		( 0x0021, 0x007E ), # Basic Latin
		( 0x00A1, 0x00AC ), # Latin-1 Supplement
		( 0x00AE, 0x00FF ), # Latin-1 Supplement
		( 0x0100, 0x017F ), # Latin Extended-A
		( 0x0180, 0x024F ), # Latin Extended-B
		( 0x0250, 0x02AF ), # International Phonetic Alphabet
		( 0x0370, 0x0377 ), # Greek and Coptic
		( 0x037A, 0x037E ), # Greek and Coptic
		( 0x0384, 0x038A ), # Greek and Coptic
		( 0x038C, 0x038C ), # Greek and Coptic
		( 0x038E, 0x03FF ), # Greek and Coptic
		( 0x0400, 0x04FF ), # Cyrillic
		( 0x0500, 0x052F ), # Cyrillic Supplement
		( 0x0600, 0x06FF ), # Arabic
		( 0x0750, 0x077F ), # Arabic Supplement
		( 0x16A0, 0x16F0 ), # Runic
		( 0x1E00, 0x1EFF ), # Latin Extended Additional
		( 0x2600, 0x26FF ), # Misc. Symbols
		( 0x2700, 0x27BF ), # Block Dingbats
		( 0x2C60, 0x2C7F ), # Latin Extended-C
		( 0xA720, 0xA7AD ), # Latin Extended-D
	]

	charlist = [
		get_char(code_point) for current_range in include_ranges
			for code_point in range(current_range[0], current_range[1] + 1)
	]
	return ''.join(secrets.choice(charlist) for i in range(length))


def generate_account():
	first_names = [ "Leanne", "Lauryn", "Cheryl", "Addie", "Lynnette", "Meredith", "Jay", "Bernie",
					"Kenneth", "Harding", "Elissa", "Beth", "Vance", "Holden", "Careen", "Jackie",
					"Laurence", "Grover", "Megan", "Daniel", "Shelby", "Desmond", "Jason", "Patton",
					"Harvey", "Dylan", "Eleanor", "Grace", "Randall", "Carmen", "Lewis"
	]

	last_names = [ "Rennoll", "Layton", "Page", "Steffen", "Wilbur", "Clifford", "Ridge", "Norton",
					"Haden", "Smith", "Harris", "Bush", "Addison", "Warren", "Armstrong", "Radcliff",
					"Stern", "Jernigan", "Tucker", "Blackwood", "Gray", "Eaton", "Bissette", "Albert",
					"Rogers", "Tyrrell", "Randall", "Ramsey", "Parish", "Towner", "Granville"
	]

	rgen = secrets.SystemRandom()

	account = {}

	# Generate basic account data

	wid = str(uuid.uuid4())
	account['wid'] = wid
	if rgen.randint(1, 100) < 51:
		account['friendly_address'] = ''.join([rgen.choice(first_names), ' ', 
											rgen.choice(last_names), '/example.com'])
	else:
		account['friendly_address'] = ''
	
	password = generate_password()
	account['password'] = password
	salt = nacl.utils.random(nacl.pwhash.argon2id.SALTBYTES)
	account['pwsalt'] = salt
	account['pwsalt_b85'] = base64.b85encode(salt).decode('utf8')
	account['pwhash'] = nacl.pwhash.argon2id.kdf(nacl.secret.SecretBox.KEY_SIZE,
							bytes(password, 'utf8'), salt,
							opslimit=nacl.pwhash.argon2id.OPSLIMIT_INTERACTIVE,
							memlimit=nacl.pwhash.argon2id.MEMLIMIT_INTERACTIVE)	
	account['pwhash_b85'] = base64.b85encode(account['pwhash']).decode('utf8')
	
	if rgen.randint(1, 100) < 76:
		account['status'] = 'active'
	else:
		account['status'] = 'disabled'
	
	# Generate user's encryption keys
	identity = nacl.public.PrivateKey.generate()
	contact_request = nacl.public.PrivateKey.generate()
	firstdevice = nacl.public.PrivateKey.generate()
	broadcast_aes = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
	system_aes = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
	folder_aes = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
	
	account['keys'] = [
		{	'type' : 'ed25519',
			'purpose' : 'identity',
			'id' : generate_unid(50),
			'public_key' : bytes(identity.public_key),
			'private_key' : bytes(identity),
			'public_b85' : base64.b85encode(bytes(identity.public_key)).decode('utf8'),
			'private_b85' : base64.b85encode(bytes(identity)).decode('utf8')
		},
		{	'type' : 'ed25519',
			'purpose' : 'contact_request',
			'id' : generate_unid(50),
			'public_key' : bytes(contact_request.public_key),
			'private_key' : bytes(contact_request),
			'public_b85' : base64.b85encode(bytes(contact_request.public_key)).decode('utf8'),
			'private_b85' : base64.b85encode(bytes(contact_request)).decode('utf8')
		},
		{	'type' : 'ed25519',
			'purpose' : 'firstdevice',
			'id' : generate_unid(50),
			'public_key' : bytes(firstdevice.public_key),
			'private_key' : bytes(firstdevice),
			'public_b85' : base64.b85encode(bytes(firstdevice.public_key)).decode('utf8'),
			'private_b85' : base64.b85encode(bytes(firstdevice)).decode('utf8')
		},
		{
			'type' : 'aes256',
			'purpose' : 'broadcast',
			'id' : generate_unid(50),
			'key' : broadcast_aes,
			'key_b85' : base64.b85encode(broadcast_aes).decode('utf8')
		},
		{
			'type' : 'aes256',
			'purpose' : 'system',
			'id' : generate_unid(50),
			'key' : system_aes,
			'key_b85' : base64.b85encode(system_aes).decode('utf8')
		},
		{
			'type' : 'aes256',
			'purpose' : 'folder',
			'id' : generate_unid(50),
			'key' : folder_aes,
			'key_b85' : base64.b85encode(folder_aes).decode('utf8')
		},
	]
	
	account['folder_map'] = {
		'Messages' : str(uuid.uuid4()),
		'Contacts' : str(uuid.uuid4()),
		'Calendar' : str(uuid.uuid4()),
		'Tasks' : str(uuid.uuid4()),
		'Files' : str(uuid.uuid4()),
		'Files Attachments' : str(uuid.uuid4()),
		'Social' : str(uuid.uuid4())
	}

	account['devices'] = list()
	dev_count = rgen.randrange(1,6)
	i = 0
	while i < dev_count:
		devkey = nacl.public.PrivateKey.generate()
		account['devices'].append( {
				'id' : str(uuid.uuid4()),
				'key' :	{
					'type' : 'ed25519',
					'purpose' : 'identity',
					'id' : generate_unid(50),
					'public_key' : bytes(devkey.public_key),
					'private_key' : bytes(devkey),
					'public_b85' : base64.b85encode(bytes(devkey.public_key)).decode('utf8'),
					'private_b85' : base64.b85encode(bytes(devkey)).decode('utf8')
				}
			}
		)
		i = i + 1

	return account


def reset_database(dbconn):
	# Drop all tables in the database
	dropcmd = '''DO $$ DECLARE
		r RECORD;
	BEGIN
		FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
			EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
		END LOOP;
	END $$;'''
	cursor = dbconn.cursor()
	cursor.execute(dropcmd)
	cursor.execute("CREATE TABLE iwkspc_main(id SERIAL PRIMARY KEY, wid char(36) NOT NULL, "
					"friendly_address VARCHAR(48) NULL, password VARCHAR(128) NOT NULL, "
					"status VARCHAR(16) NOT NULL);")
	cursor.execute("CREATE TABLE iwkspc_folders(id SERIAL PRIMARY KEY, fid char(36) NOT NULL, "
					"wid char(36) NOT NULL, enc_name VARCHAR(128) NOT NULL, "
					"enc_key VARCHAR(64) NOT NULL);")
	cursor.execute("CREATE TABLE iwkspc_sessions(id SERIAL PRIMARY KEY, wid char(36) NOT NULL, "
					"devid char(36) NOT NULL, device_key VARCHAR(128) NOT NULL);")
	cursor.close()
	dbconn.commit()


def add_account_to_db(account, dbconn):
	cursor = dbconn.cursor()
	cmdparts = ["INSERT INTO iwkspc_main(wid,friendly_address,password,status) VALUES('",
				account['wid'],
				"',"]
	if len(account['friendly_address']) > 0:
		cmdparts.extend(["'",account['friendly_address'],"',"])
	else:
		cmdparts.append("'',")
	
	cmdparts.extend(["$$", account['pwhash_b85'],"$$,'",account['status'], "');"])
	cmd = ''.join(cmdparts)
	cursor.execute(cmd)
	
	box = nacl.secret.SecretBox(account['keys'][5]['key'])
	for folder_name,fid in account['folder_map'].items():
		cmd = ("INSERT INTO iwkspc_folders(wid, fid, enc_name, enc_key) "
					"VALUES('%s','%s','%s',$$%s$$);" % 
					( account['wid'], fid,
					base64.b85encode(box.encrypt(bytes(folder_name, 'utf8'))).decode('utf8'),
					account['keys'][5]['id']))
		cursor.execute(cmd)

	i = 0
	while i < len(account['devices']):
		cmd =	(	"INSERT INTO iwkspc_sessions(wid, devid, device_key) "
					"VALUES('%s','%s',$$%s$$);" % (
						account['wid'], account['devices'][i]['id'], 
						account['devices'][i]['key']['public_b85']
					)
				)
		cursor.execute(cmd)
		i = i + 1
	
	cursor.close()
	dbconn.commit()


def dump_account(account):
	out = {
		"Workspace ID" : account['wid'],
		"Friendly Address" : account['friendly_address'],
		"Status" : account['status'],
		"Password" : account['password'],
		"Password Salt.b85" : account['pwsalt_b85'],
		"Password Hash.b85" : account['pwhash_b85'],
		"Identity Public.b85" : account['keys'][0]['public_b85'],
		"Identity Private.b85" : account['keys'][0]['private_b85'],
		"Contact Public.b85" : account['keys'][1]['public_b85'],
		"Contact Private.b85" : account['keys'][1]['private_b85'],
		"First Device Public.b85" : account['keys'][2]['public_b85'],
		"First Device Private.b85" : account['keys'][2]['private_b85'],
		"Broadcast.b85" : account['keys'][3]['key_b85'],
		"System.b85" : account['keys'][4]['key_b85'],
		"Folder Map.b85" : account['keys'][5]['key_b85'],
		"Message Folder" : account['folder_map']['Messages'],
		"Contacts Folder" : account['folder_map']['Contacts'],
		"Calendar Folder" : account['folder_map']['Calendar'],
		"Tasks Folder" : account['folder_map']['Tasks'],
		"Files Folder" : account['folder_map']['Files'],
		"Attachments Folder" : account['folder_map']['Files Attachments'],
		"Social Folder" : account['folder_map']['Social'],
	}
	
	i = 0
	while i < len(account['devices']):
		out["Device #%s ID" % str(i+1)] = account['devices'][i]['id']
		out["Device #%s Public.b85" % str(i+1)] = account['devices'][i]['key']['public_b85']
		out["Device #%s Private.b85" % str(i+1)] = account['devices'][i]['key']['private_b85']
		i = i + 1

	for k,v in out.items():
		print("%s : %s" % (k,v))
	print("")
	

## Begin script execution	

# Step 1: load the config

config_file_path = '/etc/anselus-server/serverconfig.toml'

if os.path.exists(config_file_path):
	try:
		serverconfig = toml.load(config_file_path)
	except Exception as e:
		print("Unable to load server config %s: %s" % (config_file_path, e))
		sys.exit(1)
else:
	serverconfig = {}

serverconfig.setdefault('database', dict())
serverconfig['database'].setdefault('engine','postgresql')
serverconfig['database'].setdefault('ip','127.0.0.1')
serverconfig['database'].setdefault('port','5432')
serverconfig['database'].setdefault('name','anselus')
serverconfig['database'].setdefault('user','anselus')
serverconfig['database'].setdefault('password','CHANGEME')

serverconfig.setdefault('network', dict())
serverconfig['network'].setdefault('listen_ip','127.0.0.1')
serverconfig['network'].setdefault('port','2001')

serverconfig.setdefault('global', dict())
serverconfig['global'].setdefault('workspace_dir','/var/anselus')
serverconfig['global'].setdefault('registration','private')
serverconfig['global'].setdefault('default_quota',0)

serverconfig.setdefault('security', dict())
serverconfig['security'].setdefault('failure_delay_sec',3)
serverconfig['security'].setdefault('max_failures',5)
serverconfig['security'].setdefault('lockout_delay_min',15)
serverconfig['security'].setdefault('registration_delay_min',15)

if serverconfig['database']['engine'].lower() != 'postgresql':
	print("This script expects a server config using PostgreSQL. Exiting")
	sys.exit()

# Step 2: Connect to the database

try:
	conn = psycopg2.connect(host=serverconfig['database']['ip'],
							port=serverconfig['database']['port'],
							database=serverconfig['database']['name'],
							user=serverconfig['database']['user'],
							password=serverconfig['database']['password'])
except Exception as e:
	print("Couldn't connect to database: %s" % e)
	sys.exit(1)

# Step 3: Generate accounts and add to database

reset_database(conn)
for i in range(0,5):
	test = generate_account()
	add_account_to_db(test, conn)
	dump_account(test)
