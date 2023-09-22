const path = require('path');
const TerserPlugin = require("terser-webpack-plugin");
let default_conf = require('./webpack.default.config.jsx');
const _ = require("lodash");


const prod_conf = {
    mode: 'production',
    entry: {
        'index.organizer': path.resolve(__dirname, '../_build/index.organizer.js'),
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

module.exports = _.merge(default_conf, prod_conf);