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

        push("sdc.registry.jetbrains.space/p/pythonProject/docker/python_custom_img") {
            tags{
                +"0.0.1"
            }
        }
    }
}