// Copyright 2017 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

goog.module('goog.i18n.DateIntervalFormatTest');
goog.setTestOnly('goog.i18n.DateIntervalFormatTest');

var DateIntervalFormat = goog.require('goog.i18n.DateIntervalFormat');
var DateRange = goog.require('goog.date.DateRange');
var DateTime = goog.require('goog.date.DateTime');
var DateTimeFormat = goog.require('goog.i18n.DateTimeFormat');
var DateTimeSymbols_ar = goog.require('goog.i18n.DateTimeSymbols_ar');
var DateTimeSymbols_en = goog.require('goog.i18n.DateTimeSymbols_en');
var DateTimeSymbols_fr_CA = goog.require('goog.i18n.DateTimeSymbols_fr_CA');
var DateTimeSymbols_gl = goog.require('goog.i18n.DateTimeSymbols_gl');
var DateTimeSymbols_hi = goog.require('goog.i18n.DateTimeSymbols_hi');
var DateTimeSymbols_zh = goog.require('goog.i18n.DateTimeSymbols_zh');
var GoogDate = goog.require('goog.date.Date');
var Interval = goog.require('goog.date.Interval');
var TimeZone = goog.require('goog.i18n.TimeZone');
var dateIntervalPatterns = goog.require('goog.i18n.dateIntervalPatterns');
var dateIntervalSymbols = goog.require('goog.i18n.dateIntervalSymbols');
var object = goog.require('goog.object');
var testSuite = goog.require('goog.testing.testSuite');

/** @const {!Object<string, !Object>} */
var localeSymbols = {
  'ar': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_ar,
    DateTimeSymbols: DateTimeSymbols_ar
  },
  'en': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_en,
    DateTimeSymbols: DateTimeSymbols_en
  },
  'fr_CA': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_fr_CA,
    DateTimeSymbols: DateTimeSymbols_fr_CA
  },
  'gl': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_gl,
    DateTimeSymbols: DateTimeSymbols_gl
  },
  'hi': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_hi,
    DateTimeSymbols: DateTimeSymbols_hi
  },
  'zh': {
    DateIntervalSymbols: dateIntervalSymbols.DateIntervalSymbols_zh,
    DateTimeSymbols: DateTimeSymbols_zh
  }
};

/**
 * @param {string} locale
 * @param {!Array<number>} firstDate
 * @param {!Array<number>} secondDate
 * @param {number|!dateIntervalSymbols.DateIntervalPatternMap} pattern
 * @param {string} expected
 * @constructor
 */
var Data = function(locale, firstDate, secondDate, pattern, expected) {
  this.locale = locale;
  this.firstDate = firstDate;
  this.secondDate = secondDate;
  this.pattern = pattern;
  this.expected = expected;
};

/**
 * @return {string} Error description.
 */
Data.prototype.getErrorDescription = function() {
  return 'Error for locale:' + this.locale + ' firstDate:\'' + this.firstDate +
      '\' secondDate:\'' + this.secondDate + '\'';
};

