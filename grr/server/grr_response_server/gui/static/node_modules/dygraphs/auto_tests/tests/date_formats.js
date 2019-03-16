/**
 * @fileoverview Tests that various formats of date are understood by dygraphs.
 *
 * @author dan@dygraphs.com (Dan Vanderkam)
 */
var dateFormatsTestCase = TestCase("date-formats");

dateFormatsTestCase.prototype.setUp = function() {
};

dateFormatsTestCase.prototype.tearDown = function() {
};

dateFormatsTestCase.prototype.testISO8601 = function() {
  // Format: YYYY-MM-DDTHH:MM:SS.ddddddZ
  // The "Z" indicates UTC, so this test should pass regardless of the time
  // zone of the machine on which it is run.

  // Firefox <4 does not support this format:
  // https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Date/parse
  if (navigator.userAgent.indexOf("Firefox/3.5") == -1) {
    assertEquals(946816496789, Dygraph.dateParser("2000-01-02T12:34:56.789012Z"));
  }
};

dateFormatsTestCase.prototype.testHyphenatedDate = function() {
  // Format: YYYY-MM-DD HH:MM

  // Midnight February 2, 2000, UTC
  var d = new Date(Date.UTC(2000, 1, 2));

  // Convert to a string in the local time zone: YYYY-DD-MM HH:MM
  var zp = function(x) { return x < 10 ? '0' + x : x; };
  var str = d.getFullYear() + '-' +
            zp(1 + d.getMonth()) + '-' +
            zp(d.getDate()) + ' ' +
            zp(d.getHours()) + ':' +
            zp(d.getMinutes());
  assertEquals(Date.UTC(2000, 1, 2), Dygraph.dateParser(str));
};
