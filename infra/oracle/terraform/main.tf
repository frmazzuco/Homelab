provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

locals {
  cloud_init = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    allowed_tcp_ports = var.allowed_tcp_ports
    ssh_user          = var.ssh_user
  })
}

data "oci_identity_availability_domains" "this" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "this" {
  compartment_id           = var.compartment_ocid
  operating_system         = var.operating_system
  operating_system_version = var.operating_system_version
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "vcn-always-free"
  dns_label      = "alwaysfree"
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  display_name   = "igw-always-free"
  vcn_id         = oci_core_vcn.this.id
}

resource "oci_core_route_table" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "rt-always-free"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "sl-always-free"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  dynamic "ingress_security_rules" {
    for_each = toset(var.allowed_ssh_cidrs)
    content {
      protocol  = "6"
      source    = ingress_security_rules.value
      stateless = false
      tcp_options {
        min = 22
        max = 22
      }
    }
  }
}

resource "oci_core_subnet" "this" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.this.id
  cidr_block                 = var.subnet_cidr
  display_name               = "subnet-always-free"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.this.id
  security_list_ids          = [oci_core_security_list.this.id]
  prohibit_public_ip_on_vnic = false
}

resource "oci_core_network_security_group" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "nsg-always-free"
}

resource "oci_core_network_security_group_security_rule" "ssh_ingress" {
  for_each = toset(var.allowed_ssh_cidrs)

  network_security_group_id = oci_core_network_security_group.this.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

locals {
  extra_ingress = flatten([
    for cidr in var.allowed_tcp_cidrs : [
      for port in var.allowed_tcp_ports : {
        cidr = cidr
        port = port
      }
    ]
  ])
  availability_domain_count = length(data.oci_identity_availability_domains.this.availability_domains)
  availability_domain_index = local.availability_domain_count == 0 ? 0 : min(var.availability_domain_index, local.availability_domain_count - 1)
}

resource "oci_core_network_security_group_security_rule" "extra_tcp_ingress" {
  for_each = {
    for rule in local.extra_ingress : "${rule.cidr}-${rule.port}" => rule
  }

  network_security_group_id = oci_core_network_security_group.this.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value.cidr
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = each.value.port
      max = each.value.port
    }
  }
}

resource "oci_core_instance" "this" {
  availability_domain = data.oci_identity_availability_domains.this.availability_domains[local.availability_domain_index].name
  compartment_id      = var.compartment_ocid
  display_name        = "always-free-2gb"
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.this.id
    assign_public_ip = true
    nsg_ids          = [oci_core_network_security_group.this.id]
  }

  metadata = {
    ssh_authorized_keys = join("\n", concat([trimspace(file(var.ssh_public_key_path))], var.additional_ssh_public_keys))
    user_data           = base64encode(local.cloud_init)
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.this.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_gbs
  }

  lifecycle {
    # Evita recriacao da VM por atualizacao automatica da imagem base da OCI.
    ignore_changes = [
      metadata["ssh_authorized_keys"],
      source_details[0].source_id
    ]
  }
}
