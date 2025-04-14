#!/bin/sh

SUPPORTED_ENVS="dev stage prod"
MIGRATION_FLAG=false

# Parse command line arguments
while getopts ":m" opt; do
  case ${opt} in
  m)
    MIGRATION_FLAG=true
    ;;
  \?)
    echo "Invalid option: $OPTARG" 1>&2
    exit 1
    ;;
  esac
done
shift $((OPTIND - 1))

# Check environment argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 [-m] <env>"
  echo "Supported environments: $SUPPORTED_ENVS"
  exit 1
fi

ENV=$1

if ! echo "$SUPPORTED_ENVS" | grep -wq "$ENV"; then
  echo "Error: Unsupported environment '$ENV'"
  echo "Supported environments: $SUPPORTED_ENVS"
  exit 1
fi

# Run docker compose
docker compose -f .docker/${ENV}-docker-compose.yml --env-file=.envs/.${ENV} up -d --build

# If migration flag is true, run test.sh
if [ "$MIGRATION_FLAG" = true ]; then
  sh .scripts/auto-migration.sh $ENV
fi