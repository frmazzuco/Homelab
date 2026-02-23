variable "tenancy_ocid" {
  type        = string
  description = "OCID da tenancy."
}

variable "user_ocid" {
  type        = string
  description = "OCID do usuario que possui a API key."
}

variable "fingerprint" {
  type        = string
  description = "Fingerprint da API key."
}

variable "private_key_path" {
  type        = string
  description = "Caminho para a private key usada na autenticacao do provider."
}

variable "region" {
  type        = string
  description = "Regiao OCI, por exemplo sa-saopaulo-1."
}

variable "compartment_ocid" {
  type        = string
  description = "OCID do compartment onde os recursos serao criados."
}

variable "availability_domain_index" {
  type        = number
  description = "Indice do Availability Domain (0 = AD-1, 1 = AD-2, ...)."
  default     = 0
}

variable "ssh_public_key_path" {
  type        = string
  description = "Caminho para a chave publica SSH usada no acesso a instancia."
}

variable "additional_ssh_public_keys" {
  type        = list(string)
  description = "Chaves publicas SSH adicionais (formato authorized_keys)."
  default     = []
}

variable "ssh_user" {
  type        = string
  description = "Usuario SSH padrão da imagem (ex: opc para Oracle Linux, ubuntu para Ubuntu)."
  default     = "opc"
}

variable "gateway_repo_url" {
  type        = string
  description = "Repositorio Git clonado no bootstrap para executar o gateway OpenClaw."
  default     = "https://github.com/openclaw/openclaw.git"
}

variable "gateway_repo_dir" {
  type        = string
  description = "Diretorio destino do clone no host remoto."
  default     = "/opt/openclaw"
}

variable "allowed_ssh_cidrs" {
  type        = list(string)
  description = "CIDRs permitidos para SSH. Use seu IP publico/32."
}

variable "vcn_cidr" {
  type        = string
  description = "CIDR da VCN."
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  type        = string
  description = "CIDR da subnet publica."
  default     = "10.0.1.0/24"
}

variable "instance_shape" {
  type        = string
  description = "Shape da instancia Always Free."
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  type        = number
  description = "OCPUs para o shape flex."
  default     = 4
}

variable "instance_memory_gbs" {
  type        = number
  description = "Memoria (GB) para o shape flex."
  default     = 26
}

variable "boot_volume_size_gbs" {
  type        = number
  description = "Tamanho do boot volume em GB."
  default     = 50
}

variable "operating_system" {
  type        = string
  description = "Sistema operacional da imagem."
  default     = "Oracle Linux"
}

variable "operating_system_version" {
  type        = string
  description = "Versao do sistema operacional da imagem."
  default     = "8"
}

variable "allowed_tcp_ports" {
  type        = list(number)
  description = "Portas TCP extras para liberar (alem de 22)."
  default     = []
}

variable "allowed_tcp_cidrs" {
  type        = list(string)
  description = "CIDRs permitidos para as portas extras."
  default     = []
}
