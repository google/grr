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
 * @param {Array<String>=} extraCommandArgs
 */
function Compiler(args, extraCommandArgs) {
  this.commandArguments = (extraCommandArgs || []).slice();

  if (Compiler.JAR_PATH) {
    this.commandArguments.push('-jar', Compiler.JAR_PATH);
  }

  if (Array.isArray(args)) {
    this.commandArguments = this.commandArguments.concat(args.slice());
  } else {
    for (var key in args) {
      if (Array.isArray(args[key])) {
        for (var i = 0; i < args[key].length; i++) {
          this.commandArguments.push(
              this.formatArgument(key, args[key][i]));
        }
      } else {
        this.commandArguments.push(
            this.formatArgument(key, args[key]));
      }
    }
  }
}

/**
 * @const
 * @type {string}
 */
Compiler.JAR_PATH = compilerPath;

/**
 * @type {string}
 */
Compiler.prototype.javaPath = 'java';

/** @type {function(...*)|null} */
Compiler.prototype.logger = null;

/** @type {Object<string, string>} */
Compiler.prototype.spawnOptions = undefined;

/**
 * @param {function(number, string, string)=} callback
 * @return {child_process.ChildProcess}
 */
Compiler.prototype.run = function(callback) {
  if (this.logger) {
    this.logger(this.getFullCommand() + '\n');
  }

  var compileProcess = spawn(this.javaPath, this.commandArguments, this.spawnOptions);

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
  return this.javaPath + ' ' + this.commandArguments.join(' ');
};

/**
 * @param {string} msg
 * @return {string}
 */
Compiler.prototype.prependFullCommand = function(msg) {
  return this.getFullCommand() + '\n\n' + msg + '\n\n';
};

/**
 * @param {string} key
 * @param {(string|boolean)=} val
 * @return {string}
 */
Compiler.prototype.formatArgument = function(key, val) {
  if (val === undefined || val === null) {
    return '--' + key;
  }

  return '--' + key + '=' + val;
};

module.exports = Compiler;
