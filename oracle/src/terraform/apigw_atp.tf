resource oci_apigateway_gateway starter_apigw_public {
  compartment_id = local.lz_appdev_cmp_ocid
  display_name  = "${var.prefix}-apigw-public"
  endpoint_type = "PUBLIC" 
  subnet_id = data.oci_core_subnet.starter_public_subnet.id
  freeform_tags = local.freeform_tags       
}

locals {
  db_root_url = replace(data.oci_database_autonomous_database.starter_atp.connection_urls[0].apex_url, "/ords/apex", "" )
}

output db_root_url {
  value = local.db_root_url
}


resource "oci_apigateway_deployment" "starter_apigw_public_deployment" {
  compartment_id = local.lz_appdev_cmp_ocid
  display_name   = "${var.prefix}-apigw-public-deployment"
  gateway_id     = oci_apigateway_gateway.starter_apigw_public.id
  path_prefix    = "/"
  specification {
    routes {
      path    = "/{pathname*}"
      methods = [ "ANY" ]
      backend {
        type = "HTTP_BACKEND"
        url    = "${local.db_root_url}/$${request.path[pathname]}"
        connect_timeout_in_seconds = 60
        read_timeout_in_seconds = 120
        send_timeout_in_seconds = 120            
      }
      request_policies {
          header_transformations {
            set_headers {
              items {
                  name = "Host"
                  values = ["$${request.headers[Host]}"]
              }
            }
          }
        }
    }        
  }
  freeform_tags = local.freeform_tags
}