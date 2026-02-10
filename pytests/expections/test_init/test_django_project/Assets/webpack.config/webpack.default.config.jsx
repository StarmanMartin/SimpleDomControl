const path = require('path');

const override = path.resolve(__dirname, "../overwrite_libs");

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
        },
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
        }]
    }
  }
};