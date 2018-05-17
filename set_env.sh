export APPHOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export SNORKELHOME="$APPHOME/snorkel"

echo "app home directory: $APPHOME"
echo "snorkel home directory: $SNORKELHOME"

export PYTHONPATH="$PYTHONPATH:$APPHOME:$SNORKELHOME:$SNORKELHOME/treedlib"
export PATH="$PATH:$APPHOME:$SNORKELHOME:$SNORKELHOME/treedlib"
echo "$PYTHONPATH"
echo "Environment variables set!"
