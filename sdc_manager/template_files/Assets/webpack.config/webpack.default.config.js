const path = require('path');
const webpack = require("webpack");
const outputDir = path.resolve(__dirname, '../build');

module.exports = {
    mode: 'production',
    entry: {
        'index.organizer': path.resolve(__dirname, '../src/index.organizer.js'),
    },
    output: {
        path: outputDir,
        filename: '[name].js'
    },
    module: {
        rules: [
            {
                test: /\.s[ac]ss$/i,
                use: [{
                    loader: 'style-loader', // inject CSS to page
                }, {
                    loader: 'css-loader', // translates CSS into CommonJS modules
                }, {
                    loader: 'postcss-loader', // Run post css actions
                    options: {
                        plugins: function () { // post css plugins, can be exported to postcss.config.js
                            return [
                                require('precss'),
                                require('autoprefixer')
                            ];
                        }
                    }
                }, {
                    loader: 'sass-loader' // compiles Sass to CSS
                }]
            },
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: ['babel-loader']
            }]
    }
};