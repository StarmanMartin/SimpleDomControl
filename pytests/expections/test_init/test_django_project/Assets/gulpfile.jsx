'use strict'

const {src, dest, series, watch, parallel} = require('gulp');
const sass = require('gulp-sass')(require('sass'));
const webpack = require('webpack-stream');
const through = require('through2');
const gclean = require('gulp-clean');
const fs = require('fs');
const chokidar = require('chokidar');
const exec = require('gulp-exec');

function scss() {
    return src('./src/*.scss', {follow: true})
        .pipe(sass().on('error', sass.logError))
        .pipe(dest('../static'));
}

function pre_compile_javascript() {
    return src('./src/**/*.js', {follow: true})
        .pipe(through.obj(function (obj, enc, next) {
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
        }))
        .pipe(dest('./_build'));
}

function javascript() {
    const webpack_config = (process.env.NODE_ENV === 'development' ? './webpack.config/webpack.development.config.jsx' : './webpack.config/webpack.production.config.jsx');

    return src('./_build/index.organizer.js')
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

function link_files(cb) {
    const python = process.env.PYTHON
    if (!python) {
        console.log(`The environment variable PYTHON (Path to python interpreter) is not set. In this case link_files cannot be executed`);
        cb();
        return;
    }

    process.chdir('..');
    const options = {
        continueOnError: true, // default = false, true means don't emit error event
        pipeStdout: true, // default = false, true means stdout is written to file.contents
    };
    return src(python)
        .pipe(exec(file => `${file.path} manage.py sdc_update_links`, options).on('error', function (err) {
            console.error('Error:', err.message);
            this.emit('end'); // Continue with the next task
        })).on('end', () => {
            process.chdir('./Assets');
            cb();
        });

}


const webpack_series = series(clean, pre_compile_javascript, javascript, clean);
exports.webpack = webpack_series;
exports.scss = scss;
exports.link_files = link_files;
exports.clean = clean;
const defaultBuild = series(link_files, parallel(scss, webpack_series));
exports.default = defaultBuild;

function watch_scss() {
    const watcher = chokidar.watch('./src/**/*.scss', {followSymlinks: true});
    watcher.on('change', (a) => {
        console.log(`${a} has changed! SCSS is recompiling...`);
        scss().on('end', ()=>{
            console.log(`... recompiling done!`);
        });
    });
}

exports.watch_scss = watch_scss;

function watch_webpack() {
    const watcher = chokidar.watch('./src/**/*.js', {followSymlinks: true});

    watcher.on('change', (a) => {
        console.log(`${a} has changed! javascript is recompiling...`);
        webpack_series().on('end', ()=>{
            console.log(`... recompiling done!`);
        });
    });
}

exports.watch_webpack = watch_webpack;


exports.develop = series(function (done) {
    process.env.NODE_ENV = 'development'
    done();
}, defaultBuild, parallel(
    watch_scss,
    watch_webpack
));
