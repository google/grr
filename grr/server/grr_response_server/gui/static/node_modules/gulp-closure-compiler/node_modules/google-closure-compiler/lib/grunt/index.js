/*
 * Copyright 2015 The Closure Compiler Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @fileoverview Grunt task for closure-compiler
 *
 * @author Chad Killingsworth (chadkillingsworth@gmail.com)
 */

'use strict';

module.exports = function(grunt) {
  var chalk = require('chalk');
  var Compiler = require('../node/closure-compiler');

  function compilationPromise(options) {
    var destFilename = options.js_output_file;
    if (destFilename) {
      destFilename = ' ' + chalk.cyan(destFilename);
    } else {
      destFilename = '';
    }

    return new Promise(function(resolve, reject) {
      function compilationCompleted(exitCode, stdOut, stdErr) {
        if (exitCode === 0) {
          if (stdErr.trim().length > 0) {
            grunt.log.warn(stdErr);
          }

          grunt.log.ok((destFilename.length > 0 ? destFilename : 'file') + ' created.');

          resolve(stdOut, stdErr, destFilename);
        } else {
          grunt.log.warn('Error compiling source' + destFilename);
          grunt.fail.warn('Compilation failed\n\n' + stdErr);

          reject(stdOut, stdErr, destFilename);
        }
      }

      var compiler = new Compiler(options);
      compiler.logger = grunt.verbose.write;
      compiler.run(compilationCompleted);
    });
  }

  grunt.registerMultiTask('closure-compiler',
      'Minify files with Google Closure Compiler',
      function() {
    var taskObject = this;
    var asyncDone = this.async();
    var compileTasks = [];

    function getCompilerOptions() {
      var opts = taskObject.options({
        args: undefined
      });

      var args = opts.args;

      delete opts.args;

      return {
        args: args,
        compilerOpts: opts
      }
    }

    taskObject.files.forEach(function (f) {
      var options = getCompilerOptions();

      var src = f.src.filter(function (filepath) {
        if (!grunt.file.exists(filepath)) {
          grunt.log.warn('Source file ' + chalk.cyan(filepath) + ' not found.');
          return false;
        }
        return true;
      });

      // Require source files
      if (src.length === 0) {
        grunt.log.warn('Destination ' + chalk.cyan(f.dest) +
            ' not written because src files were empty.');
        asyncDone();
        return;
      } else {
        options.compilerOpts.js = (options.compilerOpts.js || []).concat(src);
        options.compilerOpts.js_output_file = f.dest;
      }

      compileTasks.push(compilationPromise(options.args || options.compilerOpts));
    });

    // If an args array was provided as an option, invoke the compiler
    // with those arguments - but only if no src file sets were specified
    var options = getCompilerOptions();
    if (taskObject.files.length === 0) {
      compileTasks.push(compilationPromise(options.args || options.compilerOpts));
    }

    Promise.all(compileTasks).then(function () {
      asyncDone();
    }, function () {
      asyncDone();
    });
  });
};
