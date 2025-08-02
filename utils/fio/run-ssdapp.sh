#!/bin/bash

source ../setup-server.sh

help()
{
    echo "Usage: run-ssdapp
               [ -H | --home (home directory)]
               [ -E | --exp (experiment name, this name will be used to create output directories; default='rdma-test')]
               [ -o | --outdir (name of the output directory which will store the records; default=test) ] 
               [ -c | --cpu_mask (comma separated CPU mask to run the app on, recommended to run on NUMA node local to the NIC for maximum performance; default=0) ]
               [ --bs (FIO Block Size in bytes, default=4k)]
               [ --iodepth (FIO I/O depth, default=1)]
               [ --rw (FIO test type, default=read)]
               [ --submit_batch (FIO submit batch size, default=1)]
               [ --comp_batch (FIO min completion batch size, default=1)]
               [ --t | --num_threads (number of threads to use, default=1)]
               [ -h | --help  ]"
    exit 2
}

SHORT=H:,E:,o:,c:,t:,h
LONG=home:,exp:,outdir:,cpu_mask:,bs:,iodepth:,rw:,submit_batch:,comp_batch:,num_threads:,help
OPTS=$(getopt -a -n run-ssdapp --options $SHORT --longoptions $LONG -- "$@")

VALID_ARGUMENTS=$# # Returns the count of arguments that are in short or long options

if [ "$VALID_ARGUMENTS" -eq 0 ]; then
  help
fi

eval set -- "$OPTS"

#default values
CPU_MASK="64-79"
HOME=$DEP_DIR
EXP="fio-test"
OUT_DIR="/tmp/fio-test"
SETUP_DIR=$HOME/Fast-and-Safe-IO-Memory-Protection/utils
EXP_DIR=$HOME/Fast-and-Safe-IO-Memory-Protection/utils/fio
MLC_DIR=$HOME/mlc/Linux

fio_template="$EXP_DIR/jobfiles/bs_rw_logging.fio"

# FIO default parameters
BS=4k
IODEPTH=8
RW="randread"
SUBMIT_BATCH=4
COMP_BATCH=4
NUM_THREADS=8

UNAME=$CLIENT_USERNAME
SSH_HOSTNAME=$CLIENT_SSH_IP
PASSWORD=$CLIENT_PWD


while :
do
  case "$1" in
    -H | --home ) HOME="$2"; shift 2 ;;
    -E | --exp ) EXP="$2"; shift 2 ;;
    -o | --outdir) OUT_DIR="$2"; shift 2 ;;
    -c | --cpu_mask ) CPU_MASK="$2"; shift 2 ;;
    --bs ) BS="$2"; shift 2 ;;
    --iodepth ) IODEPTH="$2"; shift 2 ;;
    --rw ) RW="$2"; shift 2 ;;
    --submit_batch ) SUBMIT_BATCH="$2"; shift 2 ;;
    --comp_batch ) COMP_BATCH="$2"; shift 2 ;;
    -t | --num_threads ) NUM_THREADS="$2"; shift 2 ;;
    -h | --help) help ;;
    --) shift; break ;;
    *) echo "Unexpected option: $1"; help ;;
  esac
done



# export SIZE=$BS
# export IODEPTH=$IODEPTH
echo "Running $RW test with block size $BS..."
# Generate a concrete .fio file for this test
fio_jobfile="/tmp/ladio_${RW}_${BS}_logging.fio"
log_path=$DEP_DIR/Fast-and-Safe-IO-Memory-Protection/utils/logs/$OUT_DIR
mkdir -p "$log_path"
sed "s|\${SIZE}|$BS|g; s|\${IODEPTH}|$IODEPTH|g; s|\${RW}|$RW|g; s|\${OUT_DIR}|$log_path|g; s|\${SUBMIT_BATCH}|$SUBMIT_BATCH|g; s|\${COMP_BATCH}|$COMP_BATCH|g; s|\${NUM_THREADS}|$NUM_THREADS|g; s|\${CPU_MASK}|$CPU_MASK|g;" "$fio_template" > "$fio_jobfile"

sudo -E taskset -c $CPU_MASK fio $fio_jobfile --terse=3 --output=$log_path/fio_bw_${RW}_${BS} > /dev/null 2>&1 < /dev/null &
WRAPPER_PID=$!
sleep 1 # Wait for the wrapper to start
FIO_PID=$(pgrep -P $WRAPPER_PID fio)  # Get child PID of the wrapper (actual fio process)
echo $FIO_PID > /tmp/fio_pid.txt
echo "FIO process started with PID: $FIO_PID"

# sleep 10
# sudo pkill -x fio
