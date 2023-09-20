'use strict'

const gulp = require('gulp');
const babel = require('gulp-babel');

gulp.task('default', gulp.series((done) => {
    process.env.NODE_ENV = 'test'
    done();
}, () => {
    return gulp.src('sdc_manager/template_files/Assets/src/simpleDomControl/**/*.js')
        .pipe(babel({
            "presets": ["@babel/preset-env"]
        }))
        .pipe(gulp.dest('test/dist'));
}));
