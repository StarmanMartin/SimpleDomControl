'use strict'

const {src, dest, series, parallel} = require('gulp');
const webpack = require('webpack-stream');
const copy = require('gulp-copy');

process.env.JS_CILENT_FILE_EXTENTIONS = ['.js', '.json'];

const {
    sdc_scss,
    sdc_clean,
    sdc_link_files,
    sdc_watch_webpack_factory,
    sdc_watch_scss,
    sdc_default_build_factory
} = require('sdc_client/gulp/gulp.jsx');

function webpack_javascript() {
    const webpack_config = require((process.env.NODE_ENV === 'development' ? './webpack.config/webpack.development.config.jsx' : './webpack.config/webpack.production.config.jsx'));
    return src('./_build/index.organizer.js')
        .pipe(webpack(webpack_config))
        .pipe(dest('../static'));
}

function copy_statics() {
    return src('./static/**/*')
        .pipe(copy('../static', { prefix: 1 }))
        .on('end', () => {
            console.log('Contents copied successfully!');
        });
}

exports.webpack = webpack_javascript;
exports.scss = sdc_scss;
exports.link_files = sdc_link_files;
exports.clean = sdc_clean;
exports.copy_statics = copy_statics;
exports.default = series(copy_statics, sdc_default_build_factory(webpack_javascript));
exports.watch_scss = sdc_watch_scss;
exports.watch_webpack = sdc_watch_webpack_factory(webpack_javascript);

exports.develop = series(function (done) {
    process.env.NODE_ENV = 'development';
    process.env.BABEL_ENV = 'development';
    done();
}, sdc_default_build_factory(webpack_javascript), parallel(
    sdc_watch_scss,
    sdc_watch_webpack_factory(webpack_javascript)
));
