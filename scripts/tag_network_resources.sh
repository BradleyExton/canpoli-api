#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVERLESS_FILE="${ROOT_DIR}/serverless.yml"

usage() {
  cat <<'USAGE'
Usage:
  tag_network_resources.sh [options] --tag Key=Value [--tag Key=Value ...]

Options:
  --vpc VPC_ID           VPC to tag (optional)
  --subnet SUBNET_ID     Subnet to tag (repeatable; optional)
  --sg SG_ID             Security group to tag (repeatable; optional)
  --region REGION        AWS region (optional)
  --dry-run              Use AWS CLI dry-run mode
  --help                 Show this help

Notes:
  - If --subnet or --sg are not provided, IDs are inferred from serverless.yml.
  - At least one --tag must be provided.
USAGE
}

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI not found. Install/configure AWS CLI first." >&2
  exit 1
fi

VPC_ID=""
REGION=""
DRY_RUN="false"
TAGS=()
SUBNET_IDS=()
SG_IDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vpc)
      VPC_ID="$2"
      shift 2
      ;;
    --subnet)
      SUBNET_IDS+=("$2")
      shift 2
      ;;
    --sg)
      SG_IDS+=("$2")
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --tag)
      TAGS+=("$2")
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift 1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ${#TAGS[@]} -eq 0 ]]; then
  echo "At least one --tag Key=Value is required." >&2
  usage
  exit 1
fi

if [[ ${#SUBNET_IDS[@]} -eq 0 && -f "$SERVERLESS_FILE" ]]; then
  mapfile -t SUBNET_IDS < <(grep -Eo 'subnet-[0-9a-f]+' "$SERVERLESS_FILE" | sort -u)
fi

if [[ ${#SG_IDS[@]} -eq 0 && -f "$SERVERLESS_FILE" ]]; then
  mapfile -t SG_IDS < <(grep -Eo 'sg-[0-9a-f]+' "$SERVERLESS_FILE" | sort -u)
fi

RESOURCES=()
if [[ -n "$VPC_ID" ]]; then
  RESOURCES+=("$VPC_ID")
fi
RESOURCES+=("${SUBNET_IDS[@]}")
RESOURCES+=("${SG_IDS[@]}")

# Deduplicate resources
if [[ ${#RESOURCES[@]} -eq 0 ]]; then
  echo "No resources found. Provide --vpc/--subnet/--sg or ensure serverless.yml contains IDs." >&2
  exit 1
fi

# Build AWS CLI tag format
AWS_TAGS=()
for tag in "${TAGS[@]}"; do
  if [[ "$tag" != *"="* ]]; then
    echo "Invalid tag format: $tag (expected Key=Value)" >&2
    exit 1
  fi
  key="${tag%%=*}"
  value="${tag#*=}"
  if [[ -z "$key" ]]; then
    echo "Invalid tag key in: $tag" >&2
    exit 1
  fi
  AWS_TAGS+=("Key=${key},Value=${value}")
done

AWS_ARGS=(ec2 create-tags --resources)
AWS_ARGS+=("${RESOURCES[@]}")
AWS_ARGS+=(--tags)
AWS_ARGS+=("${AWS_TAGS[@]}")

if [[ -n "$REGION" ]]; then
  AWS_ARGS+=(--region "$REGION")
fi
if [[ "$DRY_RUN" == "true" ]]; then
  AWS_ARGS+=(--dry-run)
fi

aws "${AWS_ARGS[@]}"

