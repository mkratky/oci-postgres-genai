export DB_USER="vector"
export DB_PASSWORD="##DB_PASSWORD##"
export DB_URL="##DB_URL##"

export STREAM_OCID="##STREAM_OCID##"
export STREAM_MESSAGE_ENDPOINT="##STREAM_MESSAGE_ENDPOINT##"
export FN_OCID="##FN_OCID##"
export FN_INVOKE_ENDPOINT="##FN_INVOKE_ENDPOINT##"
export TF_VAR_compartment_ocid=`curl -s -H "Authorization: Bearer Oracle" -L http://169.254.169.254/opc/v2/instance/ | jq -r .compartmentId`
export TF_VAR_region=`curl -s -H "Authorization: Bearer Oracle" -L http://169.254.169.254/opc/v2/instance/ | jq -r .canonicalRegionName`
