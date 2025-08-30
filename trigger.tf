resource "aws_instance" "trigger" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  
  vpc_security_group_ids = ["sg-12345"]
  
  user_data = <<-EOF
    #!/bin/bash
    echo "export SECRET=${var.secret}" >> /etc/environment
  EOF

  tags = {
    Name = "trigger-instance"
  }

  root_block_device {
    encrypted = true
  }

  source_dest_check = false

  dynamic "user_data" {
    for_each = [var.user_data_commands]
    
    content {
      content = user_data.value
    }
  }

  provisioner "local-exec" {
    command = "echo ${var.secret} > /secret && chmod 600 /secret"
    when    = create
  }

  depends_on = [aws_security_group_rule.allow_ssh]

  lifecycle {
    create_before_destroy = true
  }
}

variable "secret" {
  description = "Secret key"
  type        = string
  sensitive   = true
}

variable "user_data_commands" {
  description = "List of user data commands"
  type        = list(object({
    value      = string
  }))
}