let _ = require('lodash');
const webpack = require("webpack");
let default_conf = require('./webpack.default.config.jsx');


let dev_conf = {
    mode: 'development',
    devtool: 'eval-source-map',
    plugins: [
        new webpack.SourceMapDevToolPlugin({})
    ]
};

default_conf.module.rules.push({
    test: /\.js$/,
    exclude: /node_modules/,
    use: ['babel-loader']
});

module.exports = _.merge(default_conf, dev_conf);