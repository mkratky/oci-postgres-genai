variable "vcn_ocid" {}
variable "public_subnet_ocid" {}
variable "app_subnet_ocid" {}
variable "db_subnet_ocid" {}

data "oci_core_vcn" "starter_vcn" {
  vcn_id = var.vcn_ocid
}

data "oci_core_subnet" "starter_public_subnet" {
  subnet_id = var.public_subnet_ocid
}

data "oci_core_subnet" "starter_app_subnet" {
  subnet_id = var.app_subnet_ocid
}

data "oci_core_subnet" "starter_db_subnet" {
  subnet_id = var.db_subnet_ocid
}
