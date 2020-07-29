set -euxo pipefail

if [ -n "$1" ]; then # First parameter = target destination
	DEST=$1
else
	DEST="."
fi

RSYNC_SRC="rsync://piscanner/share"
SLEEP_TIME=10

echo "Synchronization started from $RSYNC_SRC to $DEST every ${SLEEP_TIME}s"

while [ : ]
do
    rsync -aP "$RSYNC_SRC" "$DEST"
    sleep $SLEEP_TIME
done
