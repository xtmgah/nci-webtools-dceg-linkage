from pymongo import MongoClient
import os
import csv
client = MongoClient()
client = MongoClient('localhost', 27017)
# Open Database
db = client.snp_test

#Create/Update database
def Multi():
	
	# Manifest Info
	folder='./snp_test/test2/' #<------Must change to source folder of manifest files
	manifest_file=os.listdir(folder)
	manifest=[]
	for k in range(0,len(manifest_file)):
		file_name=os.path.splitext(manifest_file[k])[0]
		manifest.append(file_name)
		manifest_file[k]=folder+manifest_file[k]

	for i in range(len(manifest)):
		Insert(manifest_file[i],manifest[i])			
		

def Single():


def Insert(file,platform):
	db.snp_col.create_index("pos")
	snp_data=csv.reader(open(file))			
	for coord in snp_data:
		Chr=coord[0].split(":")[0].strip("chr")
		position=coord[0].split("-")[1]
		db.snp_col.update(
    		{ "pos": position },
    		{ "$addToSet" : { "data" : { "$each" :[ { "chr" : Chr, "platform" :platform} ] } } },
    		upsert=True,
		)
