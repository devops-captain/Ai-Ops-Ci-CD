resource "aws_instance" "trigger" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  
  security_groups = ["sg-12345"]
  
  user_data = <<-EOF
    #!/bin/bash
    export SECRET="test123"
  EOF
}
