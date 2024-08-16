#!/bin/bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./env.sh

get_attribute_from_tfstate "STREAM_OCID" "starter_stream" "id"
get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"
get_attribute_from_tfstate "STREAM_MESSAGE_ENDPOINT" "starter_stream" "messages_endpoint"
# Not used anymore ?
get_attribute_from_tfstate "STREAM_POOL_OCID" "starter_stream_pool" "id"
get_attribute_from_tfstate "STREAM_BOOSTRAPSERVER" "starter_stream_pool" "kafka_settings[0].bootstrap_servers"

get_attribute_from_tfstate "FN_OCID" "starter_fn_function" "id"
get_attribute_from_tfstate "FN_INVOKE_ENDPOINT" "starter_fn_function" "invoke_endpoint"

get_id_from_tfstate "PRIVATE_SUBNET_OCID" "starter_private_subnet" 

echo 
echo "--------------------------"
echo "OCI SEARCH LAB Environment"
echo "--------------------------"
# echo "TENANCY_NAME=$TENANCY_NAME"
echo
echo "-- STREAMING CONNECTION --------------------------"
echo "STREAM_MESSAGE_ENDPOINT=$STREAM_MESSAGE_ENDPOINT"
echo "STREAM_OCID=$STREAM_OCID"
echo "STREAM_USERNAME=$TENANCY_NAME/$TF_VAR_username/$STREAM_OCID"
echo
echo "-- FUNCTION CONNECTION ---------------------------"
echo "FUNCTION_ENDPOINT=$FN_INVOKE_ENDPOINT/20181201/functions/$FN_OCID"

# Deploy compute simplified
cp -r src/compute/* $TARGET_DIR/compute/.
scp -r -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path $TARGET_DIR/compute/* opc@$BASTION_IP:/home/opc/.
ssh -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path opc@$BASTION_IP "export TF_VAR_language=python;export FN_INVOKE_ENDPOINT=\"$FN_INVOKE_ENDPOINT\";export FN_OCID=\"$FN_OCID\";export STREAM_MESSAGE_ENDPOINT=\"$STREAM_MESSAGE_ENDPOINT\";export STREAM_OCID=\"$STREAM_OCID\";export DB_USER=\"$TF_VAR_db_user\";export DB_PASSWORD=\"$TF_VAR_db_password\";export DB_URL=\"$DB_URL\"; bash compute_bootstrap.sh 2>&1 | tee -a compute_bootstrap.log"

# oci os object bulk-upload -bn psql-public-bucket -ns $TF_VAR_namespace --overwrite --src-dir ../sample_files

echo
echo "-- SEARCH_URL -------"
echo "https://${APIGW_HOSTNAME}/app/"
echo "http://$BASTION_IP/"
echo
echo "Please wait 5 mins. The server is starting." 
