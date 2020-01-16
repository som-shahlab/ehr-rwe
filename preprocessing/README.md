# Clinical Text NLP Pre-processing
This pipeline uses spaCy for all NLP parsing. Pipes for clinical text
tokenization and sentence boundary detection (SBD) are reasonably fast and
accurate enough for within-sentence relational inference.

## 1. Instructions
For fast loading with Pandas, we note must be in TSV format. The TSV format
requires only 2 columns: `DOC_NAME` and `TEXT`; any other additional columns
will be treated as document metadata and added to the `metadata` field in the
final output JSON file.

If your input is a directory of text files, you can conver to TSV files
of size `batch_size` using:

	python notes_to_tsv.py \
		--inputdir <INDIR> \
		--outputdir <OUTDIR> \
		--batch_size 5000

Parse TSV files and dump to a JSON container format:

	python parse.py \
		--inputdir <INDIR> \
		--outputdir <OUTDIR> \
		--prefix mimic \
		--n_procs 4 \
		--disable ner,tagger,parser \
		--batch_size 5000

## 2. Benchmarks
- 50,000 MIMIC-III documents
- 4 core MacBook Pro 2.5Ghz mid-2015

| Time (minutes) | Disable Pipes | NLP Output |
|---------------|----------------|------------|
| 1.5 | `ner,parser,tagger` | tokens, SBD|
| 5.6 | `ner,parser` | tokens, SBD, POS tags|
| 17.9 | `ner` | tokens, SBD, POS tags, dependency tree |

## 3. JSON Output Format
The JSON format consists for a document name, a sentence offset index `i`, a list of sentences with NLP markup (e.g., POS tags), and (optional) document metadata.

```
{
"name":"7569_NURSING_OTHER_REPORT_1992373",
"sentences":[{
	"words":["CCU","Progress","Note",":","S","-","intubated","&","sedated","."],
	"abs_char_offsets":[2,6,15,19,22,23,25,35,37,44],
	"i":0}, ...],
    "metadata": {}
}
```