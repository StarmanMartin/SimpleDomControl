job("Prepare Docker image") {
    // do not run on git push
    startOn {
        gitPush { enabled = false }
    }

    kaniko {
        build {
            file = "./Dockerfile"
            labels["vendor"] = "sdc"
        }

        push("sdc.registry.jetbrains.space/p/main/sdc-python/myimage) {
            tags{
                +"0.0.1"
            }
        }
    }
}