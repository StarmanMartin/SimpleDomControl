import { exec } from 'child_process';

function runGulpTask(taskName) {
    return new Promise((resolve, reject) => {
        exec(`gulp --gulpfile=Assets/gulpfile.jsx ${taskName}`, (err, stdout, stderr) => {
            if (err) {
                reject(stderr);
            } else {
                resolve(stdout);
            }
        });

    });
}


// Run the 'prepare_test' Gulp task
await runGulpTask('prepare_test');

