import {exec, spawn} from 'child_process';
import dotenv from "dotenv";
import fs from "fs";
import http from "http";
import path from "path";


dotenv.config({path: './Assets/.sdc_env'});
dotenv.config({path: './Assets/.sdc_python_env'});

const PORT = 8765;
const SERVER_START_TIMEOUT_MS = 30000;

/**
 * Runs a shell command. Resolves with stdout; rejects with an error that
 * contains the command and its output if the command fails.
 */
function executeCmd(task) {
    return new Promise((resolve, reject) => {
        exec(task, {maxBuffer: 64 * 1024 * 1024}, (err, stdout, stderr) => {
            if (err) {
                reject(new Error(`Command failed: ${task}\n${stderr || stdout || err.message}`));
            } else {
                resolve(stdout);
            }
        });
    });
}

/** Resolves as soon as the test server answers HTTP requests. */
function waitForServer(childProcess, logFile) {
    const deadline = Date.now() + SERVER_START_TIMEOUT_MS;
    return new Promise((resolve, reject) => {
        let exited = false;
        childProcess.on('exit', (code) => {
            exited = true;
            reject(new Error(`The test server stopped (exit code ${code}). See ${logFile}`));
        });
        const poll = () => {
            if (exited) return;
            const req = http.get({host: '127.0.0.1', port: PORT, path: '/'}, (res) => {
                res.resume();
                resolve();
            });
            req.on('error', () => {
                if (Date.now() > deadline) {
                    reject(new Error(`The test server did not start within ${SERVER_START_TIMEOUT_MS / 1000}s. See ${logFile}`));
                } else {
                    setTimeout(poll, 250);
                }
            });
        };
        poll();
    });
}

export default async function (globalConfig, projectConfig) {
    const python = process.env.PYTHON;
    const json_data_dump_path = process.env.JSON_DATA_DUMP === '0' ? false : process.env.JSON_DATA_DUMP;
    const copy_default = process.env.COPY_DEFAULT_DB !== "0";
    const db_python_script = process.env.DB_PYTHON_SCRIPT === '0' ? false : process.env.DB_PYTHON_SCRIPT;


    if (!python) {
        throw new Error(`The environment PYTHON is not set. Simply add it to: ./Assets/.sdc_env or run ./manage.py sdc_init`)
    }
    if (typeof json_data_dump_path === 'string') {
        fs.mkdirSync(path.dirname(json_data_dump_path), {recursive: true});
    }

    const export_cmd = `${python} manage.py dumpdata --exclude auth.permission --exclude contenttypes -o ${json_data_dump_path}`
    const migrate_cmd = `${python} manage.py migrate`
    const import_cmd = `${python} manage.py loaddata ${json_data_dump_path}`
    const python_script_cmd = `${python} manage.py sdc_shell_execute_script -s ${db_python_script}`
    const flush_cmd = `${python} manage.py flush --no-input`

    console.log('Prepare JEST DB');

    // Copying the development database is optional: if it fails (e.g. the database
    // is not migrated yet), the tests run without that data.
    if (copy_default && json_data_dump_path) {
        console.log('Export default DB');
        try {
            await executeCmd(export_cmd);
        } catch (e) {
            console.warn(`Could not export the default DB, its data is not copied.\n${e.message}`);
            fs.rmSync(json_data_dump_path, {force: true});
        }
    }

    process.env.DJANGO_DATABASE = 'jest';

    console.log('Execute JEST DB migrate');
    await executeCmd(migrate_cmd);
    console.log('Flushing JEST DB');
    await executeCmd(flush_cmd);

    if (json_data_dump_path && fs.existsSync(json_data_dump_path)) {
        console.log(`Import ${json_data_dump_path} to JEST DB`);
        await executeCmd(import_cmd);
    }

    if (db_python_script) {
        console.log(`Execute ${python_script_cmd} to prepare DB`);
        process.env.SCRIPT_OUTPUT = (await executeCmd(python_script_cmd)).trim('\n');
        console.log(process.env.SCRIPT_OUTPUT);
    }

    fs.mkdirSync('./Assets/tests/logs', {recursive: true});
    const start = new Date();
    const logFile = `./Assets/tests/logs/jest_server_logs_${start.toLocaleString('de-DE').replace(', ', '_')}.log`;
    console.log(`Starting server on port ${PORT} (log: ${logFile})`);
    let childProcess = spawn(`${python}`, ['manage.py', 'runserver', `${PORT}`, '--noreload'], {
        detached: true
    })
    childProcess.unref();
    const logStream = fs.createWriteStream(logFile, {flags: 'a'});
    childProcess.stdout.pipe(logStream);
    childProcess.stderr.pipe(logStream);

    process.on('exit', function () {
        if (!childProcess.killed) {
            childProcess.kill();
            logStream.close();
        }
    });

    // Set reference to the server process in order to close it during teardown.
    globalThis.__childProcess__ = childProcess;

    await waitForServer(childProcess, logFile);
};
