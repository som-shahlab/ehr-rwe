import sys
sys.path.insert(0,'../../ehr-rwe/')

import os
import glob
import collections
import argparse
import numpy as np
import pandas as pd
import hashlib
import datetime

from datetime import datetime, timedelta
from prep_mimic import preprocess

def load_clinical_notes(row_ids, mimic_fpath):
	# load row_id notes
	docs = {}
	for chunk in pd.read_csv(mimic_fpath, sep=',', compression='infer', chunksize=10000):
		for row in chunk.itertuples():
			#digest = hashlib.md5(row.TEXT.encode("utf-8")).digest()
			try:
				if row.ROW_ID in row_ids:
					docs[row.ROW_ID] = row
			except Exception as e:
				print(e, row.ROW_ID)
				
	return docs

def load_row_ids(fpath):
	return set([int(x) for x in open(fpath, 'r').read().splitlines()])

def process_clinical_notes(docs):
	for row_id in docs:
		row = docs[row_id]
		row = {name:getattr(row, name) for name in row._fields if name != 'Index'}
		
		# convert timestamps
		chartdate = None if type(row['CHARTDATE']) is not str else datetime.strptime(row['CHARTDATE'], '%Y-%m-%d')
		charttime = None if type(row['CHARTTIME']) is not str else datetime.strptime(row['CHARTTIME'], '%Y-%m-%d %H:%M:%S')
		
		# get structured chart time
		doc_ts = charttime.year if charttime else chartdate.year
		
		# convert note text
		text, tdelta = preprocess(row["TEXT"], doc_ts=doc_ts, preserve_offsets=True)
		# escape whitespace
		text = text.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r') 
		
		# if timedelta is 0, then no full datetimes were found in the note,
		if tdelta == 0:
			sample_range = range(2008, 2020)
			tdelta = int(doc_ts - np.random.choice(sample_range, 1)[0])
		
		if chartdate:
			chartdate -= timedelta(days=tdelta * 365)
		if charttime:
			charttime -= timedelta(days=tdelta * 365)
		
		
		if type(row['HADM_ID']) is not str and np.isnan(row['HADM_ID']):
			row['HADM_ID'] = 'NaN'
		else:
			row['HADM_ID'] = int(row['HADM_ID'])
		
		row['SUBJECT_ID'] = int(row['SUBJECT_ID'])
		row['ROW_ID'] = int(row['ROW_ID'])
		
		row['DOC_NAME'] = f"{row['ROW_ID']}_{row['SUBJECT_ID']}_{row['HADM_ID']}"
		row['TEXT'] = text
		row['CHARTDATE'] = str(chartdate.date())
		row['CHARTTIME'] = str(charttime)  if charttime is not None else np.nan  
		docs[row_id] = row

def dump_tsvs(dataset, fpath):
	for name in dataset:
		if not os.path.exists(f'{fpath}/{name}'):
			os.makedirs(f'{fpath}/{name}')
		
		with open(f'{fpath}/{name}/{name}.tsv', 'w') as fp:
			for i, row_id in enumerate(dataset[name]):
				row = dataset[name][row_id]
				header = sorted(row.keys())
				
				if i == 0:
					fp.write('\t'.join(header))
					fp.write('\n')
				
				values = [str(row[col]) for col in header]
				line = '\t'.join(values)
				fp.write(f'{line}\n')


def main(args):
	mimic_notes_fpath = args.mimic_notes
	anno_data_path = args.anno_data
	outputdir = args.outputdir

	dataset = {
		'gold': 'gold.pain_complications.mimic.row_ids.tsv',
		'unlabeled': 'unlabeled.pain_complications.mimic.row_ids.tsv'
	}

	print("Loading MIMIC-III notes ...")
	for name in dataset:
		dataset[name] = load_row_ids(f'{anno_data_path}/{dataset[name]}')
		dataset[name] = load_clinical_notes(dataset[name], mimic_notes_fpath)
		print("... loaded "+f'{len(dataset[name])} {name}' + " documents.")

	print("Processing MIMIC-III notes...")
	process_clinical_notes(dataset['gold'])
	process_clinical_notes(dataset['unlabeled'])

	print("Writing TSV output ...")
	dump_tsvs(dataset, outputdir)

	print("Done!")

if __name__ == '__main__':

	argparser = argparse.ArgumentParser()
	argparser.add_argument("-m", "--mimic_notes", type=str, required=True,  help="path to mimic 1.4 NOTEEVENTS.csv.gz file")
	argparser.add_argument("-a", "--anno_data", type=str,  required = True,  help="directory containing TSV files specifying gold and unlabeled MIMIC note row IDs")
	argparser.add_argument("-o", "--outputdir", type=str, required=True, help="output directory")
	
	args = argparser.parse_args()

	main(args)
