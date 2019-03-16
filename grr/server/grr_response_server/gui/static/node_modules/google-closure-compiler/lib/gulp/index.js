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
 * @fileoverview Gulp task for closure-compiler. Multiplexes input
 * files into a json encoded stream which can be piped into closure-compiler.
 * Each json file object includes the contents, path and optionally sourcemap
 * for every input file.
 *
 * Closure-compiler will return the same style string via standard-out which
 * is then converted back to vinyl files.
 *
 * @author Chad Killingsworth (chadkillingsworth@gmail.com)
 */

'use strict';

/**
 * @param {Object<string,string>} initOptions
 * @return {function(Object<string,string>|Array<string>):Object}
 */
module.exports = function(initOptions) {
  var filesToJson = require('./concat-to-json');
  var jsonToVinyl = require('./json-to-vinyl');
  var Compiler = require('../node/closure-compiler');
  var stream = require('stream');
  /** @const */
  var PLUGIN_NAME = 'gulp-google-closure-compiler';

  var extraCommandArguments = initOptions ? initOptions.extraArguments : undefined;
  var applySourceMap = require('vinyl-sourcemaps-apply');
  var path = require('path');
  var chalk = require('chalk');
  var File = require('vinyl');

  /** @constructor */
  function CustomError(plugin, msg) {
    var superError = Error.call(this) || this;
    Error.captureStackTrace(superError, this.constructor);
    superError.name = 'Error';
    superError.message = msg;
    return superError;
  }
  CustomError.prototype = Object.create(Error.prototype);
  CustomError.prototype.name = 'Error';

  var PluginError;
  try {
    PluginError = require('gulp-util').PluginError;
  } catch(e) {
    PluginError = CustomError;
  }

  var gulpLog;
  try {
    gulpLog = require('gulp-util').log;
  } catch(e) {
    gulpLog = console;
  }

  function CompilationStream(compilationOptions, pluginOptions) {
    stream.Transform.call(this, {objectMode: true});

    pluginOptions = pluginOptions || {};

    this.compilationOptions_ = compilationOptions;
    this.streamMode_ = pluginOptions.streamMode || 'BOTH';
    this.logger_ = pluginOptions.logger || gulpLog;
    this.PLUGIN_NAME_ = pluginOptions.pluginName || PLUGIN_NAME;

    this.fileList_ = [];
    this._streamInputRequired = pluginOptions.requireStreamInput !== false;
  }
  CompilationStream.prototype = Object.create(stream.Transform.prototype);

  // Buffer the files into an array
  CompilationStream.prototype.src = function() {
    this._streamInputRequired = false;
    process.nextTick((function() {
      var stdInStream = new stream.Readable({ read: function() {
        return new File();
      }});
      stdInStream.pipe(this);
      stdInStream.push(null);
    }).bind(this));
    return this;
  };

  // Buffer the files into an array
  CompilationStream.prototype._transform = function(file, enc, cb) {
    // ignore empty files
    if (file.isNull()) {
      cb();
      return;
    }

    if (file.isStream()) {
      this.emit('error', new PluginError(this.PLUGIN_NAME_, 'Streaming not supported'));
      cb();
      return;
    }

    this.fileList_.push(file);
    cb();
  };

  CompilationStream.prototype._flush = function(cb) {
    var jsonFiles, logger = this.logger_.warn ? this.logger_.warn : this.logger_;
    if (this.fileList_.length > 0) {
      // Input files are present. Convert them to a JSON encoded string
      jsonFiles = filesToJson(this.fileList_);
    } else {
      // If files in the stream were required, no compilation needed here.
      if (this._streamInputRequired) {
        this.emit('end');
        cb();
        return;
      }

      // The compiler will always expect something on standard-in. So pass it an empty
      // list if no files were piped into this plugin.
      jsonFiles = [];
    }

    var compiler = new Compiler(this.compilationOptions_, extraCommandArguments);

    // Add the gulp-specific argument so the compiler will understand the JSON encoded input
    // for gulp, the stream mode will be 'BOTH', but when invoked from grunt, we only use
    // a stream mode of 'IN'
    compiler.commandArguments.push('--json_streams', this.streamMode_);

    var compilerProcess = compiler.run();

    var stdOutData = '', stdErrData = '';

    compilerProcess.stdout.on('data', function (data) {
      stdOutData += data;
    });
    compilerProcess.stderr.on('data', function (data) {
      stdErrData += data;
    });

    Promise.all([
      new Promise(function(resolve) {
        compilerProcess.on('close', function(code) {
          resolve(code);
        });
      }),
      new Promise(function(resolve) {
        compilerProcess.stdout.on('end', function() {
          resolve();
        });
      }),
      new Promise(function(resolve) {
        compilerProcess.stderr.on('end', function() {
          resolve();
        });
      })
    ]).then((function(results) {
      var code = results[0];

      // standard error will contain compilation warnings, log those
      if (stdErrData.trim().length > 0) {
        logger(chalk.yellow(this.PLUGIN_NAME_) + ': ' + stdErrData);
      }

      // non-zero exit means a compilation error
      if (code !== 0) {
        this.emit('error', new PluginError(this.PLUGIN_NAME_, 'Compilation error'));
      }

      // If present, standard output will be a string of JSON encoded files.
      // Convert these back to vinyl
      if (stdOutData.trim().length > 0) {
        var outputFiles;
        try {
          outputFiles = jsonToVinyl(stdOutData);
        } catch (e) {
          this.emit('error', new PluginError(this.PLUGIN_NAME_, 'Error parsing json encoded files'));
          cb();
          return;
        }

        for (var i = 0; i < outputFiles.length; i++) {
          if (outputFiles[i].sourceMap) {
            applySourceMap(outputFiles[i], outputFiles[i].sourceMap);
          }
          this.push(outputFiles[i]);
        }
      }
      cb();
    }).bind(this));

    // Error events occur when there was a problem spawning the compiler process
    compilerProcess.on('error', (function (err) {
      this.emit('error', new PluginError(this.PLUGIN_NAME_,
          'Process spawn error. Is java in the path?\n' + err.message));
      cb();
    }).bind(this));

    compilerProcess.stdin.on('error', (function(err) {
      this.emit('Error', new PluginError(this.PLUGIN_NAME_,
          'Error writing to stdin of the compiler.\n' + err.message));
      cb();
    }).bind(this));
    
    var stdInStream = new stream.Readable({ read: function() {}});
    stdInStream.pipe(compilerProcess.stdin);
    stdInStream.push(JSON.stringify(jsonFiles));
    stdInStream.push(null);
  };


  return function (compilationOptions, pluginOptions) {
    return new CompilationStream(compilationOptions, pluginOptions);
  };
};
