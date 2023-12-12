with open('../sdc_core/template_files/package.json') as f:
    deps = []
    dev_deps = []
    found_deps = False
    found_dev_deps = False
    for line in f.readlines():
        if "devDependencies" in line:
            found_dev_deps = True
            found_deps = False
        if "dependencies" in line:
            found_dev_deps = False
            found_deps = True
        elif (found_dev_deps or found_deps) and '}' in line:
            found_dev_deps = False
            found_deps = False
        elif found_dev_deps:
            dev_deps.append("* " + " = ".join([x.strip(' ",\n') for x in line.split(':')]))

        elif found_deps:
            deps.append("* " + " = ".join([x.strip(' ",\n') for x in line.split(':')]))


print("\n".join(deps))
print("\n".join(dev_deps))