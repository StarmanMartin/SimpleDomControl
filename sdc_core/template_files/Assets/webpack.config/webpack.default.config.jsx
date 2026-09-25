const fs = require('fs');
const path = require('path');

const override = path.resolve(__dirname, "../overwrite_libs");
const libs = path.resolve(__dirname, "../libs");

/**
 * Resolver plugin: when a module resolves to a file in Assets/libs and a file with
 * the same relative path exists in Assets/overwrite_libs, the build uses that file
 * instead (see manage.py sdc_overwrite_lib_file). This also covers the relative
 * imports inside the library organizers.
 */
class OverwriteLibsPlugin {
  apply(resolver) {
    const target = resolver.ensureHook('existing-file');
    resolver.getHook('existing-file').tapAsync('OverwriteLibsPlugin', (request, resolveContext, callback) => {
      const file = request.path;
      if (!file || !file.startsWith(libs + path.sep)) {
        return callback();
      }
      const replacement = path.join(override, path.relative(libs, file));
      if (!fs.existsSync(replacement)) {
        return callback();
      }
      resolver.doResolve(target, {...request, path: replacement},
        `overwrite_libs: ${replacement}`, resolveContext, callback);
    });
  }
}

module.exports = (filepaths) => {
  const entry = filepaths.reduce((acc, file)=> {
    const name = path.basename(file, ".js");
    acc[name] = file;
    return acc;
  }, {})

  return {
    resolve: {
      alias: {
        "libs": override
      },
      plugins: [new OverwriteLibsPlugin()],
      modules: [
        path.resolve(__dirname, "../../node_modules"),
        "node_modules"
      ],
      symlinks: false
    },
    entry,
    output: {
      filename: '[name].js'
    },
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: ['babel-loader']
        }]
    }
  }
};