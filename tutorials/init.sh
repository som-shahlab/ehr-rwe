#
# Build MIMIC-III Clinical Notes Tutorial Dataset
#
# ./init.sh <PHYSIONET_USERNAME>
#
echo "PhysioNet Login: $1"

# download MIMIC notes data
MIMIC="../data/corpora/physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz"

if [ ! -f "$MIMIC" ]; then
    echo "$MIMIC does not exist, attempting to download..."
    wget -r -N -c -np --user $1 --ask-password https://physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz
	mv physionet.org ../data/corpora/
else
	echo "$MIMIC already exists"
fi

# Extract train/test splits and preprocess notes
python ../preprocessing/mimic_to_tsv.py \
    --mimic_notes $MIMIC \
    --anno_data ../data/annotations/ \
    --outputdir ../data/corpora/

# NLP Preprocessing
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