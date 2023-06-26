'use strict'

const {src, dest, series, watch, parallel} = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const webpack = require('webpack-stream');

function clean(cb) {
    cb();
}

function scss() {
    return src('src/*.scss')

        .pipe(sass().on('error', sass.logError))
        .pipe(dest('./static'));
}

function javascript() {
    const webpack_config = (process.env.NODE_ENV === 'development' ? './webpack.config/webpack.development.config' : './webpack.config/webpack.default.config.js');
    return src('src/**/*.js')
        .pipe(webpack(require(webpack_config)))
        .pipe(dest('../static'));
}

exports.webpack = javascript;
exports.scss = scss;
const defaultBuild = parallel(scss, javascript);
exports.default = defaultBuild;

exports.develop = series(defaultBuild, function () {
    // You can use a single task
    watch('src/**/*.scss', scss);
    // Or a composed task
    watch('src/**/*.js', javascript);


});
