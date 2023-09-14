'use strict'

const {src, dest, series, watch, parallel} = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const webpack = require('webpack-stream');
const through = require('through2');
const gclean = require('gulp-clean');
const fs = require('fs');


const sdc_controller = through.obj(function (obj, enc, next) {
    let srcFile = obj.path
    if (!obj.isNull() && !obj.isDirectory() && obj.isBuffer() && /.js$/.test(srcFile)) {
        let file_content = obj.contents.toString().split('\n');
        let controller_name = null;
        let on_init_p_name = null;
        file_content.forEach((element) => {
            if (!controller_name) {
                let a = element.match(/class (.*)\s+extends\s*AbstractSDC /);
                if (a) controller_name = a[1];
            }
            if (!on_init_p_name) {
                let a = element.match(/^\s*onInit\s*\((.*)\)\s*\{/);
                if (a) on_init_p_name = a[1].split(/\s*,\s*/).join('", "');
            }


        });
        if (file_content && controller_name && on_init_p_name) {
            file_content.push(`${controller_name}.prototype._on_init_params = function() {return ["${on_init_p_name}"]; };`);
            obj.contents = Buffer.from(file_content.join('\n'));
        }

    }
    next(null, obj);
});

function scss() {
    return src('src/*.scss')
        .pipe(sass().on('error', sass.logError))
        .pipe(dest('../static'));
}

function pre_compile_javascript() {
    const webpack_config = (process.env.NODE_ENV === 'development' ? './webpack.config/webpack.development.config' : './webpack.config/webpack.production.config.js');

    return src('src/**/*.js')
        .pipe(sdc_controller)
        .pipe(dest('./_build'));
}
function javascript() {
    const webpack_config = (process.env.NODE_ENV === 'development' ? './webpack.config/webpack.development.config' : './webpack.config/webpack.production.config.js');

    return src('_build/**/*.js')
        .pipe(webpack(require(webpack_config)))
        .pipe(dest('../static'));
}

function clean(done) {
    if (fs.existsSync('./_build')) {
        return src('./_build').pipe(gclean());
    } else {
        done()
    }
}


const webpack_series = series(clean, pre_compile_javascript, javascript, clean);
exports.webpack = webpack_series;
exports.scss = scss;
exports.clean = clean;
const defaultBuild = parallel(scss, webpack_series);
exports.default = defaultBuild;

exports.develop = series(function (done) {
    process.env.NODE_ENV = 'development'
    done();
}, defaultBuild, function () {
    watch('src/**/*.scss', scss);
    watch('src/**/*.js', javascript);
});
