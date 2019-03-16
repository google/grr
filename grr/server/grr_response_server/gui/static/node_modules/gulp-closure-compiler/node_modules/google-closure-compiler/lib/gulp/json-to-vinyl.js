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
 * @fileoverview Convert a string of JSON encoded files
 * back to an array of vinyl files
 *
 * @author Chad Killingsworth (chadkillingsworth@gmail.com)
 */

'use strict';

var gutil = require('gulp-util');
var File = gutil.File;
var applySourceMap = require('vinyl-sourcemaps-apply');

/**
 * @param {string} input string of json encoded files
 * @return {Array<Object>}
 */
module.exports = function(input) {
  var fileList, outputFiles = [];

  fileList = JSON.parse(input);

  for (var i = 0; i < fileList.length; i++) {
    let file = new File({
      path: (fileList[i].path || '').trim().length === 0 || fileList[i].path === 'stdout' ?
          process.cwd() + '/compiled' + i + '.js' : fileList[i].path,
      contents: new Buffer(fileList[i].src)
    });
    if (fileList[i].source_map) {
      applySourceMap(file, fileList[i].source_map);
    }
    outputFiles.push(file);
  }

  return outputFiles;
};
