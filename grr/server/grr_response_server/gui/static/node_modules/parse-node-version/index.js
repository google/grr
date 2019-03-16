'use strict';

function parseNodeVersion(version) {
  var match = version.match(/^v(\d{1,2})\.(\d{1,2})\.(\d{1,2})$/);
  if (!match) {
    throw new Error('Unable to parse: ' + version);
  }

  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
  };
}

module.exports = parseNodeVersion;
