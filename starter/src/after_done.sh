#!/bin/bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./env.sh

get_attribute_from_tfstate "STREAM_BOOSTRAPSERVER" "starter_stream_pool" "kafka_settings[0].bootstrap_servers"
get_attribute_from_tfstate "STREAM_OCID" "starter_stream_pool" "id"
get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"

get_attribute_from_tfstate "FN_OCID" "starter_fn_function" "id"
get_attribute_from_tfstate "FN_INVOKE_ENDPOINT" "starter_fn_function" "invoke_endpoint"

get_id_from_tfstate "PRIVATE_SUBNET_OCID" "starter_private_subnet" 

echo "-- Creating oss_store.jks" 
echo -n | openssl s_client -connect $STREAM_BOOSTRAPSERVER | sed -ne  '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > target/ociStreaming.cert
keytool -keystore oss_store.jks -alias OSSStream -import -file target/ociStreaming.cert -storepass changeit -noprompt
echo "File oss_store.jks created"

echo 
echo "--------------------------"
echo "OCI SEARCH LAB Environment"
echo "--------------------------"
# echo "TENANCY_NAME=$TENANCY_NAME"
echo
echo "-- STREAMING CONNECTION --------------------------"
echo "STREAM_BOOSTRAPSERVER=$STREAM_BOOSTRAPSERVER"
echo "STREAM_OCID=$STREAM_OCID"
echo "STREAM_USERNAME=$TENANCY_NAME/$TF_VAR_username/$STREAM_OCID"
echo "AUTH_TOKEN=$TF_VAR_auth_token"
echo
echo "-- FUNCTION CONNECTION ---------------------------"
echo "FUNCTION_ENDPOINT=$FN_INVOKE_ENDPOINT/20181201/functions/$FN_OCID"
echo "Done."

