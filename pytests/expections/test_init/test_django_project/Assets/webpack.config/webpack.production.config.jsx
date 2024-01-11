const TerserPlugin = require("terser-webpack-plugin");
let default_conf = require('./webpack.default.config.jsx');
const _ = require("lodash");


const prod_conf = {
    mode: 'production',

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

module.exports = _.merge(default_conf, prod_conf);