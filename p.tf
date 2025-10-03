# insecure example: writes a file with a hardcoded password (ANTI-PATTERN)
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = ">= 2.0"
    }
  }
}

provider "local" {}

resource "local_file" "hardcoded_creds" {
  filename        = "${path.module}/db_creds.txt"
  file_permission = "0600"

  content = <<EOF
username = "admin"
password = "HardC0dedP@ssw0rd!"
EOF
}
