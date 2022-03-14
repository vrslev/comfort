variable "FRAPPE_VERSION" {}

# Shortcut for tagging images locally.
# In GitHub Actions using https://github.com/docker/metadata-action.
variable "TAG" {}

group "default" {
    targets = ["frontend", "backend"]
}

target "frontend" {
    dockerfile = "docker/frontend.Dockerfile"
    tags = ["cr.yandex/crpdmuh1072ntg30t18g/comfort-nginx:${TAG}"]
    args = {
      FRAPPE_VERSION = FRAPPE_VERSION
    }
}

target "backend" {
    dockerfile = "docker/backend.Dockerfile"
    tags = ["cr.yandex/crpdmuh1072ntg30t18g/comfort-worker:${TAG}"]
    args = {
      FRAPPE_VERSION = FRAPPE_VERSION
    }
}
