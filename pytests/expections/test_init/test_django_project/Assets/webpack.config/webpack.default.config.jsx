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
        }]
    }
  }
};