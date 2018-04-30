'use strict';

goog.module('grrUi.semantic.rekall.utils');
goog.module.declareLegacyNamespace();


/**
 * Crops a Json Rekall message list to its largest valid prefix of lenght at
 * most targetLen.
 *
 * @param {string} jsonStr A Rekall Json message list.
 * @param {number} targetLen Returned message lenght limit.
 *
 * @return {string} The cropped message list.
 */
exports.cropRekallJson = function(jsonStr, targetLen) {
  if (targetLen <= 2 || jsonStr === '[]') {
    return '[]';
  }

  if (jsonStr.length <= targetLen) {
    return jsonStr;
  }

  // Technically, JSON allows (ignores) whitespace outside of strings, so
  // jsonStr would still be valid if it started with, eg '[ [', but this is
  // unlikely in Rekall-generated JSON, so for now we assume that can't happen.
  if (!jsonStr.startsWith('[[')) {
    throw new Error('Malformed Rekall JSON message.');
  }

  var lastMsgEnd = 1;
  var depth = 1;
  var escaped = false;
  var insideString = false;

  for (var i = 2; i < targetLen - 1; ++i) {
    if (!insideString) {

      if (jsonStr[i] === '[') {
        ++depth;
      }
      else if (jsonStr[i] === ']') {
        --depth;

        if (depth == 0) {
          lastMsgEnd = i + 1;
        }
        else if (depth < 0) {
          throw new Error('Syntax error in Rekall JSON message.');
        }
      }

    }

    if (!escaped && jsonStr[i] == '"') {
      insideString = !insideString;
    }

    escaped = (!escaped && jsonStr[i] === '\\');
  }

  return jsonStr.slice(0, lastMsgEnd) + ']';
};

/**
 * Assigns table-row messages to relevant table messages in a Rekall Json data
 * stream.
 *
 * @param {Object} parsed A parsed Rekall Json data stream.
 *
 * @return {Object} The given data stream, with table-row messages moved into
 *             corresponding table messages.
 */
exports.stackRekallTables = function(parsed) {
  var ret = [];
  var lastTableRows;

  angular.forEach(parsed, function(message) {
    var type = message[0];
    var content = message[1];

    if (type == 't') {
      lastTableRows = [];
      ret.push(['t', {'header': content, 'rows': lastTableRows}]);
    }
    else if (type == 'r') {
      if (angular.isUndefined(lastTableRows)) {
        lastTableRows = [];
        ret.push(['t', {'header': undefined, 'rows': lastTableRows}]);
      }

      lastTableRows.push(content);
    }
    else {
      ret.push(message);
    }
  });

  return ret;
};
