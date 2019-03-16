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
 * @fileoverview Low level class for calling the closure-compiler jar
 * from nodejs
 *
 * @author Chad Killingsworth (chadkillingsworth@gmail.com)
 */

'use strict';

var spawn = require('child_process').spawn;
var compilerPath = require.resolve('../../compiler.jar');
var path = require('path');
var contribPath = path.dirname(compilerPath) + '/contrib';

/**
 * @constructor
 * @param {Object<string,string>|Array<string>} args
 */
function Compiler(args) {
  this.command_arguments = [];
  if (Array.isArray(args)) {
    this.command_arguments = args.slice();
  } else {
    for (let key in args) {
      if (Array.isArray(args[key])) {
        for (let i = 0; i < args[key].length; i++) {
          this.command_arguments.push('--' + key + '=' +
              this.escapeArgument(args[key][i]));
        }
      } else {
        if (args[key] !== null && args[key] !== undefined) {
          this.command_arguments.push('--' + key + '=' +
              this.escapeArgument(args[key]));
        } else {
          this.command_arguments.push('--' + key);
        }
      }
    }
  }

  this.command_arguments.unshift('-jar', Compiler.jar_path);
}

/**
 * @const
 * @type {string}
 */
Compiler.jar_path = compilerPath;

/**
 * @type {string}
 */
Compiler.prototype.java_path = 'java';

/** @type {function(...*)|null} */
Compiler.prototype.logger = null;

/** @type {Object<string, string>} */
Compiler.prototype.spawn_options = undefined;

/**
 * @param {function(number, string, string)=} callback
 * @return {child_process.ChildProcess}
 */
Compiler.prototype.run = function(callback) {
  if (this.logger) {
    this.logger(this.getFullCommand() + '\n');
  }

  var compileProcess = spawn(this.java_path, this.command_arguments, this.spawn_options);

  var stdOutData = '', stdErrData = '';
  if (callback) {
    compileProcess.stdout.on('data', function (data) {
      stdOutData += data;
    });

    compileProcess.stderr.on('data', function (data) {
      stdErrData += data;
    });

    compileProcess.on('close', (function (code) {
      if (code !== 0) {
        stdErrData = this.prependFullCommand(stdErrData);
      }

      callback(code, stdOutData, stdErrData);
    }).bind(this));

    compileProcess.on('error', (function (err) {
      callback(1, stdOutData,
          this.prependFullCommand('Process spawn error. Is java in the path?\n' + err.message));
    }).bind(this));
  }

  return compileProcess;
};

/** @type {string} */
Compiler.COMPILER_PATH = compilerPath;

/** @type {string} */
Compiler.CONTRIB_PATH = contribPath;

/**
 * @return {string}
 */
Compiler.prototype.getFullCommand = function() {
  return this.java_path + ' ' + this.command_arguments.join(' ');
};

/**
 * @param {string} msg
 * @return {string}
 */
Compiler.prototype.prependFullCommand = function(msg) {
  return this.getFullCommand() + '\n\n' + msg + '\n\n';
};

/**
 * @param {string} arg
 * @return {string}
 */
Compiler.prototype.escapeArgument = function(arg) {
  if (arg === true || arg === false ||
      (arg.substr(0, 1) === '"' && arg.substr(arg.length - 1, 1) === '"')) {
    return arg;
  }
  return '"' + arg.replace(/"/g, '\\"') + '"';
};

module.exports = Compiler;
