const fs = require('fs');
const path = require('path');
const TerserPlugin = require("terser-webpack-plugin");
let prod_conf = require('./webpack.production.config.jsx');
const _ = require("lodash");

// Packages every SDC app takes from the project (used for apps without an Assets/sdc_app.json)
const BASE_PEERS = ['sdc_client', 'jquery', 'lodash', 'bootstrap'];
const src = path.resolve(__dirname, '../src');
const build = path.resolve(__dirname, '../_build');
const peerCache = {};

/**
 * The npm packages an app takes from the project: the keys of ``peerDependencies`` in ``<app>/Assets/sdc_app.json``
 * (``Assets/src/<app>`` links to ``<app>/Assets/src/<app>``). The project installs them; the build check of
 * sdc_client (``sdc_check_dependencies``) makes sure it does.
 */
function appPeers(app) {
  if (!(app in peerCache)) {
    let peers = BASE_PEERS;
    try {
      const manifest = path.join(fs.realpathSync(path.join(src, app)), '..', '..', 'sdc_app.json');
      peers = Object.keys(JSON.parse(fs.readFileSync(manifest, 'utf8')).peerDependencies || {});
    } catch (e) {
      // no manifest: the base packages
    }
    peerCache[app] = peers;
  }
  return peerCache[app];
}

/** The package of a bare import: ``bootstrap/dist/x.js`` -> ``bootstrap``, ``@scope/pkg/x`` -> ``@scope/pkg``. */
function packageName(request) {
  const parts = request.split('/');
  return request.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
}

/**
 * Bundles of SDC apps (``gulp bundle``): one ES module per app (``bin/<app>/<app>.organizer.js``). The packages of
 * the app's ``peerDependencies`` stay imports, resolved by the project's webpack from its node_modules (one copy
 * shared by all apps); everything else the app imports is compiled into the bundle.
 */
const bundle_conf = {
  mode: "production",
  experiments: {outputModule: true},
  externalsType: 'module',
  externals: [({context, request}, callback) => {
    const relative = context && path.relative(build, context);
    if (!request || request.startsWith('.') || path.isAbsolute(request) || request.startsWith('#')
      || !relative || relative.startsWith('..')) {
      return callback();
    }
    const app = relative.split(path.sep)[0];
    return appPeers(app).includes(packageName(request)) ? callback(null, request) : callback();
  }],
  output: {
    module: true,
    chunkFormat: 'module',
    filename: (pathData)=> {
      const name = pathData.chunk.name;
      const appName = name.replace(/\.organizer$/, '')
      return `${appName}/[name].js`
    }
  },

  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        test: /\.js(\?.*)?$/i,
        terserOptions: {
          module: true,
          keep_classnames: true,
          keep_fnames: true
        }
      })
    ]
  }
};

module.exports = (filepath) => _.merge(prod_conf(filepath), bundle_conf);
