# Weakly Supervised Clinical Text Classification 

This library provides tools for rapidly building clinical text classification tasks using [weakly supervised machine learning](https://hazyresearch.github.io/snorkel/blog/ws_blog_post.html). Obtaining labeled training data is a common roadblock to using machine learning with unstructured medical data such as patient notes. Weakly supervised methods allow domain experts to quickly refine training set construction, enabling the use of modern deep learning without time consuming manual training data curation. 

This library enables integrating common clinical text heuristics and other noisy labeling sources for use with Stanford's weak supervision framework [Snorkel](https://github.com/snorkel-team/snorkel). We developed these tools while working on our npj Digital Medicine paper ["Medical Device Surveillance with Electronic Health Records"](https://www.nature.com/articles/s41746-019-0168-z) focusing on lightweight code that makes it easier to extract real-world patient outcomes from clinical notes. 

### Features (2/4/2020)
- Fast text tokenization, sentence boundary detection, and NLP preprocesssing using custom [spaCy](https://spacy.io/) modules optimized for clinical and biomedical text.
- Lightweight information extraction pipeline for span and relation classification with multiprocessing support via [Joblib](https://joblib.readthedocs.io/en/latest/) and [Dask](https://dask-ml.readthedocs.io/en/latest/joblib.html).
- Tagging support for [UMLS](https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/index.html) concepts, [TIMEX3](https://en.wikipedia.org/wiki/TimeML#TIMEX3), and custom dictionary/regular expression concept matching.
- Labeling functions for common, clinical concept attribute classification tasks including:
  * Parent Section Header
  * Negation / Hypothetical / Historical
  * Datetime Canonicalization
  * Event Time Delta (in days preceding doc timestamp)
  * Laterality
  * Family vs. Patient-linked Concept
 

## Contents
* [Installation](#installation)
* [Tutorials](#tutorials)
* [Reproducing Paper Results](#reproducing)
* [Citations](#citations)

## Installation

All requirements can be installed via conda. To create a new virtual enviornment and install all dependencies

	conda create --yes -n rwe python=3.6
	conda activate rwe
	conda install pytorch==1.1.0 -c pytorch
	conda install snorkel==0.9.3 -c conda-forge
	conda install --name rwe -c conda-forge -c pytorch --file requirements.txt
	python -m spacy download en
	
Once the environment is configured, you can launch the tutorial notebooks with

	conda activate rwe
	cd tutorials
	jupyter notebook

## Tutorials

### Fast Document Preprocessing 
The [spaCy](https://spacy.io/) pipeline and documentation for processing large document collections is found at [`preprocessing/`](preprocessing/)

### Building Training Sets

We've provided a tutorial for tagging clinical concepts and doing relational inference with MIMIC-III data at [`tutorials/`](tutorials/)


## Reproducing Paper Results

This framework was used in our paper ["Medical Device Surveillance with Electronic Health Records"](https://www.nature.com/articles/s41746-019-0168-z) where we described two relation extraction tasks `{Pain, Anatomy}` and `{Complication, Implant}` used to evaluate the real-world performance of artifical hip replacements using Stanford Healthcare data. 
  
The original code was written using [Snorkel v0.7](https://github.com/snorkel-team/snorkel-extraction) and [Snorkel MeTaL]() which are both now deprecated. We've written a new simple tutorial pipeline for use with the latest release of [Snorkel v0.9.4](https://github.com/snorkel-team/snorkel) using MIMIC-III clinical notes. This new library incorporates many of the lessons we learned while building our original models. We strongly recomend using this tutorial as the basis for any new projects. 

The complete labeling functions used in the paper are also available for reference 

* **{Pain, Anatomy}** `legacy/pain.py`
* **{Complication, Implant}**  `legacy/implant_complications.ipynb`
  

## Citations

If you make use of any of these tools, please cite

	@article{Callahan2019,
		author  = {Callahan, Alison and 
		           Fries, Jason A. and 
		           R{\'e}, Christopher and
		           Huddleston, James I. and 
		           Giori, Nicholas J. and
		           Delp, Scott and 
		           Shah, Nigam H.},
		title   = {Medical device surveillance with electronic health records},
		journal = {{npj Digital Medicine}},
		volume  = 2,
		number  = 1,
		pages   = 94,
		year    = 2019,
		url     = {https://www.nature.com/articles/s41746-019-0168-z.pdf},
		doi     = {10.1038/s41746-019-0168-z}
	}
	
and

	@article{RatnerVLDB2017,
	  author    = {Ratner, Alexander and
	               Bach, Stephen H. and
	               Ehrenberg, Henry R. and
	               Fries, Jason A. and
	               Wu, Sen and
	               R{\'{e}}}, Christopher 
	  title     = {Snorkel: Rapid Training Data Creation with Weak Supervision},
	  journal   = {{PVLDB}},
	  volume    = {11},
	  number    = {3},
	  pages     = {269--282},
	  year      = {2017},
	  url       = {http://www.vldb.org/pvldb/vol11/p269-ratner.pdf},
	  doi       = {10.14778/3157794.3157797}
	}


