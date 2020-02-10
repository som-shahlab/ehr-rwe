# Tutorials

## I. Quick Start

### 1. Downloading and Preprocessing MIMIC-III Data

This tutorial requires clinical notes from the [MIMIC-III](https://mimic.physionet.org/) dataset. Instructions for obtaining access are available [here](https://mimic.physionet.org/gettingstarted/access/). If you already have an account you can run the following script to generate all data needed for this tutorial. This will prompt you for your PhysioNet password. 

	init.sh <PHYSIONET_USERNAME> 

### 2. Tutorial Notebooks

We've put together Jupyter notebooks that walk you through the process of building a weakly labeled training set. 

- `1_Building_Training_Sets.ipynb` Demonstrates how to: 
	1. Load documents
	2. Define a tagging pipeline
	3. Write and apply labeling functions to data
	4. Train a Snorkel label model
	5. Export a probabalistically (weakly) labeled training set 



- `2_Training_BioBERT_EndModel.ipynb` **Coming Soon!**
   1. Load weakly labeled data
   2. Train a BioBERT model for relational inference. 

## II. Dataset Preprocessing

### 1. Downloading MIMIC-III Data

Once you have an MIMIC-III account, you can download the `NOTEEVENTS.csv.gz` file directly [here](https://physionet.org/content/mimiciii/1.4/NOTEEVENTS.csv.gz) or via the command line. 

	wget -r -N -c -np \
	     --user <PHYSIONET_USERNAME> \
	     --ask-password \
	     https://physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz
	
The file `NOTEEVENTS.csv.gz` should be moved to [`../data/corpora/`](../data/corpora/)

### 2. Extracting Dataset Splits

Next, we'll extract pre-defined train/test splits from the notes file. This script also applies some minimal preprocessing to assign each note a creation timestamp and transform all MIMIC blinded date mentions into realistic time ranges. This is required so that date math labeling functions work as intended. See [`../preprocessing/prep_mimic.py`](../preprocessing/prep_mimic.py) and [`../preprocessing/mimic_to_tsv.py`](../preprocessing/mimic_to_tsv.py) for details. 

	python ../preprocessing/mimic_to_tsv.py \
		--mimic_notes ../data/corpora/NOTEEVENTS.csv.gz \
		--anno_data ../data/annotations/ \
		--outputdir ../data/corpora/

### 3. NLP Preprocessing
Finally, we preprocess splits using our NLP pipeline. This transforms raw text into tokenized sentences formatted in a simple JSON container object. 

	python ../preprocessing/parse.py \
		--inputdir  ../data/corpora/gold/ \
		--outputdir  ../data/corpora/ \
		--prefix mimic_gold \
		--n_procs 4 \
		--disable ner,tagger,parser \
		--batch_size 5000

	python ../preprocessing/parse.py \
		--inputdir  ../data/corpora/unlabeled/ \
		--outputdir  ../data/corpora/ \
		--prefix mimic_unlabeled \
		--n_procs 4 \
		--disable ner,tagger,parser \
		--batch_size 5000

## III. Tagger Details

A common design pattern in clinical text is to select 1 or more onotologies (e.g., SNOMEDCT_US) from the Unified Medical Language System (UMLS) and treat all exact string matches as your set of concepts.
 
In this library, concept tagging is rule-based, relying on custom dictionary and regular expression matchers to define types of interest. In addition to custom concepts, we provide code for tagging section headers and TIMEX3 (explicit datetime) mentions. 

- `Clinical Concept` `∈ {SNOMEDCT_US}`
- `Misc.` `∈ {TIMEX3, HEADER}`

Each clinical concept mention is associated with the following attributes:

- `Parent Section Heading` (i.e., the parent section of the target concept)
- `Negation` `∈ {0,1}`
- `Hypothetical` `∈ {0,1}`
- `Historical	` `∈ {0,1}` 
- `Time Delta` `∈ ℤ <=0` (in days preceeding document timestamp)
- `Laterality` `∈ {L, R, Bi}` (e.g., left/right/bilateral hip pain}
- `Family` `∈ {0,1}` Does the concept refer to the patient or their family?

In the current formulation, each of these maps to a collection of 1 or more labeling functions. Currently, we take the logical OR over these functions to assign attributes, however you can treat each attribute as a weakly supervised task and train a machine learning model if you need better performance.  
