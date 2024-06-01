#!/bin/bash
PROJECT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export BIN_DIR=$PROJECT_DIR/bin

# Env Variables
export TF_VAR_prefix="psql"

export TF_VAR_ui_type="html"
export TF_VAR_db_type="psql"
export TF_VAR_license_model="LICENSE_INCLUDED"
export TF_VAR_oke_type="managed"
export TF_VAR_deploy_type="function"
export TF_VAR_language="java"
export TF_VAR_db_user="postgres"

# export TF_VAR_compartment_ocid=ocid1.compartment.xxxxx
# TF_VAR_db_password : Min length 12 characters, 2 lowercase, 2 uppercase, 2 numbers, 2 special characters. Ex: LiveLab__12345
#   If not filled, it will be generated randomly during the first build.
export TF_VAR_db_password="__TO_FILL__"
# TF_VAR_auth_token : See doc: https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrygettingauthtoken.htm
export TF_VAR_auth_token="__TO_FILL__"

if [ -f $PROJECT_DIR/../group_common_env.sh ]; then
  . $PROJECT_DIR/../group_common_env.sh
elif [ -f $PROJECT_DIR/../../group_common_env.sh ]; then
  . $PROJECT_DIR/../../group_common_env.sh
elif [ -f $HOME/.oci_starter_profile ]; then
  . $HOME/.oci_starter_profile
fi

# Creation Details
export OCI_STARTER_CREATION_DATE=2024-06-01-18-11-43-021126
export OCI_STARTER_VERSION=2.0
export OCI_STARTER_PARAMS="prefix,java_framework,java_vm,java_version,ui_type,db_type,license_model,mode,infra_as_code,db_password,oke_type,deploy_type,language"

# Get other env variables automatically (-silent flag can be passed)
. $BIN_DIR/auto_env.sh $1
