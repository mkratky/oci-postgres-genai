variable idcs_domain_name { default = "Default" }
variable idcs_url { default = "" }

data "oci_identity_domains" "starter_domains" {
    #Required
    compartment_id = var.tenancy_ocid
    display_name = var.idcs_domain_name
}

locals {
  idcs_url = (var.idcs_url!="")?var.idcs_url:data.oci_identity_domains.starter_domains.domains[0].url
}

resource "oci_identity_domains_dynamic_resource_group" "search-fn-dyngroup" {
    #Required
    provider       = oci.home    
    display_name = "${var.prefix}-fn-dyngroup"
    idcs_endpoint = local.idcs_url
    matching_rule = "ALL {resource.type = 'fnfunc', resource.compartment.id = '${local.lz_app_cmp_ocid}'}"
    schemas = ["urn:ietf:params:scim:schemas:oracle:idcs:DynamicResourceGroup"]
}

resource "oci_identity_domains_dynamic_resource_group" "search-bastion-dyngroup" {
    #Required
    provider       = oci.home    
    display_name = "${var.prefix}-bastion-dyngroup"
    idcs_endpoint = local.idcs_url
    matching_rule = "ALL {instance.id = '${oci_core_instance.starter_bastion.id}'}"
    schemas = ["urn:ietf:params:scim:schemas:oracle:idcs:DynamicResourceGroup"]
}

resource "time_sleep" "wait_30_seconds" {
  depends_on = [ oci_identity_domains_dynamic_resource_group.search-bastion-dyngroup, oci_identity_domains_dynamic_resource_group.search-fn-dyngroup ]
  create_duration = "30s"
}

resource "oci_identity_policy" "starter_search_policy" {
    provider       = oci.home    
    depends_on     = [ time_sleep.wait_30_seconds ]
    name           = "${var.prefix}-policy"
    description    = "${var.prefix} policy"
    compartment_id = local.lz_serv_cmp_ocid

    statements = [
        "Allow dynamic-group ${var.prefix}-fn-dyngroup to manage objects in compartment id ${local.lz_serv_cmp_ocid}",
        "Allow dynamic-group ${var.prefix}-bastion-dyngroup to manage all-resources in compartment id ${local.lz_serv_cmp_ocid}",
        "Allow dynamic-group ${var.prefix}-bastion-dyngroup to manage stream-family in compartment id ${local.lz_serv_cmp_ocid}"
        # "Allow dynamic-group ${var.idcs_domain_name}/${var.prefix}-fn-dyngroup to manage objects in compartment id ${var.compartment_ocid}",
        # "Allow dynamic-group ${var.idcs_domain_name}/${var.prefix}-bastion-dyngroup to manage all-resources in compartment id ${var.compartment_ocid}",
        # "Allow dynamic-group ${var.idcs_domain_name}/${var.prefix}-bastion-dyngroup to manage stream-family in compartment id ${var.compartment_ocid}"
    ]
}

