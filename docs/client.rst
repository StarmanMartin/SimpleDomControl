The Client
==========

The entire client is organized within the *Assets* directory,
encompassing not only the core code of SDC but also containing
pre-implemented SDC controllers for frequently used functionalities.
These encompass page navigation, list views, form views for both
editing and creating, search views, and more. These controllers are
located in the 'sdc_tools' folder and the 'sdc_user' folder. Another
notable advantage of a framework like SDC, which is intricately tied
to its environment and technologies, is that the entire build chain
can be pre-designed. Through the use of two Gulp tasks, **build**
and **develop** a significant portion of the workload has been
alleviated. However, it's important to note that usage of these tasks
is optional, and you have the flexibility to choose whether or not to utilize them.

::

    └─ ...
       ├─ Assets/
          ├─ src/
             ├─ sdc_tools/
                └─ ...
             ├─ sdc_user/
                └─ ...
             ├─ simpleDomControl/
                └─ ...
             ├─ index.organizer.js
             └─ index.style.scss
          ├─ webpack.config/
             ├─ webpack.development.config.js
             ├─ webpack.production.config.js
             └─ webpack.default.config.js
          ├─ tests/
             ├─ utils/
                └─ test_utils.js
             └─ ...
          ├─ babel.config.json
          ├─ gulpfile.js
          └─ package.json
       └─ ...

Dependencies
************

Let's first look at the dependencies in the package.json
file. The following list presents all the development dependencies.

* @babel/core = ^7.21.0
* @babel/preset-env = ^7.20.2
* babel-loader = ^9.1.2
* css-loader = ^6.7.3
* gulp = ^4.0.2
* gulp-clean = ^0.4.0
* gulp-rename = ^2.0.0
* gulp-sass = ^5.1.0
* gulp-sourcemaps = ^3.0.0
* gulp-uglify = ^3.0.2
* jest = ^28.1.3
* sass = ^1.58.3
* sass-loader = ^13.2.0
* style-loader = ^3.3.1
* terser-webpack-plugin = ^5.3.9
* through2 = ^4.0.2
* webpack = ^5.75.0
* webpack-stream = ^7.0.0

All development dependencies are necessary for the build process.
The remaining dependencies need to be installed for the error-free application of SDC

* bootstrap = ^5.2.3
* jquery = ^3.6.3
* lodash = ^4.17.21"

Build client
____________

As previously mentioned, one of the notable advantages of SDC's design is its ability to pre-configure
the entire build chain. Consequently, the *Assets/package.json* file contains two executable scripts:
**'build'** and **'develop'**, both of which run Gulp tasks defined in *Assets/gulpfile.js.*

**The 'build' task** is responsible for generating CSS and JavaScript index files within a newly created
*static* folder. These files undergo the process of uglification, resulting in optimized and production-ready assets.

**The 'develop' task**, on the other hand, also produces CSS and JavaScript index files in the 'static'
folder. However, it includes source mapping to facilitate browser debugging. In addition, it initiates
a file watcher, which automatically triggers a rebuild whenever there is a change in any CSS or JavaScript file.

Feel free to customize the Gulp tasks to suit your needs, but it's crucial to ensure that the **pre_compile_javascript**
task remains intact for SDC to function correctly. You can alter the webpack process to suit your specific requirements.
Within the *Assets/webpack.config/* directory, you'll find three webpack configuration files: a common default file, a
development file, and a production file.

Organization of the client-file structure
-----------------------------------------



::

    └─ ...
       ├─ Assets/
          ├─ src/
             ├─ sdc_tools/
                ├─ controller
                   ├─ sdc_alert_messenger
                      ├─ sdc_alert_messenger.js
                      ├─ sdc_alert_messenger.scss
                      └─ sdc_alert_messenger.html (ONLY LINKED)
                   ├─ sdc_navigator
                      └─ ...
                   └─ ...
                ├─ sdc_tools.organizer.js
                └─ sdc_tools.style.scss
          └─ ...
       └─ ...