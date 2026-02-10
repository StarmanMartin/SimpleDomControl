const TerserPlugin = require("terser-webpack-plugin");
let prod_conf = require('./webpack.production.config.jsx');
const _ = require("lodash");


const bundle_conf = {
  mode: "production",
  externals: {
    jquery: "jquery",
    lodash: "lodash",
    bootstrap: "bootstrap",
    sdc_client: "sdc_client",
  },
  output: {
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
          keep_classnames: true,
          keep_fnames: true
        }
      })
    ]
  }
};

module.exports = (filepath) => _.merge(prod_conf(filepath), bundle_conf);