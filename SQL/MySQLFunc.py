# -*- coding: utf-8 -*-

import MYSQL as SQL
import sys,time,signal
sys.path.append( "./blocks/" )
import blocksreader as bh
import base64

from datetime import datetime
from colors import *
ClosedThreads = False

def CloseThreads(a=0,b=0):
	ClosedThreads=True
	print COLORSBASH["YELLOW"]+"Close SQL thread...."+COLORSBASH["END"]

def ReadingDat(datfile):
	return AddBlock(datfile)

def GetSize(datfile):
		TmpSize = datfile.tell()
		datfile.seek(0,2)
		LastTell = datfile.tell()
		datfile.seek(TmpSize,0)
		return LastTell


def SetFseek(datfile):
	tmpBase = SQL.MySQL()
	cursor = tmpBase.query("select conf_value from settings where conf_name='lseek';",())
	lseek = 0
	for (conf_value) in cursor:
	 lseek=int(conf_value[0])
	cursor.close()
	datfile.seek(0,2)
	last_size = datfile.tell() # maybe later... for other...
	print "Buff bytes of blockchain: "+ str(last_size)
	datfile.seek(0,0)
	if lseek > 0:
		datfile.seek(lseek,0)
	tmpBase.destruct()
	cursor = None
	tmpBase = None

def Thread(datfile):
	signal.signal(signal.SIGUSR1,CloseThreads)
	global ClosedThreads
	SetFseek(datfile)
	while not ClosedThreads:
	 if ReadingDat(datfile) == False:
		print COLORSBASH["GREEN"]+"Synchroned!"+COLORSBASH["END"]
		LastSize = GetSize(datfile)
		while LastSize <= GetSize(datfile):
			print COLORSBASH["WHITE"]+"Wait other blocks"+COLORSBASH["END"]
			time.sleep(30)
		SetFseek(datfile)
	 

def InstallTables():
	tmpBase = SQL.MySQL()

	INSTALLING = []
	INSTALLING.append("create table Blocks(id bigint(255) unsigned PRIMARY KEY AUTO_INCREMENT,     size int(255) unsigned,    version int(255) unsigned,            magic varchar(10),prevhash varchar(64),MerkleRoot varchar(64),Difficulty double unsigned,nonce int(255) unsigned,date varchar(24));");
	INSTALLING.append('''create table Blocks_Transactions(id bigint(255) unsigned PRIMARY KEY AUTO_INCREMENT,
TxVersion int unsigned,
Count_inputs bigint(255) unsigned,
Count_outputs bigint(255) unsigned,
locktime int unsigned
);''')
	INSTALLING.append('''create table Blocks_Transactions_Input(from_id bigint(255) unsigned,
txOutId int(255) unsigned,
seqNo int(255) unsigned,
prevhash varchar(64),
scriptSig varchar(255),
scriptlen int(255) unsigned 
);''')
	INSTALLING.append('''create table Blocks_Transactions_Output(from_id bigint(255) unsigned,
pubkey varchar(255),
value double unsigned,
scriptlen int(255) unsigned 
);''')
	INSTALLING.append('''create table settings(conf_name varchar(255),conf_value varchar(255));''')
	INSTALLING.append('''insert into settings values('lseek', '0' );''')
	for i in INSTALLING:	
	 cursor = tmpBase.query(i,())
	 cursor.close()
	#tmpBase.commit()
	tmpBase.destruct()
	tmpBase = None	
	return True

def AddBlock(dat):
	block = bh.BlockReader(dat)
	if block == False:
	 tmpBase.destruct()
	 return False
	tmpBase = SQL.MySQL()

	BlocksAdd = '''
	insert into Blocks(size,version,magic,prevhash,MerkleRoot,Difficulty,nonce,date) values
	(
	%s,%s,%s,%s,%s,%s,%s,%s
	);
	'''
	
	BlocksTransactionsAdd = '''insert into Blocks_Transactions(TxVersion,Count_inputs,Count_outputs,locktime) values(%s,%s,%s,%s);'''
	BlocksTransactionsInputAdd = '''insert into Blocks_Transactions_Input values(%s,%s,%s,%s,%s,%s);'''
	BlocksTransactionsInputOutput = '''insert into Blocks_Transactions_Output values(%s,%s,%s,%s);'''
	addLastSeek = '''update settings set conf_value='%s' where conf_name='lseek';'''
	LastBlockCount = '''SELECT COUNT(*) as last from Blocks;'''
	tmp = block.ReturnAllToList()
	if tmp == False or tmp['BlockSize'] ==0 or tmp["BlockHeader"]['version']==0:
		cursor = tmpBase.query(addLastSeek,(dat.tell(),))
		cursor.close()
		return False
	
	cursor = tmpBase.query(BlocksAdd,(tmp['BlockSize'],tmp["BlockHeader"]['version'],tmp["Magic"],tmp["BlockHeader"]['previousHash'],tmp['BlockHeader']['merkleRoot'],bh.GetDiff(tmp["BlockHeader"]['nbits']),tmp["BlockHeader"]['nonce'],datetime.utcfromtimestamp(tmp["BlockHeader"]['ntime']).strftime('%Y.%m.%d %H:%M:%S GMT0'),))
	cursor.close()
    	cursor = tmpBase.query(LastBlockCount,())
	LastBlock = 0
	for (last) in cursor:
	 LastBlock = last[0]-1
	cursor.close()
	for txs in tmp["Txs"]:
	 tmptxs = txs.GetAllAsList()
	 # Add bluh-bluh
	 cursor = tmpBase.query(BlocksTransactionsAdd,(tmptxs["TxVersion"],tmptxs["TxInputs"],tmptxs["TxOutPuts"],tmptxs["TxLockTime"],))
	 cursor.close()
	 for i in tmptxs['TxInput']:
	  t = i.GetAllAsList()	  
	  scriptSig = base64.b64encode(t['scriptSig'])
	  cursor = tmpBase.query(BlocksTransactionsInputAdd,(LastBlock,t['txOutId'],t['seqNo'],bh.hashstr(t['PrevHash']),scriptSig,t['scriptLen'],))
	  cursor.close()
	 for i in tmptxs['TxOutputs']:
	  t = i.GetAllAsList()
	  cursor = tmpBase.query(BlocksTransactionsInputOutput,(LastBlock,bh.hashstr(t['pubkey']),bh.FromSatToFull(t['value']),t['scriptLen'],))
	  cursor.close()	
	cursor = tmpBase.query(addLastSeek,(dat.tell(),))
	cursor.close()
	cursor=None
	tmpBase.commit()
	tmpBase.destruct()
	tmpBase = None
	block = None
	print COLORSBASH["CYAN"]+"Added block #"+str(LastBlock)+COLORSBASH["END"]
	return True
