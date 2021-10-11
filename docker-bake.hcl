variable "FRAPPE_VERSION" {}

target "frappe-version" {
  args = {
    FRAPPE_VERSION = FRAPPE_VERSION
  }
}

group "default" {
    targets = ["nginx", "worker"]
}

target "nginx" {
    inherits = ["frappe-version"]
    dockerfile = "docker/nginx.Dockerfile"
}

target "worker" {
    inherits = ["frappe-version"]
    dockerfile = "docker/worker.Dockerfile"
}
