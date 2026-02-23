output "instance_id" {
  value = oci_core_instance.this.id
}

data "oci_core_vnic_attachments" "this" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.this.id
}

data "oci_core_vnic" "primary" {
  vnic_id = data.oci_core_vnic_attachments.this.vnic_attachments[0].vnic_id
}

output "public_ip" {
  value = data.oci_core_vnic.primary.public_ip_address
}

output "ssh_command" {
  value = "ssh ${var.ssh_user}@${data.oci_core_vnic.primary.public_ip_address}"
}
