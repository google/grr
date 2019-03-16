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
 * @fileoverview Convert an array of vinyl files to
 * a single JSON encoded string to pass to closure-compiler
 *
 * @author Chad Killingsworth (chadkillingsworth@gmail.com)
 */

'use strict';

function json_file(src, path, source_map) {
  var filejson = {
    src: src
  };

  if (path) {
    filejson.path = path;
  }

  if (source_map) {
    filejson.source_map = source_map;
  }

  return filejson;
}

/**
 * @param {Array<Object>} files
 * @return {string}
 */
module.exports = function(files) {
  var jsonFiles = [];
  for (var i = 0; i < files.length; i++) {
    jsonFiles.push(
        json_file(files[i].contents.toString(),
            files[i].relative,
            files[i].sourceMap ? JSON.stringify(files[i].sourceMap) : undefined));
  }

  return JSON.stringify(jsonFiles);
};
