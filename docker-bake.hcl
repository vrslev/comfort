variable "FRAPPE_VERSION" {}

# Shortcut for tagging images locally.
# In GitHub Actions using https://github.com/docker/metadata-action.
variable "TAG" {}

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
    tags = ["cr.yandex/crpdmuh1072ntg30t18g/comfort-nginx:${TAG}"]
}

target "worker" {
    inherits = ["frappe-version"]
    dockerfile = "docker/worker.Dockerfile"
    tags = ["cr.yandex/crpdmuh1072ntg30t18g/comfort-worker:${TAG}"]
}
