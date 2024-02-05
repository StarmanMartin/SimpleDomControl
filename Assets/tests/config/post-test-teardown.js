export default async function (globalConfig, projectConfig) {
    console.log(globalConfig.testPathPattern);
    console.log(projectConfig.cache);

    await globalThis.__childProcess__.kill();
};