// clang-format off
var formatTestData = [
  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.YEAR_FULL, '2007 – 2008'),

  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'January 10'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'January 10'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'January 10'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'November 10 – 20'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'October 10 – November 10'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.MONTH_DAY_FULL, 'October 10, 2007 – October 10, 2008'),

  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10 – 20'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10/10 – 11/10'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.DAY_ABBR, '10/10/2007 – 10/10/2008'),

  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Wed, Jan 10, 2007'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Wed, Jan 10, 2007'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Wed, Jan 10, 2007'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Sat, Nov 10 – Tue, Nov 20, 2007'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Wed, Oct 10 – Sat, Nov 10, 2007'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_en.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, 'Wed, Oct 10, 2007 – Fri, Oct 10, 2008'),

  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  DateTimeFormat.Format.SHORT_TIME, '10:10 AM'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  DateTimeFormat.Format.SHORT_TIME, '10:00 – 10:20 AM'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  DateTimeFormat.Format.SHORT_TIME, '10:00 AM – 2:10 PM'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], DateTimeFormat.Format.SHORT_TIME, '11/10/2007, 10:10 AM – 11/20/2007, 10:10 AM'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], DateTimeFormat.Format.SHORT_TIME, '10/10/2007, 10:10 AM – 11/10/2007, 10:10 AM'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  DateTimeFormat.Format.SHORT_TIME, '10/10/2007, 10:10 AM – 10/10/2008, 10:10 AM'),

  new Data('en', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  DateTimeFormat.Format.SHORT_DATETIME, '1/10/07, 10:10 AM'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  DateTimeFormat.Format.SHORT_DATETIME, '1/10/07, 10:00 – 10:20 AM'),
  new Data('en', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  DateTimeFormat.Format.SHORT_DATETIME, '1/10/07, 10:00 AM – 2:10 PM'),
  new Data('en', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], DateTimeFormat.Format.SHORT_DATETIME, '11/10/07, 10:10 AM – 11/20/07, 10:10 AM'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], DateTimeFormat.Format.SHORT_DATETIME, '10/10/07, 10:10 AM – 11/10/07, 10:10 AM'),
  new Data('en', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  DateTimeFormat.Format.SHORT_DATETIME, '10/10/07, 10:10 AM – 10/10/08, 10:10 AM'),

  new Data('ar', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠ يناير'),
  new Data('ar', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠ يناير'),
  new Data('ar', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠ يناير'),
  new Data('ar', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠–٢٠ نوفمبر'),
  new Data('ar', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠ أكتوبر – ١٠ نوفمبر'),
  new Data('ar', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_ar.MONTH_DAY_ABBR, '١٠ أكتوبر، ٢٠٠٧ – ١٠ أكتوبر، ٢٠٠٨'),

  new Data('fr_CA', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10 janvier'),
  new Data('fr_CA', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10 janvier'),
  new Data('fr_CA', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10 janvier'),
  new Data('fr_CA', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10–20 novembre'),
  new Data('fr_CA', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10 octobre – 10 novembre'),
  new Data('fr_CA', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_fr_CA.MONTH_DAY_MEDIUM, '10 octobre 2007 – 10 octobre 2008'),

  new Data('gl', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'Xaneiro de 2007'),
  new Data('gl', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'Xaneiro de 2007'),
  new Data('gl', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'Xaneiro de 2007'),
  new Data('gl', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'Novembro de 2007'),
  new Data('gl', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'outubro–novembro de 2007'),
  new Data('gl', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_gl.YEAR_MONTH_FULL, 'outubro de 2007 – outubro de 2008'),

  new Data('hi', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 जनवरी'),
  new Data('hi', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 जनवरी'),
  new Data('hi', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 जनवरी'),
  new Data('hi', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 नवंबर–20'),
  new Data('hi', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 अक्तूबर – 10 नवंबर'),
  new Data('hi', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_hi.MONTH_DAY_MEDIUM, '10 अक्तूबर 2007 – 10 अक्तूबर 2008'),

  new Data('zh', [2007, 0, 10, 10, 10, 10],  [2007, 0, 10, 10, 10, 20],  dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年1月10日周三'),
  new Data('zh', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 10, 20, 10],  dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年1月10日周三'),
  new Data('zh', [2007, 0, 10, 10, 0, 10],   [2007, 0, 10, 14, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年1月10日周三'),
  new Data('zh', [2007, 10, 10, 10, 10, 10], [2007, 10, 20, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年11月10日周六至20日周二'),
  new Data('zh', [2007, 9, 10, 10, 10, 10],  [2007, 10, 10, 10, 10, 10], dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年10月10日周三至11月10日周六'),
  new Data('zh', [2007, 9, 10, 10, 10, 10],  [2008, 9, 10, 10, 10, 10],  dateIntervalPatterns.DateIntervalPatterns_zh.WEEKDAY_MONTH_DAY_YEAR_MEDIUM, '2007年10月10日周三至2008年10月10日周五')
];
// clang-format on

testSuite({
  testFormat: function() {
    for (var i = 0; i < formatTestData.length; i++) {
      var data = formatTestData[i];
      var symbols = localeSymbols[data.locale];
      var dt1 = new Date(Date.UTC.apply(null, data.firstDate));
      var dt2 = new Date(Date.UTC.apply(null, data.secondDate));
      var fmt = new DateIntervalFormat(
          data.pattern, symbols.DateIntervalSymbols, symbols.DateTimeSymbols);
      var tz = TimeZone.createTimeZone(0);
      assertEquals(
          data.getErrorDescription(), data.expected, fmt.format(dt1, dt2, tz));
    }
  },

  testRangeFormat: function() {
    var dt1 = new GoogDate(2007, 1, 10);
    var dt2 = new GoogDate(2007, 6, 3);
    var dtRng = new DateRange(dt1, dt2);
    var fmt = new DateIntervalFormat(DateTimeFormat.Format.LONG_DATE);
    assertEquals('February 10 – July 3, 2007', fmt.formatRange(dtRng));
  },

  testDateAndIntervalFormat: function() {
    var dt = new GoogDate(2007, 1, 10);
    var itv = new Interval(0, 4, 23);
    var fmt = new DateIntervalFormat(DateTimeFormat.Format.LONG_DATE);
    assertEquals('February 10 – July 3, 2007', fmt.format(dt, itv));
  },

  testNewYearFormat: function() {
    var dt1 = new Date(Date.UTC(2007, 0, 1, 3, 0, 23));
    var dt2 = new Date(Date.UTC(2007, 0, 1, 3, 40, 23));
    var fmt = new DateIntervalFormat(DateTimeFormat.Format.FULL_DATETIME);
    var tz = TimeZone.createTimeZone(210);
    assertEquals(
        'Sunday, December 31, 2006 at 11:30:23 PM UTC-3:30 – ' +
            'Monday, January 1, 2007 at 12:10:23 AM UTC-3:30',
        fmt.format(dt1, dt2, tz));
  },

  testTimeZone: function() {
    var dt1 = new Date(Date.UTC(2007, 0, 10, 6, 0, 23));
    var dt2 = new Date(Date.UTC(2007, 0, 10, 6, 20, 23));
    var fmt = new DateIntervalFormat(DateTimeFormat.Format.LONG_TIME);
    var tz = TimeZone.createTimeZone(240);
    assertEquals(
        '2:00:23 AM UTC-4 – 2:20:23 AM UTC-4', fmt.format(dt1, dt2, tz));
  },

  testFormatSecondDateWithFirstPattern: function() {
    // Set the new fallback pattern.
    var symbols = object.clone(dateIntervalSymbols.getDateIntervalSymbols());
    symbols.FALLBACK = '{1} – {0}';
    // Format the dates.
    var dt1 = new GoogDate(2007, 1, 10);
    var dt2 = new GoogDate(2007, 6, 3);
    var fmt = new DateIntervalFormat(DateTimeFormat.Format.LONG_DATE, symbols);
    assertEquals('July 3 – February 10, 2007', fmt.format(dt1, dt2));
  },

  testGetLargestDifferentCalendarField: function() {
    // Era
    var dt1 = new DateTime(-1, 1, 10);
    var dt2 = new DateTime(2007, 6, 3);
    var calField =
        DateIntervalFormat.getLargestDifferentCalendarField_(dt1, dt2);
    assertEquals('G', calField);
    // Month
    dt1 = new DateTime(2007, 1, 10);
    dt2 = new DateTime(2007, 6, 3);
    calField = DateIntervalFormat.getLargestDifferentCalendarField_(dt1, dt2);
    assertEquals('M', calField);
    // AmPm
    dt1 = new DateTime(2007, 1, 10, 10);
    dt2 = new DateTime(2007, 1, 10, 14);
    calField = DateIntervalFormat.getLargestDifferentCalendarField_(dt1, dt2);
    assertEquals('a', calField);
    // AmPm + Timezone
    dt1 = new Date(Date.UTC(2007, 1, 10, 8, 25));
    dt2 = new Date(Date.UTC(2007, 1, 10, 8, 35));
    var tz = new TimeZone.createTimeZone(-210);
    calField =
        DateIntervalFormat.getLargestDifferentCalendarField_(dt1, dt2, tz);
    assertEquals('a', calField);
    // Seconds
    dt1 = new DateTime(2007, 1, 10, 10, 0, 1);
    dt2 = new DateTime(2007, 1, 10, 10, 0, 10);
    calField = DateIntervalFormat.getLargestDifferentCalendarField_(dt1, dt2);
    assertEquals('s', calField);
  },

  testDivideIntervalPattern: function() {
    var pttn = DateIntervalFormat.divideIntervalPattern_('MMM d – d, y');
    assertObjectEquals({firstPart: 'MMM d – ', secondPart: 'd, y'}, pttn);
    pttn = DateIntervalFormat.divideIntervalPattern_('MMM d, y');
    assertNull(pttn);
  },

  testIsCalendarFieldLargerOrEqualThan: function() {
    assertTrue(DateIntervalFormat.isCalendarFieldLargerOrEqualThan_('G', 's'));
    assertTrue(DateIntervalFormat.isCalendarFieldLargerOrEqualThan_('a', 'm'));
    assertFalse(DateIntervalFormat.isCalendarFieldLargerOrEqualThan_('a', 'y'));
    assertFalse(DateIntervalFormat.isCalendarFieldLargerOrEqualThan_('a', '-'));
  }
});
