import {exec, spawn} from 'child_process';
import dotenv from "dotenv";
import fs from "fs";
import path from "path";


dotenv.config({path: './Assets/.sdc_env'});
dotenv.config({path: './Assets/.sdc_python_env'});

export default async function (globalConfig, projectConfig) {
    const python = process.env.PYTHON;
    const json_data_dump_path = process.env.JSON_DATA_DUMP === '0'? false : process.env.JSON_DATA_DUMP;
    const copy_default = process.env.COPY_DEFAULT_DB !== "0";
    const db_python_script =  process.env.DB_PYTHON_SCRIPT === '0'? false : process.env.DB_PYTHON_SCRIPT;


    if (!python) {
        throw new Error(`The environment PYTHON is not set. Simply add it to: ./Assets/.sdc_env or run ./manage.py sdc_init`)
    }
    if(typeof json_data_dump_path === 'string') {
        fs.mkdirSync(path.dirname(json_data_dump_path), {recursive: true});
    }


    const export_cmd = `${python} manage.py dumpdata --exclude auth.permission --exclude contenttypes > ${json_data_dump_path}`
    const migrate_cmd = `${python} manage.py migrate`
    const import_cmd = `${python} manage.py loaddata ${json_data_dump_path}`
    const python_script_cmd = `${python} manage.py sdc_shell_execute_script -s ${db_python_script}`
    const flush_cmd = `${python} manage.py flush --no-input`


    function executeCmd(task) {
        return new Promise((resolve) => {
            exec(task, (err, stdout, stderr) => {
                if (err) {
                    resolve(stderr);
                } else {
                    resolve(stdout);
                }
            });
        });
    }

    console.log('Prepare JEST DB');

    if(copy_default) {
        console.log('Export default DB');
        await executeCmd(export_cmd);
    }

    process.env.DJANGO_DATABASE = 'jest';



    fs.mkdirSync('./Assets/tests/logs', { recursive: true });
    console.log(`Starting server on port 8765`);
    let childProcess = spawn(`${python}`, ['manage.py', 'runserver', '8765'], {
        detached: true
    })
    childProcess.unref();
    const start = new Date();
    const logStream = fs.createWriteStream(`./Assets/tests/logs/jest_server_logs_${start.toLocaleString('de-DE').replace(', ', '_')}.log`, {flags: 'a'});
    childProcess.stdout.pipe(logStream);
    childProcess.stderr.pipe(logStream);

    await new Promise((resolve)=> setTimeout(resolve, 1000))

    console.log('Execute JEST DB migrate');
    await executeCmd(migrate_cmd);
    console.log('Flushing JEST DB');
    await executeCmd(flush_cmd);

    if(json_data_dump_path && fs.existsSync(json_data_dump_path)) {
        console.log(`Import ${json_data_dump_path} to JEST DB`);
        await executeCmd(import_cmd);
    }

    if(db_python_script) {
        console.log(`Execute ${python_script_cmd} to JEST DB`);
        process.env.SCRIPT_OUTPUT = (await executeCmd(python_script_cmd)).trim('\n');
        console.log(process.env.SCRIPT_OUTPUT);
    }

    process.on('exit', function () {
        if(!childProcess.killed) {
            childProcess.kill();
            logStream.close();
        }
    });


    // Set reference to mongod in order to close the server during teardown.
    globalThis.__childProcess__ = childProcess;
};