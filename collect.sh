#!/bin/bash
# #########################################################
# COLLECT.sh
# USAGE: ./collect.sh {YEAR:2019}
# #########################################################
# USER DEFINE VARIABLES
HOST=localhost
PORT=5000
ENTITY=races

# VARIDATE ARGUMENTS
CMDNAME=`basename $0`
if [ $# -ne 1 ]; then
  echo "Usage: ${CMDNAME} YEAR" 1>&2
  exit 1
fi
YEAR=$1

# BULK COLLECT RACE
for i in `seq 1 12`
do
  MONTH=`printf %02d $i`
  echo "`date "+%Y%-m%-d %H:%M:%S"` [RUN] COLLECTING FOR ${YEAR}/${MONTH}"
  echo `curl -s -X POST ${HOST}:${PORT}/${ENTITY} -d "YYYYMM=${YEAR}${MONTH}"`
done

echo "`date "+%Y%-m%-d %H:%M:%S"` [END] FINISH COLLECTION FOR ${YEAR}"
exit 0
