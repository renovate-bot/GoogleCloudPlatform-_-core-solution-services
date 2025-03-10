#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <project-id> <firebase-app-name> <domain-name> <contact-email>"
  exit 1
fi

PROJECT_ID=$1
FIREBASE_APP_NAME=$2
DOMAIN_NAME=$3
CONTACT_EMAIL=$4

# Determine the base directory of the repository
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Navigate to the webapp directory
WEBAPP_DIR="$BASE_DIR/components/frontend_react/webapp"
echo "Changing directory to $WEBAPP_DIR..."
cd "$WEBAPP_DIR" || { echo "Failed to change directory to $WEBAPP_DIR. Please run this script from the components/frontend_react directory."; exit 1; }

# Call sub-scripts
echo "Installing dependencies..."
bash "$BASE_DIR/deployment_scripts/1_deploy_install_dependencies.sh"

echo "Configuring Firebase..."
bash "$BASE_DIR/deployment_scripts/2_deploy_configure_firebase.sh" "$PROJECT_ID" "$FIREBASE_APP_NAME"

echo "Populating environment files..."
bash "$BASE_DIR/deployment_scripts/3_deploy_set_env_vars.sh"

echo "Building and deploying the app..."
bash "$BASE_DIR/deployment_scripts/4_deploy_build_and_deploy.sh"

echo "Installation and deployment complete."