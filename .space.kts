job("Prepare Docker image") {
    // do not run on git push
    startOn {
        gitPush { enabled = false }
    }

    kaniko {
        build {
            dockerfile = "./Dockerfile"
            labels["vendor"] = "sdc"
        }

        push("sdc.registry.jetbrains.space/p/main/sdc-python/myimage") {
            tags{
                +"0.0.1"
            }
        }
    }
}

job("Run tests, build, publish") {
    container(image = "sdc.registry.jetbrains.space/p/main/sdc-python/myimage:0.0.1") {
        // specify URL of the package index using env var
        env["URL"] = "https://packages.jetbrains.space/pypi/p/my-python-project/mypypi/legacy"

        // We suppose that your project has default build configuration -
        // the built package is saved to the ./dist directory
        shellScript {
            content = """
                echo Run tests...
                pytest
            """
        }
    }
}