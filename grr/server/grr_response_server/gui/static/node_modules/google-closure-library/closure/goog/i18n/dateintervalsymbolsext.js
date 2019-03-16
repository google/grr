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

/**
 * @fileoverview Date interval formatting symbols for all locales.
 *
 * File generated from CLDR ver. 31.0.1
 *
 * This file covers those locales that are not covered in
 * "dateintervalsymbols.js".
 */

// clang-format off

goog.module('goog.i18n.dateIntervalSymbolsExt');

var dateIntervalSymbols = goog.require('goog.i18n.dateIntervalSymbols');

/** @type {!dateIntervalSymbols.DateIntervalSymbols} */
var defaultSymbols;

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_af_NA = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'd': 'EEEE, d MMMM – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_af_ZA = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'd': 'EEEE, d MMMM – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_agq = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_agq_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ak = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'yy/MM/dd'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'yy/MM/dd h:mm a – h:mm a',
    'hm': 'yy/MM/dd h:mm–h:mm a',
    '_': 'yy/MM/dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ak_GH = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'yy/MM/dd'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'yy/MM/dd h:mm a – h:mm a',
    'hm': 'yy/MM/dd h:mm–h:mm a',
    '_': 'yy/MM/dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_am_ET = {
  FULL_DATE: {
    'Md': 'EEEE MMMM d – EEEE MMMM d፣ y',
    'y': 'EEEE፣ MMMM d፣ y – EEEE፣ MMMM d፣ y',
    '_': 'EEEE ፣d MMMM y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d፣ y',
    'd': 'MMMM d–d፣ y',
    'y': 'MMMM d፣ y – MMMM d፣ y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d፣ y',
    'd': 'MMM d–d፣ y',
    'y': 'MMM d፣ y – MMM d፣ y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE ፣d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_001 = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_AE = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_BH = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_DJ = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_EG = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_EH = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_ER = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_IL = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y H:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd‏/M‏/y HH:mm–HH:mm',
    '_': 'd‏/M‏/y H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_IQ = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_JO = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_KM = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd‏/M‏/y HH:mm–HH:mm',
    '_': 'd‏/M‏/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_KW = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_LB = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_LY = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_MA = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd‏/M‏/y HH:mm–HH:mm',
    '_': 'd‏/M‏/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_MR = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_OM = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_PS = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_QA = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_SA = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_SD = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_SO = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_SS = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_SY = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_TD = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_TN = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_XB = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y \'؜‮at‬؜\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y \'؜‮at‬؜\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ar_YE = {
  FULL_DATE: {
    'M': 'EEEE، d MMMM – EEEE، d MMMM، y',
    'd': 'EEEE، d – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'd–d MMMM، y',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd‏/M‏/y – d‏/M‏/y',
    '_': 'dd‏/MM‏/y'
  },
  SHORT_DATE: {
    '_': 'd‏/M‏/y'
  },
  FULL_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd‏/M‏/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd‏/M‏/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd‏/MM‏/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd‏/M‏/y h:mm a – h:mm a',
    'hm': 'd‏/M‏/y h:mm–h:mm a',
    '_': 'd‏/M‏/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_as = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_as_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_asa = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_asa_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ast = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM \'de\' y',
    'd': 'd – d MMM \'de\' y',
    'y': 'd MMM \'de\' y – d MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, HH:mm – HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ast_ES = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM \'de\' y',
    'd': 'd – d MMM \'de\' y',
    'y': 'd MMM \'de\' y – d MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, HH:mm – HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_az_Cyrl = {
  FULL_DATE: {
    'Md': 'd MMMM y, EEEE – d MMMM, EEEE',
    '_': 'd MMMM y, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM y – d MMMM',
    'd': 'y MMMM d–d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM y – d MMM',
    'd': 'y MMM d–d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_az_Cyrl_AZ = {
  FULL_DATE: {
    'Md': 'd MMMM y, EEEE – d MMMM, EEEE',
    '_': 'd MMMM y, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM y – d MMMM',
    'd': 'y MMMM d–d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM y – d MMM',
    'd': 'y MMM d–d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_az_Latn = {
  FULL_DATE: {
    'Md': 'd MMMM y, EEEE – d MMMM, EEEE',
    '_': 'd MMMM y, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM y – d MMMM',
    'd': 'y MMMM d–d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM y – d MMM',
    'd': 'y MMM d–d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_az_Latn_AZ = {
  FULL_DATE: {
    'Md': 'd MMMM y, EEEE – d MMMM, EEEE',
    '_': 'd MMMM y, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM y – d MMMM',
    'd': 'y MMMM d–d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM y – d MMM',
    'd': 'y MMM d–d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bas = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bas_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_be_BY = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y – d.M.y',
    '_': 'd.MM.y'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy – d.M.yy',
    '_': 'd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss, zzzz',
    '_': 'HH:mm:ss, zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss, z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH.mm–HH.mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'. \'у\' HH:mm:ss, zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'. \'у\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.MM.yy, HH.mm–HH.mm',
    '_': 'd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bem = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bem_ZM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bez = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bez_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bg_BG = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd – d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'Md': 'd.MM – d.MM.y \'г\'.',
    '_': 'd.MM.y \'г\'.'
  },
  SHORT_DATE: {
    'Md': 'd.MM – d.MM.yy \'г\'.',
    '_': 'd.MM.yy \'г\'.'
  },
  FULL_TIME: {
    'Mdy': 'd.MM.y \'г\'., H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.MM.y \'г\'., H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.MM.y \'г\'., H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.MM.y \'г\'., H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.MM.y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.MM.yy \'г\'., H:mm – H:mm',
    '_': 'd.MM.yy \'г\'., H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bm = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bm_ML = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bn_BD = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bn_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y MMMMའི་ཚེས་d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y ལོའི་MMMཚེས་d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMMའི་ཚེས་d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y ལོའི་MMMཚེས་d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bo_CN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y MMMMའི་ཚེས་d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y ལོའི་MMMཚེས་d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMMའི་ཚེས་d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y ལོའི་MMMཚེས་d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bo_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y MMMMའི་ཚེས་d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y ལོའི་MMMཚེས་d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMMའི་ཚེས་d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'སྤྱི་ལོ་y MMMMའི་ཚེས་d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y ལོའི་MMMཚེས་d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_br_FR = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE \'da\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d \'da\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_brx = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy h:mm a – h:mm a',
    'hm': 'M/d/yy h:mm–h:mm a',
    '_': 'M/d/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_brx_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy h:mm a – h:mm a',
    'hm': 'M/d/yy h:mm–h:mm a',
    '_': 'M/d/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bs_Cyrl = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    'y': 'EEEE, dd. MMMM y. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    'y': 'dd. MMMM y. – dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy. – d.M.yy.',
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bs_Cyrl_BA = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    'y': 'EEEE, dd. MMMM y. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    'y': 'dd. MMMM y. – dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy. – d.M.yy.',
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bs_Latn = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y.',
    'd': 'EEEE, d. – EEEE, d. MMMM y.',
    'y': 'EEEE, d. MMMM y. – EEEE, d. MMMM y.',
    '_': 'EEEE, d. MMMM y.'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y.',
    'd': 'd. – d. MMMM y.',
    'y': 'd. MMMM y. – d. MMMM y.',
    '_': 'd. MMMM y.'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y.',
    'd': 'd. – d. MMM y.',
    'y': 'd. MMM y. – d. MMM y.',
    '_': 'd. MMM. y.'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy. – d.M.yy.',
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y. \'u\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y. \'u\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM. y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm – HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_bs_Latn_BA = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y.',
    'd': 'EEEE, d. – EEEE, d. MMMM y.',
    'y': 'EEEE, d. MMMM y. – EEEE, d. MMMM y.',
    '_': 'EEEE, d. MMMM y.'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y.',
    'd': 'd. – d. MMMM y.',
    'y': 'd. MMMM y. – d. MMMM y.',
    '_': 'd. MMMM y.'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y.',
    'd': 'd. – d. MMM y.',
    'y': 'd. MMM y. – d. MMM y.',
    '_': 'd. MMM. y.'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy. – d.M.yy.',
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y. \'u\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y. \'u\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM. y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm – HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ca_AD = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    'd': 'EEEE, d – EEEE, d MMMM \'de\' y',
    'y': 'EEEE, d MMMM \'de\' y – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd–d MMMM \'de\' y',
    'y': 'd MMMM \'de\' y – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, H:mm',
    'ahm': 'H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, H:mm – H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ca_ES = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    'd': 'EEEE, d – EEEE, d MMMM \'de\' y',
    'y': 'EEEE, d MMMM \'de\' y – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd–d MMMM \'de\' y',
    'y': 'd MMMM \'de\' y – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, H:mm',
    'ahm': 'H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, H:mm – H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ca_FR = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    'd': 'EEEE, d – EEEE, d MMMM \'de\' y',
    'y': 'EEEE, d MMMM \'de\' y – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd–d MMMM \'de\' y',
    'y': 'd MMMM \'de\' y – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, H:mm',
    'ahm': 'H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, H:mm – H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ca_IT = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM \'de\' y',
    'd': 'EEEE, d – EEEE, d MMMM \'de\' y',
    'y': 'EEEE, d MMMM \'de\' y – EEEE, d MMMM \'de\' y',
    '_': 'EEEE, d MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd–d MMMM \'de\' y',
    'y': 'd MMMM \'de\' y – d MMMM \'de\' y',
    '_': 'd MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, H:mm',
    'ahm': 'H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM \'de\' y \'a\' \'les\' H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM \'de\' y \'a\' \'les\' H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, H:mm – H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ce = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ce_RU = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_cgg = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_cgg_UG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_chr_US = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y ᎤᎾᎢ h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y ᎤᎾᎢ h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ckb = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dی MMMMی y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dی MMMMی y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ckb_IQ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dی MMMMی y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dی MMMMی y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ckb_IR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dی MMMMی y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dی MMMMی y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_cs_CZ = {
  FULL_DATE: {
    'Md': 'EEEE d. M. – EEEE d. M. y',
    'y': 'EEEE d. M. y – EEEE d. M. y',
    '_': 'EEEE d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. M. – d. M. y',
    'd': 'd.–d. M. y',
    'y': 'd. M. y – d. M. y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd.MM.y – dd.MM.y',
    '_': 'd. M. y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd. M. y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd. M. y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd. M. y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd. M. y H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d. MMMM y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. M. y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd. MM. yy H:mm–H:mm',
    '_': 'dd.MM.yy H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_cy_GB = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM, y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM, y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'am\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'am\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_da_DK = {
  FULL_DATE: {
    'Md': 'EEEE \'den\' d.–EEEE \'den\' d. MMMM y',
    'y': 'EEEE \'den\' d. MMMM y–EEEE \'den\' d. MMMM y',
    '_': 'EEEE \'den\' d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM.–d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM.–d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y–dd/MM/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH.mm.ss zzzz',
    '_': 'HH.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH.mm.ss z',
    '_': 'HH.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH.mm.ss',
    '_': 'HH.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH.mm',
    'ahm': 'HH.mm–HH.mm',
    '_': 'HH.mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE \'den\' d. MMMM y \'kl\'. HH.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH.mm–HH.mm',
    '_': 'dd/MM/y HH.mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_da_GL = {
  FULL_DATE: {
    'Md': 'EEEE \'den\' d.–EEEE \'den\' d. MMMM y',
    'y': 'EEEE \'den\' d. MMMM y–EEEE \'den\' d. MMMM y',
    '_': 'EEEE \'den\' d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM.–d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM.–d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y–dd/MM/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h.mm.ss a zzzz',
    '_': 'h.mm.ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h.mm.ss a z',
    '_': 'h.mm.ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h.mm.ss a',
    '_': 'h.mm.ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h.mm a',
    'a': 'h.mm a–h.mm a',
    'hm': 'h.mm–h.mm a',
    '_': 'h.mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE \'den\' d. MMMM y \'kl\'. h.mm.ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. h.mm.ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y h.mm.ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h.mm a–h.mm a',
    'hm': 'dd/MM/y h.mm–h.mm a',
    '_': 'dd/MM/y h.mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dav = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dav_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_de_BE = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm \'Uhr\'',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'um\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'um\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm \'Uhr\'',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_de_DE = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm \'Uhr\'',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'um\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'um\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm \'Uhr\'',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_de_IT = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm \'Uhr\'',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'um\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'um\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm \'Uhr\'',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_de_LI = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm \'Uhr\'',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'um\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'um\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm \'Uhr\'',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_de_LU = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm \'Uhr\'',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'um\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'um\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm \'Uhr\'',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dje = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dje_NE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dsb = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd.M.y'
  },
  SHORT_DATE: {
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y H:mm',
    'ahm': '\'zeg\'. H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.M.y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy \'zeg\'. H:mm – H:mm',
    '_': 'd.M.yy H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dsb_DE = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd.M.y'
  },
  SHORT_DATE: {
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y H:mm',
    'ahm': '\'zeg\'. H:mm – H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.M.y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy \'zeg\'. H:mm – H:mm',
    '_': 'd.M.yy H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dua = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dua_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dyo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dyo_SN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dz = {
  FULL_DATE: {
    'Mdy': 'EEEE, y-MM-dd – EEEE, y-MM-dd',
    '_': 'EEEE, སྤྱི་ལོ་y MMMM ཚེས་dd'
  },
  LONG_DATE: {
    'M': 'y-MM-dd – MM-d',
    'd': 'y-MM-d – d',
    'y': 'y-MM-dd – y-MM-dd',
    '_': 'སྤྱི་ལོ་y MMMM ཚེས་ dd'
  },
  MEDIUM_DATE: {
    'M': 'y-MM-dd – MM-d',
    'd': 'y-MM-d – d',
    'y': 'y-MM-dd – y-MM-dd',
    '_': 'སྤྱི་ལོ་y ཟླ་MMM ཚེས་dd'
  },
  SHORT_DATE: {
    'M': 'y-MM-dd – MM-dd',
    'd': 'y-MM-dd – dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་h:mm:ss a',
    '_': 'ཆུ་ཚོད་h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, སྤྱི་ལོ་y MMMM ཚེས་dd ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'སྤྱི་ལོ་y MMMM ཚེས་ dd ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'སྤྱི་ལོ་y ཟླ་MMM ཚེས་dd ཆུ་ཚོད་h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd ཆུ་ཚོད་ h སྐར་མ་ mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_dz_BT = {
  FULL_DATE: {
    'Mdy': 'EEEE, y-MM-dd – EEEE, y-MM-dd',
    '_': 'EEEE, སྤྱི་ལོ་y MMMM ཚེས་dd'
  },
  LONG_DATE: {
    'M': 'y-MM-dd – MM-d',
    'd': 'y-MM-d – d',
    'y': 'y-MM-dd – y-MM-dd',
    '_': 'སྤྱི་ལོ་y MMMM ཚེས་ dd'
  },
  MEDIUM_DATE: {
    'M': 'y-MM-dd – MM-d',
    'd': 'y-MM-d – d',
    'y': 'y-MM-dd – y-MM-dd',
    '_': 'སྤྱི་ལོ་y ཟླ་MMM ཚེས་dd'
  },
  SHORT_DATE: {
    'M': 'y-MM-dd – MM-dd',
    'd': 'y-MM-dd – dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་h:mm:ss a',
    '_': 'ཆུ་ཚོད་h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d ཆུ་ཚོད་ h སྐར་མ་ mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'ཆུ་ཚོད་ h སྐར་མ་ mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, སྤྱི་ལོ་y MMMM ཚེས་dd ཆུ་ཚོད་ h སྐར་མ་ mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'སྤྱི་ལོ་y MMMM ཚེས་ dd ཆུ་ཚོད་ h སྐར་མ་ mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'སྤྱི་ལོ་y ཟླ་MMM ཚེས་dd ཆུ་ཚོད་h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd ཆུ་ཚོད་ h སྐར་མ་ mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ebu = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ebu_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ee = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d \'lia\' – EEEE, MMMM d \'lia\', y',
    'y': 'EEEE, MMMM d \'lia\', y – EEEE, MMMM d \'lia\', y',
    '_': 'EEEE, MMMM d \'lia\' y'
  },
  LONG_DATE: {
    'M': 'MMMM d \'lia\' – MMMM d \'lia\', y',
    'd': 'MMMM d \'lia\' – d \'lia\' , y',
    'y': 'MMMM d \'lia\' , y – MMMM d \'lia\', y',
    '_': 'MMMM d \'lia\' y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d \'lia\' – MMM d \'lia\', y',
    'd': 'MMM d \'lia\' – d \'lia\' , y',
    'y': 'MMM d \'lia\' , y – MMM d \'lia\', y',
    '_': 'MMM d \'lia\', y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/yy – M/d/yy',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss zzzz M/d/y',
    '_': 'a \'ga\' h:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss z M/d/y',
    '_': 'a \'ga\' h:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss M/d/y',
    '_': 'a \'ga\' h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'a \'ga\' h:mm M/d/y',
    'a': 'a \'ga\' h:mm – a \'ga\' h:mm',
    'h': 'a \'ga\' h:mm - \'ga\' h:mm',
    'm': 'a \'ga\' h:mm – \'ga\' h:mm',
    '_': 'a \'ga\' h:mm'
  },
  FULL_DATETIME: {
    '_': 'a \'ga\' h:mm:ss zzzz EEEE, MMMM d \'lia\' y'
  },
  LONG_DATETIME: {
    '_': 'a \'ga\' h:mm:ss z MMMM d \'lia\' y'
  },
  MEDIUM_DATETIME: {
    '_': 'a \'ga\' h:mm:ss MMM d \'lia\', y'
  },
  SHORT_DATETIME: {
    'a': 'a \'ga\' h:mm – a \'ga\' h:mm M/d/yy',
    'h': 'a \'ga\' h:mm - \'ga\' h:mm M/d/yy',
    'm': 'a \'ga\' h:mm – \'ga\' h:mm M/d/yy',
    '_': 'a \'ga\' h:mm M/d/yy'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ee_GH = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d \'lia\' – EEEE, MMMM d \'lia\', y',
    'y': 'EEEE, MMMM d \'lia\', y – EEEE, MMMM d \'lia\', y',
    '_': 'EEEE, MMMM d \'lia\' y'
  },
  LONG_DATE: {
    'M': 'MMMM d \'lia\' – MMMM d \'lia\', y',
    'd': 'MMMM d \'lia\' – d \'lia\' , y',
    'y': 'MMMM d \'lia\' , y – MMMM d \'lia\', y',
    '_': 'MMMM d \'lia\' y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d \'lia\' – MMM d \'lia\', y',
    'd': 'MMM d \'lia\' – d \'lia\' , y',
    'y': 'MMM d \'lia\' , y – MMM d \'lia\', y',
    '_': 'MMM d \'lia\', y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/yy – M/d/yy',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss zzzz M/d/y',
    '_': 'a \'ga\' h:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss z M/d/y',
    '_': 'a \'ga\' h:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'a \'ga\' h:mm:ss M/d/y',
    '_': 'a \'ga\' h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'a \'ga\' h:mm M/d/y',
    'a': 'a \'ga\' h:mm – a \'ga\' h:mm',
    'h': 'a \'ga\' h:mm - \'ga\' h:mm',
    'm': 'a \'ga\' h:mm – \'ga\' h:mm',
    '_': 'a \'ga\' h:mm'
  },
  FULL_DATETIME: {
    '_': 'a \'ga\' h:mm:ss zzzz EEEE, MMMM d \'lia\' y'
  },
  LONG_DATETIME: {
    '_': 'a \'ga\' h:mm:ss z MMMM d \'lia\' y'
  },
  MEDIUM_DATETIME: {
    '_': 'a \'ga\' h:mm:ss MMM d \'lia\', y'
  },
  SHORT_DATETIME: {
    'a': 'a \'ga\' h:mm – a \'ga\' h:mm M/d/yy',
    'h': 'a \'ga\' h:mm - \'ga\' h:mm M/d/yy',
    'm': 'a \'ga\' h:mm – \'ga\' h:mm M/d/yy',
    '_': 'a \'ga\' h:mm M/d/yy'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ee_TG = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d \'lia\' – EEEE, MMMM d \'lia\', y',
    'y': 'EEEE, MMMM d \'lia\', y – EEEE, MMMM d \'lia\', y',
    '_': 'EEEE, MMMM d \'lia\' y'
  },
  LONG_DATE: {
    'M': 'MMMM d \'lia\' – MMMM d \'lia\', y',
    'd': 'MMMM d \'lia\' – d \'lia\' , y',
    'y': 'MMMM d \'lia\' , y – MMMM d \'lia\', y',
    '_': 'MMMM d \'lia\' y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d \'lia\' – MMM d \'lia\', y',
    'd': 'MMM d \'lia\' – d \'lia\' , y',
    'y': 'MMM d \'lia\' , y – MMM d \'lia\', y',
    '_': 'MMM d \'lia\', y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/yy – M/d/yy',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'HH:mm:ss zzzz M/d/y',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'HH:mm:ss z M/d/y',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'HH:mm:ss M/d/y',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'HH:mm M/d/y',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'HH:mm:ss zzzz EEEE, MMMM d \'lia\' y'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z MMMM d \'lia\' y'
  },
  MEDIUM_DATETIME: {
    '_': 'HH:mm:ss MMM d \'lia\', y'
  },
  SHORT_DATETIME: {
    'ahm': 'HH:mm–HH:mm M/d/yy',
    '_': 'HH:mm M/d/yy'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_el_CY = {
  FULL_DATE: {
    'Md': 'EEEE, dd MMMM – EEEE, dd MMMM y',
    'y': 'EEEE, dd MMMM y – EEEE, dd MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y - h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y - h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm–h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_el_GR = {
  FULL_DATE: {
    'Md': 'EEEE, dd MMMM – EEEE, dd MMMM y',
    'y': 'EEEE, dd MMMM y – EEEE, dd MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y - h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y - h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm–h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_001 = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_150 = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_AG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_AI = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_AS = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_AT = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BB = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BE = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BI = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BS = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BW = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_BZ = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CC = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CH = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CX = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_CY = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_DE = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_DG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_DK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH.mm.ss zzzz',
    '_': 'HH.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH.mm.ss z',
    '_': 'HH.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH.mm.ss',
    '_': 'HH.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH.mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH.mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH.mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_DM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_ER = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_FI = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, H.mm.ss zzzz',
    '_': 'H.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, H.mm.ss z',
    '_': 'H.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, H.mm.ss',
    '_': 'H.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, H.mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'H.mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' H.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' H.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, H.mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_FJ = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_FK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_FM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GD = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GH = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GI = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GU = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_GY = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_HK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y, h:mm a – h:mm a',
    'hm': 'd/M/y, h:mm – h:mm a',
    '_': 'd/M/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_IL = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, H:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_IM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_IO = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_JE = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_JM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_KE = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_KI = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_KN = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_KY = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_LC = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_LR = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_LS = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MH = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MO = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MP = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MS = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MT = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MU = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MW = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_MY = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NA = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NF = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NL = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NR = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NU = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_NZ = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd/MM/y'
  },
  SHORT_DATE: {
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd/MM/y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/yy, h:mm a – h:mm a',
    'hm': 'd/MM/yy, h:mm – h:mm a',
    '_': 'd/MM/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PH = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PN = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PR = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_PW = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_RW = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SB = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SC = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SD = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SE = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd, HH:mm – HH:mm',
    '_': 'y-MM-dd, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SH = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SI = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SL = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SS = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SX = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_SZ = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TC = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TO = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TT = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TV = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_TZ = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_UG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_UM = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_US_POSIX = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_VC = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_VG = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_VI = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm – h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_VU = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_WS = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_XA = {
  FULL_DATE: {
    'Md': '[EEEE, MMMM d – EEEE, MMMM d, y]',
    'y': '[EEEE, MMMM d, y – EEEE, MMMM d, y]',
    '_': '[EEEE, MMMM d, y]'
  },
  LONG_DATE: {
    'M': '[MMMM d – MMMM d, y]',
    'd': '[MMMM d – d, y]',
    'y': '[MMMM d, y – MMMM d, y]',
    '_': '[MMMM d, y]'
  },
  MEDIUM_DATE: {
    'M': '[MMM d – MMM d, y]',
    'd': '[MMM d – d, y]',
    'y': '[MMM d, y – MMM d, y]',
    '_': '[MMM d, y]'
  },
  SHORT_DATE: {
    'Mdy': '[M/d/yy – M/d/yy]',
    '_': '[M/d/yy]'
  },
  FULL_TIME: {
    'Mdy': '[[M/d/y], [h:mm:ss a zzzz]]',
    '_': '[h:mm:ss a zzzz]'
  },
  LONG_TIME: {
    'Mdy': '[[M/d/y], [h:mm:ss a z]]',
    '_': '[h:mm:ss a z]'
  },
  MEDIUM_TIME: {
    'Mdy': '[[M/d/y], [h:mm:ss a]]',
    '_': '[h:mm:ss a]'
  },
  SHORT_TIME: {
    'Mdy': '[[M/d/y], [h:mm a]]',
    'a': '[h:mm a – h:mm a]',
    'hm': '[h:mm – h:mm a]',
    '_': '[h:mm a]'
  },
  FULL_DATETIME: {
    '_': '[[EEEE, MMMM d, y] \'åţ\' [h:mm:ss a zzzz] \'one\']'
  },
  LONG_DATETIME: {
    '_': '[[MMMM d, y] \'åţ\' [h:mm:ss a z] \'one\']'
  },
  MEDIUM_DATETIME: {
    '_': '[[MMM d, y], [h:mm:ss a]]'
  },
  SHORT_DATETIME: {
    'a': '[[M/d/yy], [h:mm a – h:mm a]]',
    'hm': '[[M/d/yy], [h:mm – h:mm a]]',
    '_': '[[M/d/yy], [h:mm a]]'
  },
  FALLBACK: '[{0} – {1} one]'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_ZM = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'at\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'at\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y, h:mm a – h:mm a',
    'hm': 'dd/MM/y, h:mm – h:mm a',
    '_': 'dd/MM/y, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_en_ZW = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dd MMM,y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y \'at\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y \'at\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM,y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y, HH:mm – HH:mm',
    '_': 'd/M/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_eo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d-\'a\' \'de\' MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'y-MMMM-dd'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y-MMM-dd'
  },
  SHORT_DATE: {
    '_': 'yy-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d H-\'a\' \'horo\' \'kaj\' m:ss zzzz',
    '_': 'H-\'a\' \'horo\' \'kaj\' m:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d H-\'a\' \'horo\' \'kaj\' m:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d-\'a\' \'de\' MMMM y H-\'a\' \'horo\' \'kaj\' m:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y-MMMM-dd HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y-MMM-dd HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'yy-MM-dd HH:mm–HH:mm',
    '_': 'yy-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_AR = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM \'al\' d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y \'al\' d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} a el {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_BO = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM \'de\' y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM \'de\' y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_BR = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_BZ = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_CL = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd-MM-y – dd-MM-y',
    '_': 'dd-MM-y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MM-y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy H:mm–H:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} a el {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_CO = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'My': 'd/MM/y \'al\' d/MM/y',
    'd': 'd/MM/y \'a\' d/MM/y',
    '_': 'd/MM/y'
  },
  SHORT_DATE: {
    'My': 'd/MM/yy \'al\' d/MM/yy',
    'd': 'd/MM/yy \'a\' d/MM/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'a': 'h:mm a \'a\' h:mm a',
    'hm': 'h:mm \'a\' h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd/MM/y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/yy, h:mm a \'a\' h:mm a',
    'hm': 'd/MM/yy, h:mm \'a\' h:mm a',
    '_': 'd/MM/yy, h:mm a'
  },
  FALLBACK: '{0} ‘al’ {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_CR = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_CU = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_DO = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_EA = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y H:mm:ss (z)',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_EC = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_GQ = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y H:mm:ss (z)',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_GT = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/MM/y – d/MM/y',
    '_': 'd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'd/MM/yy – d/MM/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd/MM/y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/MM/yy H:mm–H:mm',
    '_': 'd/MM/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_HN = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE dd \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y–d \'de\' MMMM \'de\' y',
    '_': 'dd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE dd \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_IC = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y H:mm:ss (z)',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy H:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_NI = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_PA = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y–d/M/y',
    '_': 'MM/dd/y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy–d/M/yy',
    '_': 'MM/dd/yy'
  },
  FULL_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'MM/dd/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MM/dd/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'MM/dd/yy h:mm a – h:mm a',
    'hm': 'MM/dd/yy h:mm – h:mm a',
    '_': 'MM/dd/yy h:mm a'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_PE = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy–d/M/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/MM/yy H:mm–H:mm',
    '_': 'd/MM/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_PH = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_PR = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y–d/M/y',
    '_': 'MM/dd/y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy–d/M/yy',
    '_': 'MM/dd/yy'
  },
  FULL_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'MM/dd/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'MM/dd/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MM/dd/y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'MM/dd/yy h:mm a – h:mm a',
    'hm': 'MM/dd/yy h:mm – h:mm a',
    '_': 'MM/dd/yy h:mm a'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_PY = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM \'al\' d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy \'al\' d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_SV = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_UY = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy H:mm–H:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_es_VE = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM–EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM–d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd \'de\' MMM – d \'de\' MMM \'de\' y',
    'd': 'd – d \'de\' MMM \'de\' y',
    'y': 'd \'de\' MMM \'de\' y – d \'de\' MMM \'de\' y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_et_EE = {
  FULL_DATE: {
    'Md': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y – d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_eu_ES = {
  FULL_DATE: {
    'M': 'y(\'e\')\'ko\' MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y(\'e\')\'ko\' MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y(\'e\')\'ko\' MMMM d – MMMM d',
    'd': 'y(\'e\')\'ko\' MMMM d–d',
    '_': 'y(\'e\')\'ko\' MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y(\'e\')\'ko\' MMM d – MMM d',
    'd': 'y(\'e\')\'ko\' MMM d–d',
    'y': 'y(\'e\')\'ko\' MMM d – y(\'e\')\'ko\' MMM d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'yy/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d HH:mm:ss (zzzz)',
    '_': 'HH:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d HH:mm:ss (z)',
    '_': 'HH:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y(\'e\')\'ko\' MMMM d, EEEE HH:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'y(\'e\')\'ko\' MMMM d HH:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'yy/M/d HH:mm–HH:mm',
    '_': 'yy/M/d HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ewo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ewo_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fa_AF = {
  FULL_DATE: {
    'Md': 'EEEE d LLLL تا EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd LLLL تا d MMMM y',
    'd': 'd تا d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd LLL تا d MMM y',
    'd': 'd تا d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y،‏ H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y،‏ H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y،‏ H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y،‏ H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y، ساعت H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y، ساعت H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y،‏ H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'M/d/y،‏ H:mm تا H:mm',
    '_': 'y/M/d،‏ H:mm'
  },
  FALLBACK: '{0} تا {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fa_IR = {
  FULL_DATE: {
    'Md': 'EEEE d LLLL تا EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd LLLL تا d MMMM y',
    'd': 'd تا d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd LLL تا d MMM y',
    'd': 'd تا d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d،‏ H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d،‏ H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d،‏ H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d،‏ H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y، ساعت H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y، ساعت H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y،‏ H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y/M/d،‏ H:mm تا H:mm',
    '_': 'y/M/d،‏ H:mm'
  },
  FALLBACK: '{0} تا {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ff = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ff_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ff_GN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ff_MR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y h:mm a – h:mm a',
    'hm': 'd/M/y h:mm–h:mm a',
    '_': 'd/M/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ff_SN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fi_FI = {
  FULL_DATE: {
    '_': 'cccc d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd.M.–d.M.y',
    'd': 'd.–d.M.y',
    '_': 'd.M.y'
  },
  SHORT_DATE: {
    'M': 'd.M.–d.M.y',
    'd': 'd.–d.M.y',
    '_': 'd.M.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y \'klo\' H.mm.ss zzzz',
    '_': 'H.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y \'klo\' H.mm.ss z',
    '_': 'H.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y \'klo\' H.mm.ss',
    '_': 'H.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y \'klo\' H.mm',
    '_': 'H.mm'
  },
  FULL_DATETIME: {
    '_': 'cccc d. MMMM y \'klo\' H.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'klo\' H.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.M.y \'klo\' H.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.y \'klo\' H.mm–H.mm',
    '_': 'd.M.y H.mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fil_PH = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d–d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d–d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y, h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y \'nang\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y \'nang\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy, h:mm a – h:mm a',
    'hm': 'M/d/yy, h:mm–h:mm a',
    '_': 'M/d/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fo = {
  FULL_DATE: {
    'Md': 'EEEE dd. MMMM–EEEE dd. MMMM y',
    'y': 'EEEE dd. MMMM y–EEEE dd. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'dd. MMMM–dd. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'dd. MMMM y–dd. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy–dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fo_DK = {
  FULL_DATE: {
    'Md': 'EEEE dd. MMMM–EEEE dd. MMMM y',
    'y': 'EEEE dd. MMMM y–EEEE dd. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'dd. MMMM–dd. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'dd. MMMM y–dd. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy–dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fo_FO = {
  FULL_DATE: {
    'Md': 'EEEE dd. MMMM–EEEE dd. MMMM y',
    'y': 'EEEE dd. MMMM y–EEEE dd. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'dd. MMMM–dd. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'dd. MMMM y–dd. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy–dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_BE = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' H \'h\' mm \'min\' ss \'s\' zzzz',
    '_': 'H \'h\' mm \'min\' ss \'s\' zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' H \'h\' mm \'min\' ss \'s\' z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' H \'h\' mm \'min\' ss \'s\' zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/MM/yy \'à\' HH:mm – HH:mm',
    '_': 'd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_BF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_BI = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_BJ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_BL = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CD = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CG = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CH = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y \'à\' HH.mm:ss \'h\' zzzz',
    '_': 'HH.mm:ss \'h\' zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y \'à\' HH.mm:ss \'h\' z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'à\' HH.mm:ss \'h\' zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy \'à\' HH:mm – HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CI = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_CM = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_DJ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_DZ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_FR = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_GA = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_GF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_GN = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_GP = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_GQ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_HT = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_KM = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_LU = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MA = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MC = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MG = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_ML = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MQ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MR = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_MU = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_NC = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_NE = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_PF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_PM = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_RE = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_RW = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_SC = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_SN = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_SY = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_TD = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_TG = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_TN = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_VU = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y \'à\' h:mm a – h:mm a',
    'hm': 'dd/MM/y \'à\' h:mm – h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_WF = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fr_YT = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y \'à\' HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'à\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'à\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'à\' HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y \'à\' HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fur = {
  FULL_DATE: {
    'Mdy': 'EEEE dd/MM/y – EEEE dd/MM/y',
    '_': 'EEEE d \'di\' MMMM \'dal\' y'
  },
  LONG_DATE: {
    'M': 'dd/MM/y – d/MM',
    'd': 'd – d/MM/y',
    'y': 'dd/MM/y – dd/MM/y',
    '_': 'd \'di\' MMMM \'dal\' y'
  },
  MEDIUM_DATE: {
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d \'di\' MMMM \'dal\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'di\' MMMM \'dal\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fur_IT = {
  FULL_DATE: {
    'Mdy': 'EEEE dd/MM/y – EEEE dd/MM/y',
    '_': 'EEEE d \'di\' MMMM \'dal\' y'
  },
  LONG_DATE: {
    'M': 'dd/MM/y – d/MM',
    'd': 'd – d/MM/y',
    'y': 'dd/MM/y – dd/MM/y',
    '_': 'd \'di\' MMMM \'dal\' y'
  },
  MEDIUM_DATE: {
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d \'di\' MMMM \'dal\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'di\' MMMM \'dal\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fy = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_fy_NL = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ga_IE = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gd = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d\'mh\' MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd\'mh\' MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d\'mh\' MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd\'mh\' MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gd_GB = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d\'mh\' MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd\'mh\' MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d\'mh\' MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd\'mh\' MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gl_ES = {
  FULL_DATE: {
    'M': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'd': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd MMM y – d MMM y',
    '_': 'd \'de\' MMM \'de\' y'
  },
  SHORT_DATE: {
    'Md': 'd/M/yy – d/M/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'HH:mm:ss zzzz, d/M/y',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'HH:mm:ss z, d/M/y',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'HH:mm:ss, d/M/y',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'HH:mm, d/M/y',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'HH:mm:ss zzzz \'do\' EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z \'do\' d \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATETIME: {
    '_': 'HH:mm:ss, d \'de\' MMM \'de\' y'
  },
  SHORT_DATETIME: {
    'ahm': 'HH:mm–HH:mm, dd/MM/yy',
    '_': 'HH:mm, dd/MM/yy'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gsw_CH = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gsw_FR = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gsw_LI = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'dd.MM.y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gu_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a zzzz',
    '_': 'hh:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a z',
    '_': 'hh:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a',
    '_': 'hh:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y hh:mm a',
    'a': 'h:mm a – h:mm a',
    'h': 'h:mm – h:mm a',
    'm': 'h:mm–h:mm a',
    '_': 'hh:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y hh:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y hh:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y hh:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'h': 'd/M/yy h:mm – h:mm a',
    'm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy hh:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_guz = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_guz_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gv = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_gv_IM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ha = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Md': 'dd/MM/yy – dd/MM/yy',
    'y': 'yy-MM-dd – yy-MM-dd',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ha_GH = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Md': 'dd/MM/yy – dd/MM/yy',
    'y': 'yy-MM-dd – yy-MM-dd',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ha_NE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Md': 'dd/MM/yy – dd/MM/yy',
    'y': 'yy-MM-dd – yy-MM-dd',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ha_NG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Md': 'dd/MM/yy – dd/MM/yy',
    'y': 'yy-MM-dd – yy-MM-dd',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_haw_US = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_he_IL = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE, d בMMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d בMMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd בMMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d בMMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd בMMM y'
  },
  SHORT_DATE: {
    'd': 'dd.M.y – dd.M.y',
    '_': 'd.M.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d בMMMM y בשעה H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd בMMMM y בשעה H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd בMMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.y, H:mm–H:mm',
    '_': 'd.M.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hi_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y को h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y को h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm–h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hr_BA = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    'y': 'EEEE, dd. MMMM y. – EEEE, dd. MMMM y.',
    '_': 'EEEE, d. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd. – dd. MMMM y.',
    'y': 'dd. MMMM y. – dd. MMMM y.',
    '_': 'd. MMMM y.'
  },
  MEDIUM_DATE: {
    'M': 'dd. MMM – dd. MMM y.',
    'd': 'dd. – dd. MMM y.',
    'y': 'dd. MMM y. – dd. MMM y.',
    '_': 'd. MMM y.'
  },
  SHORT_DATE: {
    'Mdy': 'dd. MM. yy. – dd. MM. yy.',
    '_': 'd. M. yy.'
  },
  FULL_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss (zzzz)',
    '_': 'HH:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss (z)',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd. MM. y. HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y. \'u\' HH:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y. \'u\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd. M. yy. HH:mm – HH:mm',
    '_': 'd. M. yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hr_HR = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    'y': 'EEEE, dd. MMMM y. – EEEE, dd. MMMM y.',
    '_': 'EEEE, d. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd. – dd. MMMM y.',
    'y': 'dd. MMMM y. – dd. MMMM y.',
    '_': 'd. MMMM y.'
  },
  MEDIUM_DATE: {
    'M': 'dd. MMM – dd. MMM y.',
    'd': 'dd. – dd. MMM y.',
    'y': 'dd. MMM y. – dd. MMM y.',
    '_': 'd. MMM y.'
  },
  SHORT_DATE: {
    '_': 'dd. MM. y.'
  },
  FULL_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss (zzzz)',
    '_': 'HH:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss (z)',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd. MM. y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd. MM. y. HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y. \'u\' HH:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y. \'u\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd. MM. y. HH:mm – HH:mm',
    '_': 'dd. MM. y. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hsb = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd.M.y'
  },
  SHORT_DATE: {
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y H:mm \'hodź\'.',
    'ahm': 'H:mm – H:mm \'hodź\'.',
    '_': 'H:mm \'hodź\'.'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.M.y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy H:mm – H:mm \'hodź\'.',
    '_': 'd.M.yy H:mm \'hodź\'.'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hsb_DE = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd.M.y'
  },
  SHORT_DATE: {
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y H:mm \'hodź\'.',
    'ahm': 'H:mm – H:mm \'hodź\'.',
    '_': 'H:mm \'hodź\'.'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd.M.y H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy H:mm – H:mm \'hodź\'.',
    '_': 'd.M.yy H:mm \'hodź\'.'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hu_HU = {
  FULL_DATE: {
    'M': 'y. MMMM d., EEEE – MMMM d., EEEE',
    'd': 'y. MMMM d., EEEE – d., EEEE',
    '_': 'y. MMMM d., EEEE'
  },
  LONG_DATE: {
    'M': 'y. MMMM d. – MMMM d.',
    'd': 'y. MMMM d–d.',
    '_': 'y. MMMM d.'
  },
  MEDIUM_DATE: {
    'M': 'y. MMM d. – MMM d.',
    'd': 'y. MMM d–d.',
    '_': 'y. MMM d.'
  },
  SHORT_DATE: {
    'M': 'y. MM. dd. – MM. dd.',
    'd': 'y. MM. dd–dd.',
    '_': 'y. MM. dd.'
  },
  FULL_TIME: {
    'Mdy': 'y. MM. dd. H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y. MM. dd. H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y. MM. dd. H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y. MM. dd. H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'y. MMMM d., EEEE H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y. MMMM d. H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y. MMM d. H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y. MM. dd. H:mm–H:mm',
    '_': 'y. MM. dd. H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_hy_AM = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y թ.',
    'y': 'EEEE, d MMMM, y – EEEE, d MMMM, y թ.',
    '_': 'y թ. MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM, y թ.',
    'd': 'dd–dd MMMM, y թ.',
    'y': 'dd MMMM, y թ․ – dd MMMM, y թ.',
    '_': 'dd MMMM, y թ.'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM, y թ.',
    'd': 'dd–dd MMM, y թ.',
    'y': 'dd MMM, y թ․ – dd MMM, y թ.',
    '_': 'dd MMM, y թ.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y թ. MMMM d, EEEE, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM, y թ., HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM, y թ., HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, H:mm–H:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_id_ID = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH.mm.ss zzzz',
    '_': 'HH.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH.mm.ss z',
    '_': 'HH.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH.mm.ss',
    '_': 'HH.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH.mm',
    'ahm': 'HH.mm–HH.mm',
    '_': 'HH.mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y HH.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH.mm–HH.mm',
    '_': 'dd/MM/yy HH.mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ig = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ig_NG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ii = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ii_CN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_is_IS = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd.–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    '_': 'd.M.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.y, HH:mm–HH:mm',
    '_': 'd.M.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_it_CH = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_it_IT = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_it_SM = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_it_VA = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM – dd MMM y',
    'd': 'dd–dd MMM y',
    'y': 'dd MMM y – dd MMM y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ja_JP = {
  FULL_DATE: {
    'Mdy': 'y/MM/dd(EEEE)～y/MM/dd(EEEE)',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/MM/dd～y/MM/dd',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    '_': 'y/MM/dd'
  },
  SHORT_DATE: {
    '_': 'y/MM/dd'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d H時mm分ss秒 zzzz',
    '_': 'H時mm分ss秒 zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d H時mm分ss秒 z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d H:mm',
    'ahm': 'H時mm分～H時mm分',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE H時mm分ss秒 zzzz'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y/MM/dd H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y/MM/dd H時mm分～H時mm分',
    '_': 'y/MM/dd H:mm'
  },
  FALLBACK: '{0}～{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_jgo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'M.d.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M.d.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M.d.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M.d.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_jgo_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'M.d.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M.d.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M.d.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M.d.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_jmc = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_jmc_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ka_GE = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM. – EEEE, d MMMM. y',
    'y': 'EEEE, d MMMM. y – EEEE, d MMMM. y',
    '_': 'EEEE, dd MMMM, y'
  },
  LONG_DATE: {
    'M': 'dd MMMM. – dd MMMM. y',
    'd': 'd–d MMMM, y',
    'y': 'dd MMMM. y – d MMMM. y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'dd MMM. – dd MMM. y',
    'd': 'd–d MMM, y',
    'y': 'dd MMM. y – d MMM. y',
    '_': 'd MMM. y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM, y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM. y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kab = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y h:mm a – h:mm a',
    'hm': 'd/M/y h:mm–h:mm a',
    '_': 'd/M/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kab_DZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y h:mm a – h:mm a',
    'hm': 'd/M/y h:mm–h:mm a',
    '_': 'd/M/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kam = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kam_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kde = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kde_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kea = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d \'di\' MMMM \'di\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd \'di\' MMMM \'di\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'di\' MMMM \'di\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'di\' MMMM \'di\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kea_CV = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d \'di\' MMMM \'di\' y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd \'di\' MMMM \'di\' y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'di\' MMMM \'di\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'di\' MMMM \'di\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_khq = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_khq_ML = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ki = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ki_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kk_KZ = {
  FULL_DATE: {
    'M': 'y \'ж\'. d MMMM, EEEE – d MMMM, EEEE',
    'dy': 'y \'ж\'. d MMMM, EEEE – y \'ж\'. d MMMM, EEEE',
    '_': 'y \'ж\'. d MMMM, EEEE'
  },
  LONG_DATE: {
    'M': 'y \'ж\'. d MMMM – d MMMM',
    'd': 'y \'ж\'. d–d MMMM',
    'y': 'y \'ж\'. d MMMM – y \'ж\'. d MMMM',
    '_': 'y \'ж\'. d MMMM'
  },
  MEDIUM_DATE: {
    'M': 'y \'ж\'. d MMM – d MMM',
    'd': 'y \'ж\'. d–d MMM',
    'y': 'y \'ж\'. d MMM – y \'ж\'. d MMM',
    '_': 'y \'ж\'. dd MMM'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy – dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y \'ж\'. d MMMM, EEEE, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y \'ж\'. d MMMM, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y \'ж\'. dd MMM, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kkj = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE dd MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE dd MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM y HH:mm–HH:mm',
    '_': 'dd/MM y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kkj_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE dd MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM y'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE dd MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM y HH:mm–HH:mm',
    '_': 'dd/MM y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kl = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kl_GL = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kln = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kln_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_km_KH = {
  FULL_DATE: {
    'Md': 'EEEE dd MMMM y – EEEE dd MMMM y',
    'y': 'EEEE dd-MM-y – EEEE dd MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y នៅ​ម៉ោង h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y នៅ​ម៉ោង h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm – h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kn_IN = {
  FULL_DATE: {
    'M': 'EEEE, MMMM d – EEEE, MMMM d, y',
    'd': 'EEEE, MMMM d – EEEE, MMMM d,y',
    'y': 'd MMMM, y EEEE – d MMMM, y EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'MMMM d–d,y',
    'y': 'd, MMMM, y – d, MMMM, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'MMM d–d,y',
    'y': 'd, MMM, y – d, MMM, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/yy – M/d/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a zzzz',
    '_': 'hh:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a z',
    '_': 'hh:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y hh:mm:ss a',
    '_': 'hh:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y hh:mm a',
    'a': 'h:mm a – h:mm a',
    'h': 'h:mm–h:mm a',
    'm': 'h:mm – h:mm a',
    '_': 'hh:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y hh:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y hh:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y hh:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'h': 'd/M/yy h:mm–h:mm a',
    'm': 'd/M/yy h:mm – h:mm a',
    '_': 'd/M/yy hh:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ko_KP = {
  FULL_DATE: {
    'Mdy': 'y. M. d. (EEEE) ~ y. M. d. (EEEE)',
    '_': 'y년 M월 d일 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y. M. d. ~ y. M. d.',
    '_': 'y년 M월 d일'
  },
  MEDIUM_DATE: {
    '_': 'y. M. d.'
  },
  SHORT_DATE: {
    '_': 'yy. M. d.'
  },
  FULL_TIME: {
    'Mdy': 'y. M. d. a h시 m분 s초 zzzz',
    '_': 'a h시 m분 s초 zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y. M. d. a h시 m분 s초 z',
    '_': 'a h시 m분 s초 z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y. M. d. a h:mm:ss',
    '_': 'a h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y. M. d. a h:mm',
    'hm': 'a h:mm~h:mm',
    '_': 'a h:mm'
  },
  FULL_DATETIME: {
    '_': 'y년 M월 d일 EEEE a h시 m분 s초 zzzz'
  },
  LONG_DATETIME: {
    '_': 'y년 M월 d일 a h시 m분 s초 z'
  },
  MEDIUM_DATETIME: {
    '_': 'y. M. d. a h:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'yy. M. d. a h:mm ~ a h:mm',
    'hm': 'yy. M. d. a h:mm~h:mm',
    '_': 'yy. M. d. a h:mm'
  },
  FALLBACK: '{0} ~ {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ko_KR = {
  FULL_DATE: {
    'Mdy': 'y. M. d. (EEEE) ~ y. M. d. (EEEE)',
    '_': 'y년 M월 d일 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y. M. d. ~ y. M. d.',
    '_': 'y년 M월 d일'
  },
  MEDIUM_DATE: {
    '_': 'y. M. d.'
  },
  SHORT_DATE: {
    '_': 'yy. M. d.'
  },
  FULL_TIME: {
    'Mdy': 'y. M. d. a h시 m분 s초 zzzz',
    '_': 'a h시 m분 s초 zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y. M. d. a h시 m분 s초 z',
    '_': 'a h시 m분 s초 z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y. M. d. a h:mm:ss',
    '_': 'a h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y. M. d. a h:mm',
    'hm': 'a h:mm~h:mm',
    '_': 'a h:mm'
  },
  FULL_DATETIME: {
    '_': 'y년 M월 d일 EEEE a h시 m분 s초 zzzz'
  },
  LONG_DATETIME: {
    '_': 'y년 M월 d일 a h시 m분 s초 z'
  },
  MEDIUM_DATETIME: {
    '_': 'y. M. d. a h:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'yy. M. d. a h:mm ~ a h:mm',
    'hm': 'yy. M. d. a h:mm~h:mm',
    '_': 'yy. M. d. a h:mm'
  },
  FALLBACK: '{0} ~ {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kok = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kok_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ks = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy h:mm a – h:mm a',
    'hm': 'M/d/yy h:mm–h:mm a',
    '_': 'M/d/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ks_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'M/d/yy h:mm a – h:mm a',
    'hm': 'M/d/yy h:mm–h:mm a',
    '_': 'M/d/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksb = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksb_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksf = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksf_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksh = {
  FULL_DATE: {
    'Mdy': 'EEEE y-MM-dd – EEEE y-MM-dd',
    '_': 'EEEE, \'dä\' d. MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'd.–d. MMMM y',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'd.–d. MMMM y',
    'y': 'y MMM d – y MMM d',
    '_': 'd. MMM. y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd. M. y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, \'dä\' d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM. y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'd. M. y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ksh_DE = {
  FULL_DATE: {
    'Mdy': 'EEEE y-MM-dd – EEEE y-MM-dd',
    '_': 'EEEE, \'dä\' d. MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'd.–d. MMMM y',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'd.–d. MMMM y',
    'y': 'y MMM d – y MMM d',
    '_': 'd. MMM. y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd. M. y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, \'dä\' d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM. y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'd. M. y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kw = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_kw_GB = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ky_KG = {
  FULL_DATE: {
    'M': 'y-\'ж\'., d-MMMM, EEEE – d-MMMM EEEE',
    'd': 'y-\'ж\'., d-MMMM, EEEE – d-MMMM, EEEE',
    'y': 'y-\'ж\'., d-MMMM, EEEE – y-\'ж\'., d-MMMM, EEEE',
    '_': 'y-\'ж\'., d-MMMM, EEEE'
  },
  LONG_DATE: {
    'M': 'd-MMMM – d-MMMM y-\'ж\'.',
    'd': 'd–d-MMMM y-\'ж\'.',
    'y': 'd-MMMM y-\'ж\'. - d-MMMM y-\'ж\'.',
    '_': 'y-\'ж\'., d-MMMM'
  },
  MEDIUM_DATE: {
    'M': 'd-MMM – d-MMM y-\'ж\'.',
    'd': 'd–d-MMM y-\'ж\'.',
    'y': 'd-MMM y-\'ж\'. - d-MMM y-\'ж\'.',
    '_': 'y-\'ж\'., d-MMM'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy – dd.MM.yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-dd-MM HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-dd-MM HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-dd-MM HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-dd-MM HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y-\'ж\'., d-MMMM, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y-\'ж\'., d-MMMM HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y-\'ж\'., d-MMM HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm–HH:mm',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lag = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lag_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lb = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y – d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy – dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lb_LU = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y – d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy – dd.MM.yy',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lg = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lg_UG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lkt = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lkt_US = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ln_AO = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ln_CD = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ln_CF = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ln_CG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lo_LA = {
  FULL_DATE: {
    '_': 'EEEE ທີ d MMMM G y'
  },
  LONG_DATE: {
    'M': 'd/MM/y – d/MM',
    'd': 'd/MM/y – d/MM/y',
    'y': 'dd/MM/y – dd/MM/y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd/MM/y – d/MM',
    'd': 'd/MM/y – d/MM/y',
    'y': 'dd/MM/y – dd/MM/y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, H ໂມງ m ນາທີ ss ວິນາທີ zzzz',
    '_': 'H ໂມງ m ນາທີ ss ວິນາທີ zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, H ໂມງ m ນາທີ ss ວິນາທີ z',
    '_': 'H ໂມງ m ນາທີ ss ວິນາທີ z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, H:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE ທີ d MMMM G y, H ໂມງ m ນາທີ ss ວິນາທີ zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y, H ໂມງ m ນາທີ ss ວິນາທີ z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y, HH:mm–HH:mm',
    '_': 'd/M/y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lrc = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lrc_IQ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd h:mm a – h:mm a',
    'hm': 'y-MM-dd h:mm–h:mm a',
    '_': 'y-MM-dd h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lrc_IR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lt_LT = {
  FULL_DATE: {
    'M': 'y MMMM d, EEEE. – MMMM d, EEEE.',
    'd': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE. – y MMMM d, EEEE.',
    '_': 'y \'m\'. MMMM d \'d\'., EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'y \'m\'. MMMM d \'d\'.'
  },
  MEDIUM_DATE: {
    '_': 'y-MM-dd'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y \'m\'. MMMM d \'d\'., EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y \'m\'. MMMM d \'d\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y-MM-dd HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lu = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lu_CD = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_luo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_luo_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_luy = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_luy_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_lv_LV = {
  FULL_DATE: {
    'Md': 'EEEE, y. \'gada\' d. MMMM – EEEE, y. \'gada\' d. MMMM',
    'y': 'EEEE, y. \'gada\' d. MMMM – EEEE, y. \'gada\' d. MMMM',
    '_': 'EEEE, y. \'gada\' d. MMMM'
  },
  LONG_DATE: {
    'M': 'y. \'gada\' d. MMMM – d. MMMM',
    'd': 'y. \'gada\' d.–d. MMMM',
    'y': 'y. \'gada\' d. MMMM – y. \'gada\' d. MMMM',
    '_': 'y. \'gada\' d. MMMM'
  },
  MEDIUM_DATE: {
    'M': 'y. \'gada\' d. MMM – d. MMM',
    'd': 'y. \'gada\' d.–d. MMM',
    'y': 'y. \'gada\' d. MMM – y. \'gada\' d. MMM',
    '_': 'y. \'gada\' d. MMM'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.yy.–dd.MM.yy.',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'y.MM.d. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y.MM.d. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y.MM.d. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y.MM.d. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y. \'gada\' d. MMMM HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y. \'gada\' d. MMMM HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y. \'gada\' d. MMM HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd.MM.yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mas = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mas_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mas_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mer = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mer_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mfe = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mfe_MU = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mg = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mg_MG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mgh = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mgh_MZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mgo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mgo_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, y MMMM dd'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y MMMM dd HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mk_MK = {
  FULL_DATE: {
    'M': 'EEEE, dd MMMM – EEEE, dd MMMM y',
    'd': 'EEEE, dd – EEEE, dd MMMM y',
    'y': 'EEEE, dd MMMM y – EEEE, dd MMMM y',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'dd MMMM – dd MMMM y',
    'd': 'dd–dd MMMM y',
    'y': 'dd MMMM y – dd MMMM y',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd.M.y – dd.M.y',
    '_': 'dd.M.y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.M.yy – dd.M.yy',
    '_': 'dd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.M.y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.M.yy HH:mm–HH:mm',
    '_': 'dd.M.yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ml_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y, MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d – d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'y, MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d – d',
    'y': 'y MMM d – y MMM d',
    '_': 'y, MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y, MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y, MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y, MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mn_MN = {
  FULL_DATE: {
    'Mdy': 'EEEE, y/MM/dd – EEEE, y/MM/dd',
    '_': 'EEEE, y \'оны\' MM \'сарын\' d'
  },
  LONG_DATE: {
    'M': 'y/MM/dd – MM/dd',
    'd': 'y/MM/d–d',
    'y': 'y/MM/dd – y/MM/dd',
    '_': 'y\'оны\' MMMM\'сарын\' d\'өдөр\''
  },
  MEDIUM_DATE: {
    'M': 'y/MM/dd – MM/dd',
    'd': 'y/MM/d–d',
    'y': 'y/MM/dd – y/MM/dd',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'M': 'y/MM/dd –MM/dd',
    'd': 'y/MM/dd–dd',
    'y': 'y/MM/dd – y/MM/dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, y \'оны\' MM \'сарын\' d HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y\'оны\' MMMM\'сарын\' d\'өдөр\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm – HH:mm',
    '_': 'y-MM-dd, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mr_IN = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'd': 'EEEE, d MMMM y – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y रोजी h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y रोजी h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm – h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ms_BN = {
  FULL_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dd MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/yy h:mm a – h:mm a',
    'hm': 'd/MM/yy h:mm–h:mm a',
    '_': 'd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ms_MY = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/yy h:mm a – h:mm a',
    'hm': 'd/MM/yy h:mm–h:mm a',
    '_': 'd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ms_SG = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/yy h:mm a – h:mm a',
    'hm': 'd/MM/yy h:mm–h:mm a',
    '_': 'd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mt_MT = {
  FULL_DATE: {
    'M': 'EEEE, d \'ta\'’ MMMM – EEEE, d \'ta\'’ MMMM y',
    'd': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d \'ta\'’ MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'd – d MMMM y',
    'y': 'd MMMM, y – d MMMM, y',
    '_': 'd \'ta\'’ MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'd – d MMM y',
    'y': 'd MMM, y – d MMM, y',
    '_': 'dd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'ta\'’ MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'ta\'’ MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mua = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mua_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_my_MM = {
  FULL_DATE: {
    'Md': 'y MMMM d EEEEနေ့ – MMMM d EEEEနေ့',
    'y': 'y MMMM d EEEEနေ့ – y MMMM d EEEEနေ့',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'My': 'y MMMM d – y MMMM d',
    'd': 'y MMMM d – d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'My': 'y MMM d – y MMM d',
    'd': 'y MMM d – d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y zzzz HH:mm:ss',
    '_': 'zzzz HH:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y z HH:mm:ss',
    '_': 'z HH:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y zzzz HH:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y z HH:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm – HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mzn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_mzn_IR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_naq = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_naq_NA = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nb_NO = {
  FULL_DATE: {
    'M': 'EEEE d. MMMM–EEEE d. MMMM y',
    'd': 'EEEE d.–EEEE d. MMMM y',
    '_': 'EEEE d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM–d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM–d. MMM y',
    'd': 'd.–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nb_SJ = {
  FULL_DATE: {
    'M': 'EEEE d. MMMM–EEEE d. MMMM y',
    'd': 'EEEE d.–EEEE d. MMMM y',
    '_': 'EEEE d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM–d. MMMM y',
    'd': 'd.–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM–d. MMM y',
    'd': 'd.–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nd = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nd_ZW = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nds = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nds_DE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nds_NL = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ne_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd, h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd, h:mm a – h:mm a',
    'hm': 'y-MM-dd, h:mm–h:mm a',
    '_': 'y-MM-dd, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ne_NP = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd, HH:mm–HH:mm',
    '_': 'y-MM-dd, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_AW = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_BE = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/MM/yy – d/MM/yy',
    '_': 'd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/MM/yy HH:mm–HH:mm',
    '_': 'd/MM/yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_BQ = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_CW = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_NL = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_SR = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nl_SX = {
  FULL_DATE: {
    'M': 'EEEE d MMMM – EEEE d MMMM y',
    'd': 'EEEE d – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd-MM-yy – dd-MM-yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'om\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'om\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nmg = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nmg_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nn = {
  FULL_DATE: {
    'M': 'EEEE d. MMMM–EEEE d. MMMM y',
    'd': 'EEEE d.–EEEE d. MMMM y',
    'y': 'EEEE d. MMMM y–EEEE d. MMMM y',
    '_': 'EEEE d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM–d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM–d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, \'kl\'. HH:mm:ss zzzz',
    '_': '\'kl\'. HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, \'kl\'. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nn_NO = {
  FULL_DATE: {
    'M': 'EEEE d. MMMM–EEEE d. MMMM y',
    'd': 'EEEE d.–EEEE d. MMMM y',
    'y': 'EEEE d. MMMM y–EEEE d. MMMM y',
    '_': 'EEEE d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM–d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y–d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM–d. MMM y',
    'd': 'd.–d. MMM y',
    'y': 'd. MMM y–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, \'kl\'. HH:mm:ss zzzz',
    '_': '\'kl\'. HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, \'kl\'. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d. MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y \'kl\'. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nnh = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE , \'lyɛ\'̌ʼ d \'na\' MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': '\'lyɛ\'̌ʼ d \'na\' MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE , \'lyɛ\'̌ʼ d \'na\' MMMM, y,HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': '\'lyɛ\'̌ʼ d \'na\' MMMM, y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nnh_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE , \'lyɛ\'̌ʼ d \'na\' MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': '\'lyɛ\'̌ʼ d \'na\' MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE , \'lyɛ\'̌ʼ d \'na\' MMMM, y,HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': '\'lyɛ\'̌ʼ d \'na\' MMMM, y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nus = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y zzzz h:mm:ss a',
    '_': 'zzzz h:mm:ss a'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y z h:mm:ss a',
    '_': 'z h:mm:ss a'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y zzzz h:mm:ss a'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y z h:mm:ss a'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/y h:mm a – h:mm a',
    'hm': 'd/MM/y h:mm–h:mm a',
    '_': 'd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nus_SS = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y zzzz h:mm:ss a',
    '_': 'zzzz h:mm:ss a'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y z h:mm:ss a',
    '_': 'z h:mm:ss a'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y zzzz h:mm:ss a'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y z h:mm:ss a'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/MM/y h:mm a – h:mm a',
    'hm': 'd/MM/y h:mm–h:mm a',
    '_': 'd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nyn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_nyn_UG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_om = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_om_ET = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_om_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_or_IN = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'd-M-yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd-M-yy h:mm a – h:mm a',
    'hm': 'd-M-yy h:mm–h:mm a',
    '_': 'd-M-yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_os = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y \'аз\''
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y \'аз\''
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd MMM y \'аз\''
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y \'аз\', HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y \'аз\', HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y \'аз\', HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_os_GE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y \'аз\''
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y \'аз\''
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd MMM y \'аз\''
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y \'аз\', HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y \'аз\', HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y \'аз\', HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_os_RU = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y \'аз\''
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM, y \'аз\''
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd MMM y \'аз\''
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y \'аз\', HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y \'аз\', HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd MMM y \'аз\', HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pa_Arab = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pa_Arab_PK = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, dd MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pa_Guru = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm–h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pa_Guru_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm–h:mm a',
    '_': 'd/M/yy, h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pl_PL = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'M': 'dd.MM–dd.MM.y',
    'd': 'dd–dd.MM.y',
    'y': 'dd.MM.y–dd.MM.y',
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ps = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE د y د MMMM d'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'د y د MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd H:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE د y د MMMM d H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'د y د MMMM d H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y/M/d H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ps_AF = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE د y د MMMM d'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'د y د MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd H:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE د y د MMMM d H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'د y د MMMM d H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y/M/d H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_AO = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_CH = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_CV = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_GQ = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_GW = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_LU = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_MO = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy, h:mm a – h:mm a',
    'hm': 'dd/MM/yy, h:mm – h:mm a',
    '_': 'dd/MM/yy, h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_MZ = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_ST = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_pt_TL = {
  FULL_DATE: {
    'Md': 'EEEE, d \'de\' MMMM – EEEE, d \'de\' MMMM \'de\' y',
    'y': 'EEEE, d \'de\' MMMM \'de\' y – EEEE, d \'de\' MMMM \'de\' y',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'd \'de\' MMMM – d \'de\' MMMM \'de\' y',
    'd': 'd–d \'de\' MMMM \'de\' y',
    'y': 'd \'de\' MMMM \'de\' y – d \'de\' MMMM \'de\' y',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/yy – dd/MM/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y \'às\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y \'às\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd/MM/y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm – HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_qu = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z d MMMM y'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_qu_BO = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z d MMMM y'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_qu_EC = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z d MMMM y'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_qu_PE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd-MM-y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd-MM-y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z d MMMM y'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rm = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, \'ils\' d \'da\' MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd \'da\' MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd-MM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, \'ils\' d \'da\' MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'da\' MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MM-y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rm_CH = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, \'ils\' d \'da\' MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd \'da\' MMMM y'
  },
  MEDIUM_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd-MM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, \'ils\' d \'da\' MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'da\' MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MM-y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy HH:mm–HH:mm',
    '_': 'dd-MM-yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rn_BI = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ro_MD = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ro_RO = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y, HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y, HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rof = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rof_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_BY = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y \'г\'. – ccc, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, H:mm–H:mm',
    '_': 'dd.MM.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_KG = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y \'г\'. – ccc, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, H:mm–H:mm',
    '_': 'dd.MM.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_KZ = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y \'г\'. – ccc, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, H:mm–H:mm',
    '_': 'dd.MM.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_MD = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y \'г\'. – ccc, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, H:mm–H:mm',
    '_': 'dd.MM.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_RU = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y \'г\'. – ccc, d MMMM y \'г\'.',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, H:mm',
    'ahm': 'H:mm–H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, H:mm–H:mm',
    '_': 'dd.MM.y, H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ru_UA = {
  FULL_DATE: {
    'M': 'ccc, d MMMM – ccc, d MMMM y \'г\'.',
    'd': 'ccc, d – ccc, d MMMM y \'г\'.',
    'y': 'ccc, d MMMM y – ccc, d MMMM y',
    '_': 'EEEE, d MMMM y \'г\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y \'г\'.',
    'd': 'd–d MMMM y \'г\'.',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y \'г\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y \'г\'.',
    'd': 'd–d MMM y \'г\'.',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y \'г\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'г\'., HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'г\'., HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'г\'., HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.y, HH:mm–HH:mm',
    '_': 'dd.MM.y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rw = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rw_RW = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rwk = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_rwk_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sah = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y \'сыл\' MMMM d \'күнэ\', EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'y, MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y, MMM d'
  },
  SHORT_DATE: {
    'My': 'yy-MM-dd – yy-MM-dd',
    'd': 'dd.MM.yy – dd.MM.yy',
    '_': 'yy/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y \'сыл\' MMMM d \'күнэ\', EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y, MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y, MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'yy/M/d HH:mm–HH:mm',
    '_': 'yy/M/d HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sah_RU = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'y \'сыл\' MMMM d \'күнэ\', EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'y, MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'y, MMM d'
  },
  SHORT_DATE: {
    'My': 'yy-MM-dd – yy-MM-dd',
    'd': 'dd.MM.yy – dd.MM.yy',
    '_': 'yy/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y \'сыл\' MMMM d \'күнэ\', EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y, MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y, MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'yy/M/d HH:mm–HH:mm',
    '_': 'yy/M/d HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_saq = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_saq_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sbp = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sbp_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_se = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_se_FI = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_se_NO = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_se_SE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_seh = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd \'de\' MMM \'de\' y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd \'de\' MMM \'de\' y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_seh_MZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d \'de\' MMMM \'de\' y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd \'de\' MMMM \'de\' y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd \'de\' MMM \'de\' y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d \'de\' MMMM \'de\' y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd \'de\' MMMM \'de\' y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd \'de\' MMM \'de\' y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ses = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ses_ML = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sg = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sg_CF = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_shi = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_shi_Latn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_shi_Latn_MA = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_shi_Tfng = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_shi_Tfng_MA = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_si_LK = {
  FULL_DATE: {
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d – d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d – d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    'Mdy': 'y-M-d – y-M-d',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH.mm.ss zzzz',
    '_': 'HH.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH.mm.ss z',
    '_': 'HH.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH.mm.ss',
    '_': 'HH.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH.mm',
    'ahm': 'HH.mm–HH.mm',
    '_': 'HH.mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH.mm–HH.mm',
    '_': 'y-MM-dd HH.mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sk_SK = {
  FULL_DATE: {
    'M': 'EEEE d. M. – EEEE d. M. y',
    'd': 'EEEE d. – EEEE d. M. y',
    'y': 'EEEE d. M. y – EEEE d. M. y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. M. – d. M. y',
    'd': 'd. – d. M. y',
    'y': 'd. M. y – d. M. y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    '_': 'd. M. y'
  },
  SHORT_DATE: {
    '_': 'd. M. y'
  },
  FULL_TIME: {
    'Mdy': 'd. M. y, H:mm:ss zzzz',
    '_': 'H:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd. M. y, H:mm:ss z',
    '_': 'H:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd. M. y, H:mm:ss',
    '_': 'H:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd. M. y, H:mm',
    '_': 'H:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y, H:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y, H:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. M. y, H:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd. M. y, H:mm – H:mm',
    '_': 'd. M. y H:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sl_SI = {
  FULL_DATE: {
    'Md': 'EEEE, d. MMMM–EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y–EEEE, d. MMMM y',
    '_': 'EEEE, dd. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM–d. MMMM y',
    'd': 'd.–d. MMMM y',
    'y': 'd. MMMM y–d. MMMM y',
    '_': 'dd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM–d. MMM y',
    'd': 'd.–d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'M': 'd. M.–d. M. yy',
    'dy': 'd. M. yy–d. M. yy',
    '_': 'd. MM. yy'
  },
  FULL_TIME: {
    'Mdy': 'd. M. y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd. M. y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd. M. y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd. M. y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd. MM. yy HH:mm–HH:mm',
    '_': 'd. MM. yy HH:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_smn = {
  FULL_DATE: {
    '_': 'cccc, MMMM d. y'
  },
  LONG_DATE: {
    'M': 'MMMM d. – MMMM d. y',
    'd': 'MMMM d.–d. y',
    'y': 'MMMM d. y – MMMM d. y',
    '_': 'MMMM d. y'
  },
  MEDIUM_DATE: {
    'M': 'MMMM d. – MMMM d. y',
    'd': 'MMMM d.–d. y',
    'y': 'MMMM d. y – MMMM d. y',
    '_': 'MMM d. y'
  },
  SHORT_DATE: {
    'M': 'd.M.–d.M.y',
    'd': 'd. – d.M.y',
    '_': 'd.M.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss zzzz',
    '_': 'H.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss z',
    '_': 'H.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss',
    '_': 'H.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm',
    '_': 'H.mm'
  },
  FULL_DATETIME: {
    '_': 'cccc, MMMM d. y \'tme\' H.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d. y \'tme\' H.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d. y \'tme\' H.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.y \'tme\' H.mm–H.mm',
    '_': 'd.M.y H.mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_smn_FI = {
  FULL_DATE: {
    '_': 'cccc, MMMM d. y'
  },
  LONG_DATE: {
    'M': 'MMMM d. – MMMM d. y',
    'd': 'MMMM d.–d. y',
    'y': 'MMMM d. y – MMMM d. y',
    '_': 'MMMM d. y'
  },
  MEDIUM_DATE: {
    'M': 'MMMM d. – MMMM d. y',
    'd': 'MMMM d.–d. y',
    'y': 'MMMM d. y – MMMM d. y',
    '_': 'MMM d. y'
  },
  SHORT_DATE: {
    'M': 'd.M.–d.M.y',
    'd': 'd. – d.M.y',
    '_': 'd.M.y'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss zzzz',
    '_': 'H.mm.ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss z',
    '_': 'H.mm.ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm.ss',
    '_': 'H.mm.ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y \'tme\' H.mm',
    '_': 'H.mm'
  },
  FULL_DATETIME: {
    '_': 'cccc, MMMM d. y \'tme\' H.mm.ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d. y \'tme\' H.mm.ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d. y \'tme\' H.mm.ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.y \'tme\' H.mm–H.mm',
    '_': 'd.M.y H.mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sn_ZW = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_so = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM dd, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM dd, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_so_DJ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM dd, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM dd, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_so_ET = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM dd, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM dd, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_so_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM dd, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM dd, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_so_SO = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, MMMM dd, y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM dd, y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sq_AL = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy – d.M.yy',
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, h:mm:ss a, zzzz',
    '_': 'h:mm:ss a, zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, h:mm:ss a, z',
    '_': 'h:mm:ss a, z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, h:mm a',
    'a': 'h:mm a – h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'në\' h:mm:ss a, zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'në\' h:mm:ss a, z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd.M.yy, h:mm a – h:mm a',
    'hm': 'd.M.yy, h:mm – h:mm a',
    '_': 'd.M.yy, h:mm a'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sq_MK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy – d.M.yy',
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'në\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'në\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy, HH:mm – HH:mm',
    '_': 'd.M.yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sq_XK = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd – d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd – d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd.M.yy – d.M.yy',
    '_': 'd.M.yy'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y, HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'në\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'në\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy, HH:mm – HH:mm',
    '_': 'd.M.yy, HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Cyrl = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Cyrl_BA = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Cyrl_ME = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Cyrl_RS = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Cyrl_XK = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Latn_BA = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Latn_ME = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Latn_RS = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sr_Latn_XK = {
  FULL_DATE: {
    'M': 'EEEE, dd. MMMM – EEEE, dd. MMMM y.',
    'd': 'EEEE, dd. – EEEE, dd. MMMM y.',
    '_': 'EEEE, dd. MMMM y.'
  },
  LONG_DATE: {
    'M': 'dd. MMMM – dd. MMMM y.',
    'd': 'dd.–dd. MMMM y.',
    '_': 'dd. MMMM y.'
  },
  MEDIUM_DATE: {
    'Mdy': 'd.M.y. – d.M.y.',
    '_': 'dd.MM.y.'
  },
  SHORT_DATE: {
    '_': 'd.M.yy.'
  },
  FULL_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd.M.y. HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd.M.y. HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd. MMMM y. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd. MMMM y. HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd.MM.y. HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.M.yy. HH:mm–HH:mm',
    '_': 'd.M.yy. HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sv_AX = {
  FULL_DATE: {
    'Md': 'EEEE dd MMMM–EEEE dd MMMM y',
    'y': 'EEEE dd MMMM y–EEEE dd MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM–d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM–d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'M': 'y-MM-dd – MM-dd',
    'd': 'y-MM-dd – dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss zzzz',
    '_': '\'kl\'. HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sv_FI = {
  FULL_DATE: {
    'Md': 'EEEE dd MMMM–EEEE dd MMMM y',
    'y': 'EEEE dd MMMM y–EEEE dd MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM–d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM–d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'M': 'y-MM-dd – MM-dd',
    'd': 'y-MM-dd – dd',
    'y': 'y-MM-dd – y-MM-dd',
    '_': 'dd-MM-y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss zzzz',
    '_': '\'kl\'. HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd-MM-y HH:mm–HH:mm',
    '_': 'dd-MM-y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sv_SE = {
  FULL_DATE: {
    'Md': 'EEEE dd MMMM–EEEE dd MMMM y',
    'y': 'EEEE dd MMMM y–EEEE dd MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM–d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM–d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'M': 'y-MM-dd – MM-dd',
    'd': 'y-MM-dd – dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss zzzz',
    '_': '\'kl\'. HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd \'kl\'. HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y \'kl\'. HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sw_CD = {
  FULL_DATE: {
    'M': 'EEEE, MMMM d– EEEE, MMMM d y',
    'd': 'EEEE, MMMM d – EEEE, MMMM d y',
    'y': 'EEEE, MMMM d y – EEEE, MMMM d y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'Md': 'MMMM d – d, y',
    'y': 'MMMM d y – MMMM d y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'Md': 'MMM d – d, y',
    'y': 'MMM d y – MMM d y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sw_KE = {
  FULL_DATE: {
    'M': 'EEEE, MMMM d– EEEE, MMMM d y',
    'd': 'EEEE, MMMM d – EEEE, MMMM d y',
    'y': 'EEEE, MMMM d y – EEEE, MMMM d y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'Md': 'MMMM d – d, y',
    'y': 'MMMM d y – MMMM d y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'Md': 'MMM d – d, y',
    'y': 'MMM d y – MMM d y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'saa\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'saa\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y, HH:mm – HH:mm',
    '_': 'dd/MM/y, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sw_TZ = {
  FULL_DATE: {
    'M': 'EEEE, MMMM d– EEEE, MMMM d y',
    'd': 'EEEE, MMMM d – EEEE, MMMM d y',
    'y': 'EEEE, MMMM d y – EEEE, MMMM d y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'Md': 'MMMM d – d, y',
    'y': 'MMMM d y – MMMM d y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'Md': 'MMM d – d, y',
    'y': 'MMM d y – MMM d y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_sw_UG = {
  FULL_DATE: {
    'M': 'EEEE, MMMM d– EEEE, MMMM d y',
    'd': 'EEEE, MMMM d – EEEE, MMMM d y',
    'y': 'EEEE, MMMM d y – EEEE, MMMM d y',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'Md': 'MMMM d – d, y',
    'y': 'MMMM d y – MMMM d y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'Md': 'MMM d – d, y',
    'y': 'MMM d y – MMM d y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y – d/M/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm – HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ta_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss zzzz',
    '_': 'a h:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss z',
    '_': 'a h:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss',
    '_': 'a h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, a h:mm',
    'hm': 'a h:mm–h:mm',
    '_': 'a h:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y ’அன்று’ a h:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y ’அன்று’ a h:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y, a h:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, a h:mm – a h:mm',
    'hm': 'd/M/yy, a h:mm–h:mm',
    '_': 'd/M/yy, a h:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ta_LK = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y ’அன்று’ HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y ’அன்று’ HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy, HH:mm – HH:mm',
    '_': 'd/M/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ta_MY = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss zzzz',
    '_': 'a h:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss z',
    '_': 'a h:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss',
    '_': 'a h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, a h:mm',
    'hm': 'a h:mm–h:mm',
    '_': 'a h:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y ’அன்று’ a h:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y ’அன்று’ a h:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y, a h:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, a h:mm – a h:mm',
    'hm': 'd/M/yy, a h:mm–h:mm',
    '_': 'd/M/yy, a h:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ta_SG = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss zzzz',
    '_': 'a h:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss z',
    '_': 'a h:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, a h:mm:ss',
    '_': 'a h:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, a h:mm',
    'hm': 'a h:mm–h:mm',
    '_': 'a h:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM, y ’அன்று’ a h:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y ’அன்று’ a h:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y, a h:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, a h:mm – a h:mm',
    'hm': 'd/M/yy, a h:mm–h:mm',
    '_': 'd/M/yy, a h:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_te_IN = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'y': 'EEEE, d MMMM, y – EEEE, d MMMM, y',
    '_': 'd, MMMM y, EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd–d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd–d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy – d/M/yy',
    '_': 'dd-MM-yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'd, MMMM y, EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd-MM-yy h:mm a – h:mm a',
    'hm': 'dd-MM-yy h:mm–h:mm a',
    '_': 'dd-MM-yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_teo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_teo_KE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_teo_UG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_th_TH = {
  FULL_DATE: {
    '_': 'EEEEที่ d MMMM G y'
  },
  LONG_DATE: {
    '_': 'd MMMM G y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y H นาฬิกา mm นาที ss วินาที zzzz',
    '_': 'H นาฬิกา mm นาที ss วินาที zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y H นาฬิกา mm นาที ss วินาที z',
    '_': 'H นาฬิกา mm นาที ss วินาที z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm น. – HH:mm น.',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEEที่ d MMMM G y H นาฬิกา mm นาที ss วินาที zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM G y H นาฬิกา mm นาที ss วินาที z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/yy HH:mm น. – HH:mm น.',
    '_': 'd/M/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ti = {
  FULL_DATE: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ti_ER = {
  FULL_DATE: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ti_ET = {
  FULL_DATE: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'dd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'dd-MMM-y'
  },
  SHORT_DATE: {
    'Mdy': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE፣ dd MMMM መዓልቲ y G h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'dd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'dd-MMM-y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/yy h:mm a – h:mm a',
    'hm': 'dd/MM/yy h:mm–h:mm a',
    '_': 'dd/MM/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_to = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_to_TO = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y, h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y, h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y, h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y, h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y, h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy, h:mm a – h:mm a',
    'hm': 'd/M/yy, h:mm – h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_tr_CY = {
  FULL_DATE: {
    '_': 'd MMMM y EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.y – dd.MM.y',
    '_': 'd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y h:mm a',
    'a': 'a h:mm – a h:mm',
    'hm': 'a h:mm–h:mm',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd.MM.y a h:mm – a h:mm',
    'hm': 'd.MM.y a h:mm–h:mm',
    '_': 'd.MM.y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_tr_TR = {
  FULL_DATE: {
    '_': 'd MMMM y EEEE'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'dd.MM.y – dd.MM.y',
    '_': 'd.MM.y'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'd MMMM y EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd.MM.y HH:mm–HH:mm',
    '_': 'd.MM.y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_twq = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_twq_NE = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_tzm = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_tzm_MA = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ug = {
  FULL_DATE: {
    'Md': 'EEEE، MMMM d – EEEE، MMMM d، y',
    'y': 'EEEE، MMMM d، y – EEEE، MMMM d، y',
    '_': 'y d-MMMM، EEEE'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d، y',
    'd': 'MMMM d – d، y',
    'y': 'MMMM d، y – MMMM d، y',
    '_': 'd-MMMM، y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d، y',
    'd': 'MMM d – d، y',
    'y': 'MMM d، y – MMM d، y',
    '_': 'd-MMM، y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/y – M/d/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-d-M، h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y d-MMMM، EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd-MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd-MMM، y، h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd، h:mm a – h:mm a',
    'hm': 'y-MM-dd، h:mm – h:mm a',
    '_': 'y-MM-dd، h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ug_CN = {
  FULL_DATE: {
    'Md': 'EEEE، MMMM d – EEEE، MMMM d، y',
    'y': 'EEEE، MMMM d، y – EEEE، MMMM d، y',
    '_': 'y d-MMMM، EEEE'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d، y',
    'd': 'MMMM d – d، y',
    'y': 'MMMM d، y – MMMM d، y',
    '_': 'd-MMMM، y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d، y',
    'd': 'MMM d – d، y',
    'y': 'MMM d، y – MMM d، y',
    '_': 'd-MMM، y'
  },
  SHORT_DATE: {
    'Mdy': 'M/d/y – M/d/y',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-d-M، h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'y-d-M، h:mm a',
    'hm': 'h:mm – h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'y d-MMMM، EEEE h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd-MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd-MMM، y، h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'y-MM-dd، h:mm a – h:mm a',
    'hm': 'y-MM-dd، h:mm – h:mm a',
    '_': 'y-MM-dd، h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uk_UA = {
  FULL_DATE: {
    'M': 'EEEE, d MMMM – EEEE, d MMMM y',
    'd': 'EEEE, d – EEEE, d MMMM y',
    'y': 'EEEE, d MMMM y – EEEE, d MMMM y',
    '_': 'EEEE, d MMMM y \'р\'.'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'd MMMM y \'р\'.'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'd MMM y \'р\'.'
  },
  SHORT_DATE: {
    '_': 'dd.MM.yy'
  },
  FULL_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd.MM.y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd.MM.y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y \'р\'. \'о\' HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y \'р\'. \'о\' HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y \'р\'., HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd.MM.yy, HH:mm–HH:mm',
    '_': 'dd.MM.yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ur_IN = {
  FULL_DATE: {
    'Md': 'EEEE، d MMMM – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'y MMMM d–d',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM، y',
    'd': 'y MMM d–d',
    'y': 'd MMM، y – d MMM، y',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_ur_PK = {
  FULL_DATE: {
    'Md': 'EEEE، d MMMM – EEEE، d MMMM، y',
    '_': 'EEEE، d MMMM، y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM، y',
    'd': 'y MMMM d–d',
    '_': 'd MMMM، y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM، y',
    'd': 'y MMM d–d',
    'y': 'd MMM، y – d MMM، y',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE، d MMMM، y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM، y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy h:mm a – h:mm a',
    'hm': 'd/M/yy h:mm–h:mm a',
    '_': 'd/M/yy h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Arab = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Arab_AF = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    '_': 'y MMMM d, EEEE'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    '_': 'y MMMM d'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    '_': 'y MMM d'
  },
  SHORT_DATE: {
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'y MMMM d, EEEE HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'y MMMM d HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'y MMM d HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Cyrl = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'y': 'EEEE, d MMMM, y – EEEE, d MMMM, y',
    '_': 'EEEE, dd MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss (zzzz)',
    '_': 'HH:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss (z)',
    '_': 'HH:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM, y HH:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Cyrl_UZ = {
  FULL_DATE: {
    'Md': 'EEEE, d MMMM – EEEE, d MMMM, y',
    'y': 'EEEE, d MMMM, y – EEEE, d MMMM, y',
    '_': 'EEEE, dd MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss (zzzz)',
    '_': 'HH:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss (z)',
    '_': 'HH:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dd MMMM, y HH:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd MMMM, y HH:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Latn = {
  FULL_DATE: {
    'Md': 'EEEE, d-MMMM – EEEE, d-MMMM, y',
    '_': 'EEEE, d-MMMM, y'
  },
  LONG_DATE: {
    'M': 'd-MMMM – d-MMMM, y',
    'd': 'd – d-MMMM, y',
    '_': 'd-MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd-MMM – d-MMM, y',
    'd': 'd – d-MMM, y',
    '_': 'd-MMM, y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d-MMMM, y, H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd-MMMM, y, H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd-MMM, y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_uz_Latn_UZ = {
  FULL_DATE: {
    'Md': 'EEEE, d-MMMM – EEEE, d-MMMM, y',
    '_': 'EEEE, d-MMMM, y'
  },
  LONG_DATE: {
    'M': 'd-MMMM – d-MMMM, y',
    'd': 'd – d-MMMM, y',
    '_': 'd-MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd-MMM – d-MMM, y',
    'd': 'd – d-MMM, y',
    '_': 'd-MMM, y'
  },
  SHORT_DATE: {
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss (zzzz)',
    '_': 'H:mm:ss (zzzz)'
  },
  LONG_TIME: {
    'Mdy': 'dd/MM/y, H:mm:ss (z)',
    '_': 'H:mm:ss (z)'
  },
  MEDIUM_TIME: {
    'Mdy': 'dd/MM/y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'dd/MM/y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d-MMMM, y, H:mm:ss (zzzz)'
  },
  LONG_DATETIME: {
    '_': 'd-MMMM, y, H:mm:ss (z)'
  },
  MEDIUM_DATETIME: {
    '_': 'd-MMM, y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy, HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vai = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vai_Latn = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vai_Latn_LR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'M/d/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'M/d/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'M/d/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'M/d/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vai_Vaii = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vai_Vaii_LR = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y h:mm:ss a zzzz',
    '_': 'h:mm:ss a zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y h:mm:ss a z',
    '_': 'h:mm:ss a z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y h:mm:ss a',
    '_': 'h:mm:ss a'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y h:mm a',
    'hm': 'h:mm–h:mm a',
    '_': 'h:mm a'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y h:mm:ss a zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y h:mm:ss a z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y h:mm:ss a'
  },
  SHORT_DATETIME: {
    'a': 'dd/MM/y h:mm a – h:mm a',
    'hm': 'dd/MM/y h:mm–h:mm a',
    '_': 'dd/MM/y h:mm a'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vi_VN = {
  FULL_DATE: {
    'M': 'EEEE, dd \'tháng\' M – EEEE, dd \'tháng\' M, y',
    'd': 'EEEE, \'ngày\' dd MMMM – EEEE, \'ngày\' dd MMMM \'năm\' y',
    'y': 'EEEE, dd \'tháng\' M, y – EEEE, dd \'tháng\' M, y',
    '_': 'EEEE, d MMMM, y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM, y',
    'd': 'd – d MMMM, y',
    'y': '\'Ngày\' dd \'tháng\' M \'năm\' y - \'Ngày\' dd \'tháng\' M \'năm\' y',
    '_': 'd MMMM, y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM, y',
    'd': 'd – d MMM, y',
    'y': '\'Ngày\' dd \'tháng\' M \'năm\' y - \'Ngày\' dd \'tháng\' M \'năm\' y',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'dd/MM/y – dd/MM/y',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'HH:mm:ss zzzz, d/M/y',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'HH:mm:ss z, d/M/y',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'HH:mm:ss, d/M/y',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'HH:mm, d/M/y',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'HH:mm:ss zzzz EEEE, d MMMM, y'
  },
  LONG_DATETIME: {
    '_': 'HH:mm:ss z d MMMM, y'
  },
  MEDIUM_DATETIME: {
    '_': 'HH:mm:ss, d MMM, y'
  },
  SHORT_DATETIME: {
    'ahm': 'HH:mm–HH:mm, dd/MM/y',
    '_': 'HH:mm, dd/MM/y'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vun = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_vun_TZ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_wae = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd. – d. MMM y',
    'y': 'd. MMM y – d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm – HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_wae_CH = {
  FULL_DATE: {
    'M': 'EEEE, d. MMMM – EEEE, d. MMMM y',
    'd': 'EEEE, d. – EEEE, d. MMMM y',
    'y': 'EEEE, d. MMMM y – EEEE, d. MMMM y',
    '_': 'EEEE, d. MMMM y'
  },
  LONG_DATE: {
    'M': 'd. MMMM – d. MMMM y',
    'd': 'd. – d. MMMM y',
    'y': 'd. MMMM y – d. MMMM y',
    '_': 'd. MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd. MMM – d. MMM y',
    'd': 'd. – d. MMM y',
    'y': 'd. MMM y – d. MMM y',
    '_': 'd. MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'y-MM-dd'
  },
  FULL_TIME: {
    'Mdy': 'y-M-d HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-M-d HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-M-d HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-M-d HH:mm',
    'ahm': 'HH:mm – HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d. MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd. MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd. MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm – HH:mm',
    '_': 'y-MM-dd HH:mm'
  },
  FALLBACK: '{0} - {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_xog = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_xog_UG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yav = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yav_CM = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'd/M/y HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yi = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE, dטן MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dטן MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dטן MMM y'
  },
  SHORT_DATE: {
    'd': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dטן MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dטן MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dטן MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yi_001 = {
  FULL_DATE: {
    'Md': 'EEEE d MMMM – EEEE d MMMM y',
    'y': 'EEEE d MMMM y – EEEE d MMMM y',
    '_': 'EEEE, dטן MMMM y'
  },
  LONG_DATE: {
    'M': 'd MMMM – d MMMM y',
    'd': 'd–d MMMM y',
    'y': 'd MMMM y – d MMMM y',
    '_': 'dטן MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'd MMM – d MMM y',
    'd': 'd–d MMM y',
    'y': 'd MMM y – d MMM y',
    '_': 'dטן MMM y'
  },
  SHORT_DATE: {
    'd': 'yy-MM-dd – yy-MM-dd',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'd-M-y, HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd-M-y, HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, dטן MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'dטן MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'dטן MMM y, HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/yy, HH:mm–HH:mm',
    '_': 'dd/MM/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yo = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yo_BJ = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yo_NG = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE, d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'dd/MM/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'dd/MM/y HH:mm–HH:mm',
    '_': 'dd/MM/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yue = {
  FULL_DATE: {
    'Mdy': 'd/M/y (EEEE) 至 d/M/y (EEEE)',
    '_': 'y年M月d日 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日 EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0}至{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_yue_HK = {
  FULL_DATE: {
    'Mdy': 'd/M/y (EEEE) 至 d/M/y (EEEE)',
    '_': 'y年M月d日 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日 EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0}至{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zgh = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zgh_MA = {
  FULL_DATE: {
    'Md': 'y MMMM d, EEEE – MMMM d, EEEE',
    'y': 'y MMMM d, EEEE – y MMMM d, EEEE',
    '_': 'EEEE d MMMM y'
  },
  LONG_DATE: {
    'M': 'y MMMM d – MMMM d',
    'd': 'y MMMM d–d',
    'y': 'y MMMM d – y MMMM d',
    '_': 'd MMMM y'
  },
  MEDIUM_DATE: {
    'M': 'y MMM d – MMM d',
    'd': 'y MMM d–d',
    'y': 'y MMM d – y MMM d',
    '_': 'd MMM, y'
  },
  SHORT_DATE: {
    'Mdy': 'y-MM-dd – y-MM-dd',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    'ahm': 'HH:mm–HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE d MMMM y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'd MMMM y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'd MMM, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'y-MM-dd HH:mm–HH:mm',
    '_': 'd/M/y HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hans = {
  FULL_DATE: {
    'Mdy': 'y/M/dEEEE至y/M/dEEEE',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d – y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d – y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d zzzz ah:mm:ss',
    '_': 'zzzz ah:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d z ah:mm:ss',
    '_': 'z ah:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE zzzz ah:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 z ah:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hans_CN = {
  FULL_DATE: {
    'Mdy': 'y/M/dEEEE至y/M/dEEEE',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d – y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d – y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d zzzz ah:mm:ss',
    '_': 'zzzz ah:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d z ah:mm:ss',
    '_': 'z ah:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE zzzz ah:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 z ah:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hans_HK = {
  FULL_DATE: {
    'Mdy': 'd/M/yEEEE至d/M/yEEEE',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy至d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y zzzz ah:mm:ss',
    '_': 'zzzz ah:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y z ah:mm:ss',
    '_': 'z ah:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE zzzz ah:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 z ah:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/yy ah:mm至ah:mm',
    'hm': 'd/M/yy ah:mm至h:mm',
    '_': 'd/M/yy ah:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hans_MO = {
  FULL_DATE: {
    'Mdy': 'd/M/yEEEE至d/M/yEEEE',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy至d/M/yy',
    '_': 'd/M/yy'
  },
  FULL_TIME: {
    'Mdy': 'y年M月d日 zzzz ah:mm:ss',
    '_': 'zzzz ah:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'y年M月d日 z ah:mm:ss',
    '_': 'z ah:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'y年M月d日 ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y年M月d日 ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE zzzz ah:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 z ah:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'yy年M月d日 ah:mm至ah:mm',
    'hm': 'yy年M月d日 ah:mm至h:mm',
    '_': 'd/M/yy ah:mm'
  },
  FALLBACK: '{0}–{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hans_SG = {
  FULL_DATE: {
    'Mdy': 'd/M/yEEEE至d/M/yEEEE',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y至d/M/y',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/yy至d/M/yy',
    '_': 'dd/MM/yy'
  },
  FULL_TIME: {
    'Mdy': 'y年M月d日 zzzz ah:mm:ss',
    '_': 'zzzz ah:mm:ss'
  },
  LONG_TIME: {
    'Mdy': 'y年M月d日 z ah:mm:ss',
    '_': 'z ah:mm:ss'
  },
  MEDIUM_TIME: {
    'Mdy': 'y年M月d日 ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y年M月d日 ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE zzzz ah:mm:ss'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 z ah:mm:ss'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'yy年MM月dd日 ah:mm至ah:mm',
    'hm': 'yy年MM月dd日 ah:mm至h:mm',
    '_': 'dd/MM/yy ah:mm'
  },
  FALLBACK: '{0}至{1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hant = {
  FULL_DATE: {
    'Mdy': 'y/M/dEEEE至y/M/dEEEE',
    '_': 'y年M月d日 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日 EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hant_HK = {
  FULL_DATE: {
    'Mdy': 'd/M/y（EEEE） 至 d/M/y（EEEE）',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y ah:mm至ah:mm',
    'hm': 'd/M/y ah:mm至h:mm',
    '_': 'd/M/y ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hant_MO = {
  FULL_DATE: {
    'Mdy': 'd/M/y（EEEE） 至 d/M/y（EEEE）',
    '_': 'y年M月d日EEEE'
  },
  LONG_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'd/M/y 至 d/M/y',
    '_': 'd/M/y'
  },
  FULL_TIME: {
    'Mdy': 'd/M/y ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'd/M/y ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'd/M/y ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'd/M/y ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'd/M/y ah:mm至ah:mm',
    'hm': 'd/M/y ah:mm至h:mm',
    '_': 'd/M/y ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zh_Hant_TW = {
  FULL_DATE: {
    'Mdy': 'y/M/dEEEE至y/M/dEEEE',
    '_': 'y年M月d日 EEEE'
  },
  LONG_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  MEDIUM_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y年M月d日'
  },
  SHORT_DATE: {
    'Mdy': 'y/M/d至y/M/d',
    '_': 'y/M/d'
  },
  FULL_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [zzzz]',
    '_': 'ah:mm:ss [zzzz]'
  },
  LONG_TIME: {
    'Mdy': 'y/M/d ah:mm:ss [z]',
    '_': 'ah:mm:ss [z]'
  },
  MEDIUM_TIME: {
    'Mdy': 'y/M/d ah:mm:ss',
    '_': 'ah:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y/M/d ah:mm',
    'a': 'ah:mm至ah:mm',
    'hm': 'ah:mm至h:mm',
    '_': 'ah:mm'
  },
  FULL_DATETIME: {
    '_': 'y年M月d日 EEEE ah:mm:ss [zzzz]'
  },
  LONG_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss [z]'
  },
  MEDIUM_DATETIME: {
    '_': 'y年M月d日 ah:mm:ss'
  },
  SHORT_DATETIME: {
    'a': 'y/M/d ah:mm至ah:mm',
    'hm': 'y/M/d ah:mm至h:mm',
    '_': 'y/M/d ah:mm'
  },
  FALLBACK: '{0} – {1}'
};

/** @const {!dateIntervalSymbols.DateIntervalSymbols} */
exports.DateIntervalSymbols_zu_ZA = {
  FULL_DATE: {
    'Md': 'EEEE, MMMM d – EEEE, MMMM d, y',
    '_': 'EEEE, MMMM d, y'
  },
  LONG_DATE: {
    'M': 'MMMM d – MMMM d, y',
    'd': 'MMMM d – d, y',
    '_': 'MMMM d, y'
  },
  MEDIUM_DATE: {
    'M': 'MMM d – MMM d, y',
    'd': 'MMM d – d, y',
    '_': 'MMM d, y'
  },
  SHORT_DATE: {
    '_': 'M/d/yy'
  },
  FULL_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss zzzz',
    '_': 'HH:mm:ss zzzz'
  },
  LONG_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss z',
    '_': 'HH:mm:ss z'
  },
  MEDIUM_TIME: {
    'Mdy': 'y-MM-dd HH:mm:ss',
    '_': 'HH:mm:ss'
  },
  SHORT_TIME: {
    'Mdy': 'y-MM-dd HH:mm',
    '_': 'HH:mm'
  },
  FULL_DATETIME: {
    '_': 'EEEE, MMMM d, y HH:mm:ss zzzz'
  },
  LONG_DATETIME: {
    '_': 'MMMM d, y HH:mm:ss z'
  },
  MEDIUM_DATETIME: {
    '_': 'MMM d, y HH:mm:ss'
  },
  SHORT_DATETIME: {
    'ahm': 'M/d/yy HH:mm – HH:mm',
    '_': 'M/d/yy HH:mm'
  },
  FALLBACK: '{0} – {1}'
};

switch (goog.LOCALE) {
  case 'af_NA':
  case 'af-NA':
    defaultSymbols = exports.DateIntervalSymbols_af_NA;
    break;
  case 'af_ZA':
  case 'af-ZA':
    defaultSymbols = exports.DateIntervalSymbols_af_ZA;
    break;
  case 'agq':
    defaultSymbols = exports.DateIntervalSymbols_agq;
    break;
  case 'agq_CM':
  case 'agq-CM':
    defaultSymbols = exports.DateIntervalSymbols_agq_CM;
    break;
  case 'ak':
    defaultSymbols = exports.DateIntervalSymbols_ak;
    break;
  case 'ak_GH':
  case 'ak-GH':
    defaultSymbols = exports.DateIntervalSymbols_ak_GH;
    break;
  case 'am_ET':
  case 'am-ET':
    defaultSymbols = exports.DateIntervalSymbols_am_ET;
    break;
  case 'ar_001':
  case 'ar-001':
    defaultSymbols = exports.DateIntervalSymbols_ar_001;
    break;
  case 'ar_AE':
  case 'ar-AE':
    defaultSymbols = exports.DateIntervalSymbols_ar_AE;
    break;
  case 'ar_BH':
  case 'ar-BH':
    defaultSymbols = exports.DateIntervalSymbols_ar_BH;
    break;
  case 'ar_DJ':
  case 'ar-DJ':
    defaultSymbols = exports.DateIntervalSymbols_ar_DJ;
    break;
  case 'ar_EG':
  case 'ar-EG':
    defaultSymbols = exports.DateIntervalSymbols_ar_EG;
    break;
  case 'ar_EH':
  case 'ar-EH':
    defaultSymbols = exports.DateIntervalSymbols_ar_EH;
    break;
  case 'ar_ER':
  case 'ar-ER':
    defaultSymbols = exports.DateIntervalSymbols_ar_ER;
    break;
  case 'ar_IL':
  case 'ar-IL':
    defaultSymbols = exports.DateIntervalSymbols_ar_IL;
    break;
  case 'ar_IQ':
  case 'ar-IQ':
    defaultSymbols = exports.DateIntervalSymbols_ar_IQ;
    break;
  case 'ar_JO':
  case 'ar-JO':
    defaultSymbols = exports.DateIntervalSymbols_ar_JO;
    break;
  case 'ar_KM':
  case 'ar-KM':
    defaultSymbols = exports.DateIntervalSymbols_ar_KM;
    break;
  case 'ar_KW':
  case 'ar-KW':
    defaultSymbols = exports.DateIntervalSymbols_ar_KW;
    break;
  case 'ar_LB':
  case 'ar-LB':
    defaultSymbols = exports.DateIntervalSymbols_ar_LB;
    break;
  case 'ar_LY':
  case 'ar-LY':
    defaultSymbols = exports.DateIntervalSymbols_ar_LY;
    break;
  case 'ar_MA':
  case 'ar-MA':
    defaultSymbols = exports.DateIntervalSymbols_ar_MA;
    break;
  case 'ar_MR':
  case 'ar-MR':
    defaultSymbols = exports.DateIntervalSymbols_ar_MR;
    break;
  case 'ar_OM':
  case 'ar-OM':
    defaultSymbols = exports.DateIntervalSymbols_ar_OM;
    break;
  case 'ar_PS':
  case 'ar-PS':
    defaultSymbols = exports.DateIntervalSymbols_ar_PS;
    break;
  case 'ar_QA':
  case 'ar-QA':
    defaultSymbols = exports.DateIntervalSymbols_ar_QA;
    break;
  case 'ar_SA':
  case 'ar-SA':
    defaultSymbols = exports.DateIntervalSymbols_ar_SA;
    break;
  case 'ar_SD':
  case 'ar-SD':
    defaultSymbols = exports.DateIntervalSymbols_ar_SD;
    break;
  case 'ar_SO':
  case 'ar-SO':
    defaultSymbols = exports.DateIntervalSymbols_ar_SO;
    break;
  case 'ar_SS':
  case 'ar-SS':
    defaultSymbols = exports.DateIntervalSymbols_ar_SS;
    break;
  case 'ar_SY':
  case 'ar-SY':
    defaultSymbols = exports.DateIntervalSymbols_ar_SY;
    break;
  case 'ar_TD':
  case 'ar-TD':
    defaultSymbols = exports.DateIntervalSymbols_ar_TD;
    break;
  case 'ar_TN':
  case 'ar-TN':
    defaultSymbols = exports.DateIntervalSymbols_ar_TN;
    break;
  case 'ar_XB':
  case 'ar-XB':
    defaultSymbols = exports.DateIntervalSymbols_ar_XB;
    break;
  case 'ar_YE':
  case 'ar-YE':
    defaultSymbols = exports.DateIntervalSymbols_ar_YE;
    break;
  case 'as':
    defaultSymbols = exports.DateIntervalSymbols_as;
    break;
  case 'as_IN':
  case 'as-IN':
    defaultSymbols = exports.DateIntervalSymbols_as_IN;
    break;
  case 'asa':
    defaultSymbols = exports.DateIntervalSymbols_asa;
    break;
  case 'asa_TZ':
  case 'asa-TZ':
    defaultSymbols = exports.DateIntervalSymbols_asa_TZ;
    break;
  case 'ast':
    defaultSymbols = exports.DateIntervalSymbols_ast;
    break;
  case 'ast_ES':
  case 'ast-ES':
    defaultSymbols = exports.DateIntervalSymbols_ast_ES;
    break;
  case 'az_Cyrl':
  case 'az-Cyrl':
    defaultSymbols = exports.DateIntervalSymbols_az_Cyrl;
    break;
  case 'az_Cyrl_AZ':
  case 'az-Cyrl-AZ':
    defaultSymbols = exports.DateIntervalSymbols_az_Cyrl_AZ;
    break;
  case 'az_Latn':
  case 'az-Latn':
    defaultSymbols = exports.DateIntervalSymbols_az_Latn;
    break;
  case 'az_Latn_AZ':
  case 'az-Latn-AZ':
    defaultSymbols = exports.DateIntervalSymbols_az_Latn_AZ;
    break;
  case 'bas':
    defaultSymbols = exports.DateIntervalSymbols_bas;
    break;
  case 'bas_CM':
  case 'bas-CM':
    defaultSymbols = exports.DateIntervalSymbols_bas_CM;
    break;
  case 'be_BY':
  case 'be-BY':
    defaultSymbols = exports.DateIntervalSymbols_be_BY;
    break;
  case 'bem':
    defaultSymbols = exports.DateIntervalSymbols_bem;
    break;
  case 'bem_ZM':
  case 'bem-ZM':
    defaultSymbols = exports.DateIntervalSymbols_bem_ZM;
    break;
  case 'bez':
    defaultSymbols = exports.DateIntervalSymbols_bez;
    break;
  case 'bez_TZ':
  case 'bez-TZ':
    defaultSymbols = exports.DateIntervalSymbols_bez_TZ;
    break;
  case 'bg_BG':
  case 'bg-BG':
    defaultSymbols = exports.DateIntervalSymbols_bg_BG;
    break;
  case 'bm':
    defaultSymbols = exports.DateIntervalSymbols_bm;
    break;
  case 'bm_ML':
  case 'bm-ML':
    defaultSymbols = exports.DateIntervalSymbols_bm_ML;
    break;
  case 'bn_BD':
  case 'bn-BD':
    defaultSymbols = exports.DateIntervalSymbols_bn_BD;
    break;
  case 'bn_IN':
  case 'bn-IN':
    defaultSymbols = exports.DateIntervalSymbols_bn_IN;
    break;
  case 'bo':
    defaultSymbols = exports.DateIntervalSymbols_bo;
    break;
  case 'bo_CN':
  case 'bo-CN':
    defaultSymbols = exports.DateIntervalSymbols_bo_CN;
    break;
  case 'bo_IN':
  case 'bo-IN':
    defaultSymbols = exports.DateIntervalSymbols_bo_IN;
    break;
  case 'br_FR':
  case 'br-FR':
    defaultSymbols = exports.DateIntervalSymbols_br_FR;
    break;
  case 'brx':
    defaultSymbols = exports.DateIntervalSymbols_brx;
    break;
  case 'brx_IN':
  case 'brx-IN':
    defaultSymbols = exports.DateIntervalSymbols_brx_IN;
    break;
  case 'bs_Cyrl':
  case 'bs-Cyrl':
    defaultSymbols = exports.DateIntervalSymbols_bs_Cyrl;
    break;
  case 'bs_Cyrl_BA':
  case 'bs-Cyrl-BA':
    defaultSymbols = exports.DateIntervalSymbols_bs_Cyrl_BA;
    break;
  case 'bs_Latn':
  case 'bs-Latn':
    defaultSymbols = exports.DateIntervalSymbols_bs_Latn;
    break;
  case 'bs_Latn_BA':
  case 'bs-Latn-BA':
    defaultSymbols = exports.DateIntervalSymbols_bs_Latn_BA;
    break;
  case 'ca_AD':
  case 'ca-AD':
    defaultSymbols = exports.DateIntervalSymbols_ca_AD;
    break;
  case 'ca_ES':
  case 'ca-ES':
    defaultSymbols = exports.DateIntervalSymbols_ca_ES;
    break;
  case 'ca_FR':
  case 'ca-FR':
    defaultSymbols = exports.DateIntervalSymbols_ca_FR;
    break;
  case 'ca_IT':
  case 'ca-IT':
    defaultSymbols = exports.DateIntervalSymbols_ca_IT;
    break;
  case 'ce':
    defaultSymbols = exports.DateIntervalSymbols_ce;
    break;
  case 'ce_RU':
  case 'ce-RU':
    defaultSymbols = exports.DateIntervalSymbols_ce_RU;
    break;
  case 'cgg':
    defaultSymbols = exports.DateIntervalSymbols_cgg;
    break;
  case 'cgg_UG':
  case 'cgg-UG':
    defaultSymbols = exports.DateIntervalSymbols_cgg_UG;
    break;
  case 'chr_US':
  case 'chr-US':
    defaultSymbols = exports.DateIntervalSymbols_chr_US;
    break;
  case 'ckb':
    defaultSymbols = exports.DateIntervalSymbols_ckb;
    break;
  case 'ckb_IQ':
  case 'ckb-IQ':
    defaultSymbols = exports.DateIntervalSymbols_ckb_IQ;
    break;
  case 'ckb_IR':
  case 'ckb-IR':
    defaultSymbols = exports.DateIntervalSymbols_ckb_IR;
    break;
  case 'cs_CZ':
  case 'cs-CZ':
    defaultSymbols = exports.DateIntervalSymbols_cs_CZ;
    break;
  case 'cy_GB':
  case 'cy-GB':
    defaultSymbols = exports.DateIntervalSymbols_cy_GB;
    break;
  case 'da_DK':
  case 'da-DK':
    defaultSymbols = exports.DateIntervalSymbols_da_DK;
    break;
  case 'da_GL':
  case 'da-GL':
    defaultSymbols = exports.DateIntervalSymbols_da_GL;
    break;
  case 'dav':
    defaultSymbols = exports.DateIntervalSymbols_dav;
    break;
  case 'dav_KE':
  case 'dav-KE':
    defaultSymbols = exports.DateIntervalSymbols_dav_KE;
    break;
  case 'de_BE':
  case 'de-BE':
    defaultSymbols = exports.DateIntervalSymbols_de_BE;
    break;
  case 'de_DE':
  case 'de-DE':
    defaultSymbols = exports.DateIntervalSymbols_de_DE;
    break;
  case 'de_IT':
  case 'de-IT':
    defaultSymbols = exports.DateIntervalSymbols_de_IT;
    break;
  case 'de_LI':
  case 'de-LI':
    defaultSymbols = exports.DateIntervalSymbols_de_LI;
    break;
  case 'de_LU':
  case 'de-LU':
    defaultSymbols = exports.DateIntervalSymbols_de_LU;
    break;
  case 'dje':
    defaultSymbols = exports.DateIntervalSymbols_dje;
    break;
  case 'dje_NE':
  case 'dje-NE':
    defaultSymbols = exports.DateIntervalSymbols_dje_NE;
    break;
  case 'dsb':
    defaultSymbols = exports.DateIntervalSymbols_dsb;
    break;
  case 'dsb_DE':
  case 'dsb-DE':
    defaultSymbols = exports.DateIntervalSymbols_dsb_DE;
    break;
  case 'dua':
    defaultSymbols = exports.DateIntervalSymbols_dua;
    break;
  case 'dua_CM':
  case 'dua-CM':
    defaultSymbols = exports.DateIntervalSymbols_dua_CM;
    break;
  case 'dyo':
    defaultSymbols = exports.DateIntervalSymbols_dyo;
    break;
  case 'dyo_SN':
  case 'dyo-SN':
    defaultSymbols = exports.DateIntervalSymbols_dyo_SN;
    break;
  case 'dz':
    defaultSymbols = exports.DateIntervalSymbols_dz;
    break;
  case 'dz_BT':
  case 'dz-BT':
    defaultSymbols = exports.DateIntervalSymbols_dz_BT;
    break;
  case 'ebu':
    defaultSymbols = exports.DateIntervalSymbols_ebu;
    break;
  case 'ebu_KE':
  case 'ebu-KE':
    defaultSymbols = exports.DateIntervalSymbols_ebu_KE;
    break;
  case 'ee':
    defaultSymbols = exports.DateIntervalSymbols_ee;
    break;
  case 'ee_GH':
  case 'ee-GH':
    defaultSymbols = exports.DateIntervalSymbols_ee_GH;
    break;
  case 'ee_TG':
  case 'ee-TG':
    defaultSymbols = exports.DateIntervalSymbols_ee_TG;
    break;
  case 'el_CY':
  case 'el-CY':
    defaultSymbols = exports.DateIntervalSymbols_el_CY;
    break;
  case 'el_GR':
  case 'el-GR':
    defaultSymbols = exports.DateIntervalSymbols_el_GR;
    break;
  case 'en_001':
  case 'en-001':
    defaultSymbols = exports.DateIntervalSymbols_en_001;
    break;
  case 'en_150':
  case 'en-150':
    defaultSymbols = exports.DateIntervalSymbols_en_150;
    break;
  case 'en_AG':
  case 'en-AG':
    defaultSymbols = exports.DateIntervalSymbols_en_AG;
    break;
  case 'en_AI':
  case 'en-AI':
    defaultSymbols = exports.DateIntervalSymbols_en_AI;
    break;
  case 'en_AS':
  case 'en-AS':
    defaultSymbols = exports.DateIntervalSymbols_en_AS;
    break;
  case 'en_AT':
  case 'en-AT':
    defaultSymbols = exports.DateIntervalSymbols_en_AT;
    break;
  case 'en_BB':
  case 'en-BB':
    defaultSymbols = exports.DateIntervalSymbols_en_BB;
    break;
  case 'en_BE':
  case 'en-BE':
    defaultSymbols = exports.DateIntervalSymbols_en_BE;
    break;
  case 'en_BI':
  case 'en-BI':
    defaultSymbols = exports.DateIntervalSymbols_en_BI;
    break;
  case 'en_BM':
  case 'en-BM':
    defaultSymbols = exports.DateIntervalSymbols_en_BM;
    break;
  case 'en_BS':
  case 'en-BS':
    defaultSymbols = exports.DateIntervalSymbols_en_BS;
    break;
  case 'en_BW':
  case 'en-BW':
    defaultSymbols = exports.DateIntervalSymbols_en_BW;
    break;
  case 'en_BZ':
  case 'en-BZ':
    defaultSymbols = exports.DateIntervalSymbols_en_BZ;
    break;
  case 'en_CC':
  case 'en-CC':
    defaultSymbols = exports.DateIntervalSymbols_en_CC;
    break;
  case 'en_CH':
  case 'en-CH':
    defaultSymbols = exports.DateIntervalSymbols_en_CH;
    break;
  case 'en_CK':
  case 'en-CK':
    defaultSymbols = exports.DateIntervalSymbols_en_CK;
    break;
  case 'en_CM':
  case 'en-CM':
    defaultSymbols = exports.DateIntervalSymbols_en_CM;
    break;
  case 'en_CX':
  case 'en-CX':
    defaultSymbols = exports.DateIntervalSymbols_en_CX;
    break;
  case 'en_CY':
  case 'en-CY':
    defaultSymbols = exports.DateIntervalSymbols_en_CY;
    break;
  case 'en_DE':
  case 'en-DE':
    defaultSymbols = exports.DateIntervalSymbols_en_DE;
    break;
  case 'en_DG':
  case 'en-DG':
    defaultSymbols = exports.DateIntervalSymbols_en_DG;
    break;
  case 'en_DK':
  case 'en-DK':
    defaultSymbols = exports.DateIntervalSymbols_en_DK;
    break;
  case 'en_DM':
  case 'en-DM':
    defaultSymbols = exports.DateIntervalSymbols_en_DM;
    break;
  case 'en_ER':
  case 'en-ER':
    defaultSymbols = exports.DateIntervalSymbols_en_ER;
    break;
  case 'en_FI':
  case 'en-FI':
    defaultSymbols = exports.DateIntervalSymbols_en_FI;
    break;
  case 'en_FJ':
  case 'en-FJ':
    defaultSymbols = exports.DateIntervalSymbols_en_FJ;
    break;
  case 'en_FK':
  case 'en-FK':
    defaultSymbols = exports.DateIntervalSymbols_en_FK;
    break;
  case 'en_FM':
  case 'en-FM':
    defaultSymbols = exports.DateIntervalSymbols_en_FM;
    break;
  case 'en_GD':
  case 'en-GD':
    defaultSymbols = exports.DateIntervalSymbols_en_GD;
    break;
  case 'en_GG':
  case 'en-GG':
    defaultSymbols = exports.DateIntervalSymbols_en_GG;
    break;
  case 'en_GH':
  case 'en-GH':
    defaultSymbols = exports.DateIntervalSymbols_en_GH;
    break;
  case 'en_GI':
  case 'en-GI':
    defaultSymbols = exports.DateIntervalSymbols_en_GI;
    break;
  case 'en_GM':
  case 'en-GM':
    defaultSymbols = exports.DateIntervalSymbols_en_GM;
    break;
  case 'en_GU':
  case 'en-GU':
    defaultSymbols = exports.DateIntervalSymbols_en_GU;
    break;
  case 'en_GY':
  case 'en-GY':
    defaultSymbols = exports.DateIntervalSymbols_en_GY;
    break;
  case 'en_HK':
  case 'en-HK':
    defaultSymbols = exports.DateIntervalSymbols_en_HK;
    break;
  case 'en_IL':
  case 'en-IL':
    defaultSymbols = exports.DateIntervalSymbols_en_IL;
    break;
  case 'en_IM':
  case 'en-IM':
    defaultSymbols = exports.DateIntervalSymbols_en_IM;
    break;
  case 'en_IO':
  case 'en-IO':
    defaultSymbols = exports.DateIntervalSymbols_en_IO;
    break;
  case 'en_JE':
  case 'en-JE':
    defaultSymbols = exports.DateIntervalSymbols_en_JE;
    break;
  case 'en_JM':
  case 'en-JM':
    defaultSymbols = exports.DateIntervalSymbols_en_JM;
    break;
  case 'en_KE':
  case 'en-KE':
    defaultSymbols = exports.DateIntervalSymbols_en_KE;
    break;
  case 'en_KI':
  case 'en-KI':
    defaultSymbols = exports.DateIntervalSymbols_en_KI;
    break;
  case 'en_KN':
  case 'en-KN':
    defaultSymbols = exports.DateIntervalSymbols_en_KN;
    break;
  case 'en_KY':
  case 'en-KY':
    defaultSymbols = exports.DateIntervalSymbols_en_KY;
    break;
  case 'en_LC':
  case 'en-LC':
    defaultSymbols = exports.DateIntervalSymbols_en_LC;
    break;
  case 'en_LR':
  case 'en-LR':
    defaultSymbols = exports.DateIntervalSymbols_en_LR;
    break;
  case 'en_LS':
  case 'en-LS':
    defaultSymbols = exports.DateIntervalSymbols_en_LS;
    break;
  case 'en_MG':
  case 'en-MG':
    defaultSymbols = exports.DateIntervalSymbols_en_MG;
    break;
  case 'en_MH':
  case 'en-MH':
    defaultSymbols = exports.DateIntervalSymbols_en_MH;
    break;
  case 'en_MO':
  case 'en-MO':
    defaultSymbols = exports.DateIntervalSymbols_en_MO;
    break;
  case 'en_MP':
  case 'en-MP':
    defaultSymbols = exports.DateIntervalSymbols_en_MP;
    break;
  case 'en_MS':
  case 'en-MS':
    defaultSymbols = exports.DateIntervalSymbols_en_MS;
    break;
  case 'en_MT':
  case 'en-MT':
    defaultSymbols = exports.DateIntervalSymbols_en_MT;
    break;
  case 'en_MU':
  case 'en-MU':
    defaultSymbols = exports.DateIntervalSymbols_en_MU;
    break;
  case 'en_MW':
  case 'en-MW':
    defaultSymbols = exports.DateIntervalSymbols_en_MW;
    break;
  case 'en_MY':
  case 'en-MY':
    defaultSymbols = exports.DateIntervalSymbols_en_MY;
    break;
  case 'en_NA':
  case 'en-NA':
    defaultSymbols = exports.DateIntervalSymbols_en_NA;
    break;
  case 'en_NF':
  case 'en-NF':
    defaultSymbols = exports.DateIntervalSymbols_en_NF;
    break;
  case 'en_NG':
  case 'en-NG':
    defaultSymbols = exports.DateIntervalSymbols_en_NG;
    break;
  case 'en_NL':
  case 'en-NL':
    defaultSymbols = exports.DateIntervalSymbols_en_NL;
    break;
  case 'en_NR':
  case 'en-NR':
    defaultSymbols = exports.DateIntervalSymbols_en_NR;
    break;
  case 'en_NU':
  case 'en-NU':
    defaultSymbols = exports.DateIntervalSymbols_en_NU;
    break;
  case 'en_NZ':
  case 'en-NZ':
    defaultSymbols = exports.DateIntervalSymbols_en_NZ;
    break;
  case 'en_PG':
  case 'en-PG':
    defaultSymbols = exports.DateIntervalSymbols_en_PG;
    break;
  case 'en_PH':
  case 'en-PH':
    defaultSymbols = exports.DateIntervalSymbols_en_PH;
    break;
  case 'en_PK':
  case 'en-PK':
    defaultSymbols = exports.DateIntervalSymbols_en_PK;
    break;
  case 'en_PN':
  case 'en-PN':
    defaultSymbols = exports.DateIntervalSymbols_en_PN;
    break;
  case 'en_PR':
  case 'en-PR':
    defaultSymbols = exports.DateIntervalSymbols_en_PR;
    break;
  case 'en_PW':
  case 'en-PW':
    defaultSymbols = exports.DateIntervalSymbols_en_PW;
    break;
  case 'en_RW':
  case 'en-RW':
    defaultSymbols = exports.DateIntervalSymbols_en_RW;
    break;
  case 'en_SB':
  case 'en-SB':
    defaultSymbols = exports.DateIntervalSymbols_en_SB;
    break;
  case 'en_SC':
  case 'en-SC':
    defaultSymbols = exports.DateIntervalSymbols_en_SC;
    break;
  case 'en_SD':
  case 'en-SD':
    defaultSymbols = exports.DateIntervalSymbols_en_SD;
    break;
  case 'en_SE':
  case 'en-SE':
    defaultSymbols = exports.DateIntervalSymbols_en_SE;
    break;
  case 'en_SH':
  case 'en-SH':
    defaultSymbols = exports.DateIntervalSymbols_en_SH;
    break;
  case 'en_SI':
  case 'en-SI':
    defaultSymbols = exports.DateIntervalSymbols_en_SI;
    break;
  case 'en_SL':
  case 'en-SL':
    defaultSymbols = exports.DateIntervalSymbols_en_SL;
    break;
  case 'en_SS':
  case 'en-SS':
    defaultSymbols = exports.DateIntervalSymbols_en_SS;
    break;
  case 'en_SX':
  case 'en-SX':
    defaultSymbols = exports.DateIntervalSymbols_en_SX;
    break;
  case 'en_SZ':
  case 'en-SZ':
    defaultSymbols = exports.DateIntervalSymbols_en_SZ;
    break;
  case 'en_TC':
  case 'en-TC':
    defaultSymbols = exports.DateIntervalSymbols_en_TC;
    break;
  case 'en_TK':
  case 'en-TK':
    defaultSymbols = exports.DateIntervalSymbols_en_TK;
    break;
  case 'en_TO':
  case 'en-TO':
    defaultSymbols = exports.DateIntervalSymbols_en_TO;
    break;
  case 'en_TT':
  case 'en-TT':
    defaultSymbols = exports.DateIntervalSymbols_en_TT;
    break;
  case 'en_TV':
  case 'en-TV':
    defaultSymbols = exports.DateIntervalSymbols_en_TV;
    break;
  case 'en_TZ':
  case 'en-TZ':
    defaultSymbols = exports.DateIntervalSymbols_en_TZ;
    break;
  case 'en_UG':
  case 'en-UG':
    defaultSymbols = exports.DateIntervalSymbols_en_UG;
    break;
  case 'en_UM':
  case 'en-UM':
    defaultSymbols = exports.DateIntervalSymbols_en_UM;
    break;
  case 'en_US_POSIX':
  case 'en-US-POSIX':
    defaultSymbols = exports.DateIntervalSymbols_en_US_POSIX;
    break;
  case 'en_VC':
  case 'en-VC':
    defaultSymbols = exports.DateIntervalSymbols_en_VC;
    break;
  case 'en_VG':
  case 'en-VG':
    defaultSymbols = exports.DateIntervalSymbols_en_VG;
    break;
  case 'en_VI':
  case 'en-VI':
    defaultSymbols = exports.DateIntervalSymbols_en_VI;
    break;
  case 'en_VU':
  case 'en-VU':
    defaultSymbols = exports.DateIntervalSymbols_en_VU;
    break;
  case 'en_WS':
  case 'en-WS':
    defaultSymbols = exports.DateIntervalSymbols_en_WS;
    break;
  case 'en_XA':
  case 'en-XA':
    defaultSymbols = exports.DateIntervalSymbols_en_XA;
    break;
  case 'en_ZM':
  case 'en-ZM':
    defaultSymbols = exports.DateIntervalSymbols_en_ZM;
    break;
  case 'en_ZW':
  case 'en-ZW':
    defaultSymbols = exports.DateIntervalSymbols_en_ZW;
    break;
  case 'eo':
    defaultSymbols = exports.DateIntervalSymbols_eo;
    break;
  case 'es_AR':
  case 'es-AR':
    defaultSymbols = exports.DateIntervalSymbols_es_AR;
    break;
  case 'es_BO':
  case 'es-BO':
    defaultSymbols = exports.DateIntervalSymbols_es_BO;
    break;
  case 'es_BR':
  case 'es-BR':
    defaultSymbols = exports.DateIntervalSymbols_es_BR;
    break;
  case 'es_BZ':
  case 'es-BZ':
    defaultSymbols = exports.DateIntervalSymbols_es_BZ;
    break;
  case 'es_CL':
  case 'es-CL':
    defaultSymbols = exports.DateIntervalSymbols_es_CL;
    break;
  case 'es_CO':
  case 'es-CO':
    defaultSymbols = exports.DateIntervalSymbols_es_CO;
    break;
  case 'es_CR':
  case 'es-CR':
    defaultSymbols = exports.DateIntervalSymbols_es_CR;
    break;
  case 'es_CU':
  case 'es-CU':
    defaultSymbols = exports.DateIntervalSymbols_es_CU;
    break;
  case 'es_DO':
  case 'es-DO':
    defaultSymbols = exports.DateIntervalSymbols_es_DO;
    break;
  case 'es_EA':
  case 'es-EA':
    defaultSymbols = exports.DateIntervalSymbols_es_EA;
    break;
  case 'es_EC':
  case 'es-EC':
    defaultSymbols = exports.DateIntervalSymbols_es_EC;
    break;
  case 'es_GQ':
  case 'es-GQ':
    defaultSymbols = exports.DateIntervalSymbols_es_GQ;
    break;
  case 'es_GT':
  case 'es-GT':
    defaultSymbols = exports.DateIntervalSymbols_es_GT;
    break;
  case 'es_HN':
  case 'es-HN':
    defaultSymbols = exports.DateIntervalSymbols_es_HN;
    break;
  case 'es_IC':
  case 'es-IC':
    defaultSymbols = exports.DateIntervalSymbols_es_IC;
    break;
  case 'es_NI':
  case 'es-NI':
    defaultSymbols = exports.DateIntervalSymbols_es_NI;
    break;
  case 'es_PA':
  case 'es-PA':
    defaultSymbols = exports.DateIntervalSymbols_es_PA;
    break;
  case 'es_PE':
  case 'es-PE':
    defaultSymbols = exports.DateIntervalSymbols_es_PE;
    break;
  case 'es_PH':
  case 'es-PH':
    defaultSymbols = exports.DateIntervalSymbols_es_PH;
    break;
  case 'es_PR':
  case 'es-PR':
    defaultSymbols = exports.DateIntervalSymbols_es_PR;
    break;
  case 'es_PY':
  case 'es-PY':
    defaultSymbols = exports.DateIntervalSymbols_es_PY;
    break;
  case 'es_SV':
  case 'es-SV':
    defaultSymbols = exports.DateIntervalSymbols_es_SV;
    break;
  case 'es_UY':
  case 'es-UY':
    defaultSymbols = exports.DateIntervalSymbols_es_UY;
    break;
  case 'es_VE':
  case 'es-VE':
    defaultSymbols = exports.DateIntervalSymbols_es_VE;
    break;
  case 'et_EE':
  case 'et-EE':
    defaultSymbols = exports.DateIntervalSymbols_et_EE;
    break;
  case 'eu_ES':
  case 'eu-ES':
    defaultSymbols = exports.DateIntervalSymbols_eu_ES;
    break;
  case 'ewo':
    defaultSymbols = exports.DateIntervalSymbols_ewo;
    break;
  case 'ewo_CM':
  case 'ewo-CM':
    defaultSymbols = exports.DateIntervalSymbols_ewo_CM;
    break;
  case 'fa_AF':
  case 'fa-AF':
    defaultSymbols = exports.DateIntervalSymbols_fa_AF;
    break;
  case 'fa_IR':
  case 'fa-IR':
    defaultSymbols = exports.DateIntervalSymbols_fa_IR;
    break;
  case 'ff':
    defaultSymbols = exports.DateIntervalSymbols_ff;
    break;
  case 'ff_CM':
  case 'ff-CM':
    defaultSymbols = exports.DateIntervalSymbols_ff_CM;
    break;
  case 'ff_GN':
  case 'ff-GN':
    defaultSymbols = exports.DateIntervalSymbols_ff_GN;
    break;
  case 'ff_MR':
  case 'ff-MR':
    defaultSymbols = exports.DateIntervalSymbols_ff_MR;
    break;
  case 'ff_SN':
  case 'ff-SN':
    defaultSymbols = exports.DateIntervalSymbols_ff_SN;
    break;
  case 'fi_FI':
  case 'fi-FI':
    defaultSymbols = exports.DateIntervalSymbols_fi_FI;
    break;
  case 'fil_PH':
  case 'fil-PH':
    defaultSymbols = exports.DateIntervalSymbols_fil_PH;
    break;
  case 'fo':
    defaultSymbols = exports.DateIntervalSymbols_fo;
    break;
  case 'fo_DK':
  case 'fo-DK':
    defaultSymbols = exports.DateIntervalSymbols_fo_DK;
    break;
  case 'fo_FO':
  case 'fo-FO':
    defaultSymbols = exports.DateIntervalSymbols_fo_FO;
    break;
  case 'fr_BE':
  case 'fr-BE':
    defaultSymbols = exports.DateIntervalSymbols_fr_BE;
    break;
  case 'fr_BF':
  case 'fr-BF':
    defaultSymbols = exports.DateIntervalSymbols_fr_BF;
    break;
  case 'fr_BI':
  case 'fr-BI':
    defaultSymbols = exports.DateIntervalSymbols_fr_BI;
    break;
  case 'fr_BJ':
  case 'fr-BJ':
    defaultSymbols = exports.DateIntervalSymbols_fr_BJ;
    break;
  case 'fr_BL':
  case 'fr-BL':
    defaultSymbols = exports.DateIntervalSymbols_fr_BL;
    break;
  case 'fr_CD':
  case 'fr-CD':
    defaultSymbols = exports.DateIntervalSymbols_fr_CD;
    break;
  case 'fr_CF':
  case 'fr-CF':
    defaultSymbols = exports.DateIntervalSymbols_fr_CF;
    break;
  case 'fr_CG':
  case 'fr-CG':
    defaultSymbols = exports.DateIntervalSymbols_fr_CG;
    break;
  case 'fr_CH':
  case 'fr-CH':
    defaultSymbols = exports.DateIntervalSymbols_fr_CH;
    break;
  case 'fr_CI':
  case 'fr-CI':
    defaultSymbols = exports.DateIntervalSymbols_fr_CI;
    break;
  case 'fr_CM':
  case 'fr-CM':
    defaultSymbols = exports.DateIntervalSymbols_fr_CM;
    break;
  case 'fr_DJ':
  case 'fr-DJ':
    defaultSymbols = exports.DateIntervalSymbols_fr_DJ;
    break;
  case 'fr_DZ':
  case 'fr-DZ':
    defaultSymbols = exports.DateIntervalSymbols_fr_DZ;
    break;
  case 'fr_FR':
  case 'fr-FR':
    defaultSymbols = exports.DateIntervalSymbols_fr_FR;
    break;
  case 'fr_GA':
  case 'fr-GA':
    defaultSymbols = exports.DateIntervalSymbols_fr_GA;
    break;
  case 'fr_GF':
  case 'fr-GF':
    defaultSymbols = exports.DateIntervalSymbols_fr_GF;
    break;
  case 'fr_GN':
  case 'fr-GN':
    defaultSymbols = exports.DateIntervalSymbols_fr_GN;
    break;
  case 'fr_GP':
  case 'fr-GP':
    defaultSymbols = exports.DateIntervalSymbols_fr_GP;
    break;
  case 'fr_GQ':
  case 'fr-GQ':
    defaultSymbols = exports.DateIntervalSymbols_fr_GQ;
    break;
  case 'fr_HT':
  case 'fr-HT':
    defaultSymbols = exports.DateIntervalSymbols_fr_HT;
    break;
  case 'fr_KM':
  case 'fr-KM':
    defaultSymbols = exports.DateIntervalSymbols_fr_KM;
    break;
  case 'fr_LU':
  case 'fr-LU':
    defaultSymbols = exports.DateIntervalSymbols_fr_LU;
    break;
  case 'fr_MA':
  case 'fr-MA':
    defaultSymbols = exports.DateIntervalSymbols_fr_MA;
    break;
  case 'fr_MC':
  case 'fr-MC':
    defaultSymbols = exports.DateIntervalSymbols_fr_MC;
    break;
  case 'fr_MF':
  case 'fr-MF':
    defaultSymbols = exports.DateIntervalSymbols_fr_MF;
    break;
  case 'fr_MG':
  case 'fr-MG':
    defaultSymbols = exports.DateIntervalSymbols_fr_MG;
    break;
  case 'fr_ML':
  case 'fr-ML':
    defaultSymbols = exports.DateIntervalSymbols_fr_ML;
    break;
  case 'fr_MQ':
  case 'fr-MQ':
    defaultSymbols = exports.DateIntervalSymbols_fr_MQ;
    break;
  case 'fr_MR':
  case 'fr-MR':
    defaultSymbols = exports.DateIntervalSymbols_fr_MR;
    break;
  case 'fr_MU':
  case 'fr-MU':
    defaultSymbols = exports.DateIntervalSymbols_fr_MU;
    break;
  case 'fr_NC':
  case 'fr-NC':
    defaultSymbols = exports.DateIntervalSymbols_fr_NC;
    break;
  case 'fr_NE':
  case 'fr-NE':
    defaultSymbols = exports.DateIntervalSymbols_fr_NE;
    break;
  case 'fr_PF':
  case 'fr-PF':
    defaultSymbols = exports.DateIntervalSymbols_fr_PF;
    break;
  case 'fr_PM':
  case 'fr-PM':
    defaultSymbols = exports.DateIntervalSymbols_fr_PM;
    break;
  case 'fr_RE':
  case 'fr-RE':
    defaultSymbols = exports.DateIntervalSymbols_fr_RE;
    break;
  case 'fr_RW':
  case 'fr-RW':
    defaultSymbols = exports.DateIntervalSymbols_fr_RW;
    break;
  case 'fr_SC':
  case 'fr-SC':
    defaultSymbols = exports.DateIntervalSymbols_fr_SC;
    break;
  case 'fr_SN':
  case 'fr-SN':
    defaultSymbols = exports.DateIntervalSymbols_fr_SN;
    break;
  case 'fr_SY':
  case 'fr-SY':
    defaultSymbols = exports.DateIntervalSymbols_fr_SY;
    break;
  case 'fr_TD':
  case 'fr-TD':
    defaultSymbols = exports.DateIntervalSymbols_fr_TD;
    break;
  case 'fr_TG':
  case 'fr-TG':
    defaultSymbols = exports.DateIntervalSymbols_fr_TG;
    break;
  case 'fr_TN':
  case 'fr-TN':
    defaultSymbols = exports.DateIntervalSymbols_fr_TN;
    break;
  case 'fr_VU':
  case 'fr-VU':
    defaultSymbols = exports.DateIntervalSymbols_fr_VU;
    break;
  case 'fr_WF':
  case 'fr-WF':
    defaultSymbols = exports.DateIntervalSymbols_fr_WF;
    break;
  case 'fr_YT':
  case 'fr-YT':
    defaultSymbols = exports.DateIntervalSymbols_fr_YT;
    break;
  case 'fur':
    defaultSymbols = exports.DateIntervalSymbols_fur;
    break;
  case 'fur_IT':
  case 'fur-IT':
    defaultSymbols = exports.DateIntervalSymbols_fur_IT;
    break;
  case 'fy':
    defaultSymbols = exports.DateIntervalSymbols_fy;
    break;
  case 'fy_NL':
  case 'fy-NL':
    defaultSymbols = exports.DateIntervalSymbols_fy_NL;
    break;
  case 'ga_IE':
  case 'ga-IE':
    defaultSymbols = exports.DateIntervalSymbols_ga_IE;
    break;
  case 'gd':
    defaultSymbols = exports.DateIntervalSymbols_gd;
    break;
  case 'gd_GB':
  case 'gd-GB':
    defaultSymbols = exports.DateIntervalSymbols_gd_GB;
    break;
  case 'gl_ES':
  case 'gl-ES':
    defaultSymbols = exports.DateIntervalSymbols_gl_ES;
    break;
  case 'gsw_CH':
  case 'gsw-CH':
    defaultSymbols = exports.DateIntervalSymbols_gsw_CH;
    break;
  case 'gsw_FR':
  case 'gsw-FR':
    defaultSymbols = exports.DateIntervalSymbols_gsw_FR;
    break;
  case 'gsw_LI':
  case 'gsw-LI':
    defaultSymbols = exports.DateIntervalSymbols_gsw_LI;
    break;
  case 'gu_IN':
  case 'gu-IN':
    defaultSymbols = exports.DateIntervalSymbols_gu_IN;
    break;
  case 'guz':
    defaultSymbols = exports.DateIntervalSymbols_guz;
    break;
  case 'guz_KE':
  case 'guz-KE':
    defaultSymbols = exports.DateIntervalSymbols_guz_KE;
    break;
  case 'gv':
    defaultSymbols = exports.DateIntervalSymbols_gv;
    break;
  case 'gv_IM':
  case 'gv-IM':
    defaultSymbols = exports.DateIntervalSymbols_gv_IM;
    break;
  case 'ha':
    defaultSymbols = exports.DateIntervalSymbols_ha;
    break;
  case 'ha_GH':
  case 'ha-GH':
    defaultSymbols = exports.DateIntervalSymbols_ha_GH;
    break;
  case 'ha_NE':
  case 'ha-NE':
    defaultSymbols = exports.DateIntervalSymbols_ha_NE;
    break;
  case 'ha_NG':
  case 'ha-NG':
    defaultSymbols = exports.DateIntervalSymbols_ha_NG;
    break;
  case 'haw_US':
  case 'haw-US':
    defaultSymbols = exports.DateIntervalSymbols_haw_US;
    break;
  case 'he_IL':
  case 'he-IL':
    defaultSymbols = exports.DateIntervalSymbols_he_IL;
    break;
  case 'hi_IN':
  case 'hi-IN':
    defaultSymbols = exports.DateIntervalSymbols_hi_IN;
    break;
  case 'hr_BA':
  case 'hr-BA':
    defaultSymbols = exports.DateIntervalSymbols_hr_BA;
    break;
  case 'hr_HR':
  case 'hr-HR':
    defaultSymbols = exports.DateIntervalSymbols_hr_HR;
    break;
  case 'hsb':
    defaultSymbols = exports.DateIntervalSymbols_hsb;
    break;
  case 'hsb_DE':
  case 'hsb-DE':
    defaultSymbols = exports.DateIntervalSymbols_hsb_DE;
    break;
  case 'hu_HU':
  case 'hu-HU':
    defaultSymbols = exports.DateIntervalSymbols_hu_HU;
    break;
  case 'hy_AM':
  case 'hy-AM':
    defaultSymbols = exports.DateIntervalSymbols_hy_AM;
    break;
  case 'id_ID':
  case 'id-ID':
    defaultSymbols = exports.DateIntervalSymbols_id_ID;
    break;
  case 'ig':
    defaultSymbols = exports.DateIntervalSymbols_ig;
    break;
  case 'ig_NG':
  case 'ig-NG':
    defaultSymbols = exports.DateIntervalSymbols_ig_NG;
    break;
  case 'ii':
    defaultSymbols = exports.DateIntervalSymbols_ii;
    break;
  case 'ii_CN':
  case 'ii-CN':
    defaultSymbols = exports.DateIntervalSymbols_ii_CN;
    break;
  case 'is_IS':
  case 'is-IS':
    defaultSymbols = exports.DateIntervalSymbols_is_IS;
    break;
  case 'it_CH':
  case 'it-CH':
    defaultSymbols = exports.DateIntervalSymbols_it_CH;
    break;
  case 'it_IT':
  case 'it-IT':
    defaultSymbols = exports.DateIntervalSymbols_it_IT;
    break;
  case 'it_SM':
  case 'it-SM':
    defaultSymbols = exports.DateIntervalSymbols_it_SM;
    break;
  case 'it_VA':
  case 'it-VA':
    defaultSymbols = exports.DateIntervalSymbols_it_VA;
    break;
  case 'ja_JP':
  case 'ja-JP':
    defaultSymbols = exports.DateIntervalSymbols_ja_JP;
    break;
  case 'jgo':
    defaultSymbols = exports.DateIntervalSymbols_jgo;
    break;
  case 'jgo_CM':
  case 'jgo-CM':
    defaultSymbols = exports.DateIntervalSymbols_jgo_CM;
    break;
  case 'jmc':
    defaultSymbols = exports.DateIntervalSymbols_jmc;
    break;
  case 'jmc_TZ':
  case 'jmc-TZ':
    defaultSymbols = exports.DateIntervalSymbols_jmc_TZ;
    break;
  case 'ka_GE':
  case 'ka-GE':
    defaultSymbols = exports.DateIntervalSymbols_ka_GE;
    break;
  case 'kab':
    defaultSymbols = exports.DateIntervalSymbols_kab;
    break;
  case 'kab_DZ':
  case 'kab-DZ':
    defaultSymbols = exports.DateIntervalSymbols_kab_DZ;
    break;
  case 'kam':
    defaultSymbols = exports.DateIntervalSymbols_kam;
    break;
  case 'kam_KE':
  case 'kam-KE':
    defaultSymbols = exports.DateIntervalSymbols_kam_KE;
    break;
  case 'kde':
    defaultSymbols = exports.DateIntervalSymbols_kde;
    break;
  case 'kde_TZ':
  case 'kde-TZ':
    defaultSymbols = exports.DateIntervalSymbols_kde_TZ;
    break;
  case 'kea':
    defaultSymbols = exports.DateIntervalSymbols_kea;
    break;
  case 'kea_CV':
  case 'kea-CV':
    defaultSymbols = exports.DateIntervalSymbols_kea_CV;
    break;
  case 'khq':
    defaultSymbols = exports.DateIntervalSymbols_khq;
    break;
  case 'khq_ML':
  case 'khq-ML':
    defaultSymbols = exports.DateIntervalSymbols_khq_ML;
    break;
  case 'ki':
    defaultSymbols = exports.DateIntervalSymbols_ki;
    break;
  case 'ki_KE':
  case 'ki-KE':
    defaultSymbols = exports.DateIntervalSymbols_ki_KE;
    break;
  case 'kk_KZ':
  case 'kk-KZ':
    defaultSymbols = exports.DateIntervalSymbols_kk_KZ;
    break;
  case 'kkj':
    defaultSymbols = exports.DateIntervalSymbols_kkj;
    break;
  case 'kkj_CM':
  case 'kkj-CM':
    defaultSymbols = exports.DateIntervalSymbols_kkj_CM;
    break;
  case 'kl':
    defaultSymbols = exports.DateIntervalSymbols_kl;
    break;
  case 'kl_GL':
  case 'kl-GL':
    defaultSymbols = exports.DateIntervalSymbols_kl_GL;
    break;
  case 'kln':
    defaultSymbols = exports.DateIntervalSymbols_kln;
    break;
  case 'kln_KE':
  case 'kln-KE':
    defaultSymbols = exports.DateIntervalSymbols_kln_KE;
    break;
  case 'km_KH':
  case 'km-KH':
    defaultSymbols = exports.DateIntervalSymbols_km_KH;
    break;
  case 'kn_IN':
  case 'kn-IN':
    defaultSymbols = exports.DateIntervalSymbols_kn_IN;
    break;
  case 'ko_KP':
  case 'ko-KP':
    defaultSymbols = exports.DateIntervalSymbols_ko_KP;
    break;
  case 'ko_KR':
  case 'ko-KR':
    defaultSymbols = exports.DateIntervalSymbols_ko_KR;
    break;
  case 'kok':
    defaultSymbols = exports.DateIntervalSymbols_kok;
    break;
  case 'kok_IN':
  case 'kok-IN':
    defaultSymbols = exports.DateIntervalSymbols_kok_IN;
    break;
  case 'ks':
    defaultSymbols = exports.DateIntervalSymbols_ks;
    break;
  case 'ks_IN':
  case 'ks-IN':
    defaultSymbols = exports.DateIntervalSymbols_ks_IN;
    break;
  case 'ksb':
    defaultSymbols = exports.DateIntervalSymbols_ksb;
    break;
  case 'ksb_TZ':
  case 'ksb-TZ':
    defaultSymbols = exports.DateIntervalSymbols_ksb_TZ;
    break;
  case 'ksf':
    defaultSymbols = exports.DateIntervalSymbols_ksf;
    break;
  case 'ksf_CM':
  case 'ksf-CM':
    defaultSymbols = exports.DateIntervalSymbols_ksf_CM;
    break;
  case 'ksh':
    defaultSymbols = exports.DateIntervalSymbols_ksh;
    break;
  case 'ksh_DE':
  case 'ksh-DE':
    defaultSymbols = exports.DateIntervalSymbols_ksh_DE;
    break;
  case 'kw':
    defaultSymbols = exports.DateIntervalSymbols_kw;
    break;
  case 'kw_GB':
  case 'kw-GB':
    defaultSymbols = exports.DateIntervalSymbols_kw_GB;
    break;
  case 'ky_KG':
  case 'ky-KG':
    defaultSymbols = exports.DateIntervalSymbols_ky_KG;
    break;
  case 'lag':
    defaultSymbols = exports.DateIntervalSymbols_lag;
    break;
  case 'lag_TZ':
  case 'lag-TZ':
    defaultSymbols = exports.DateIntervalSymbols_lag_TZ;
    break;
  case 'lb':
    defaultSymbols = exports.DateIntervalSymbols_lb;
    break;
  case 'lb_LU':
  case 'lb-LU':
    defaultSymbols = exports.DateIntervalSymbols_lb_LU;
    break;
  case 'lg':
    defaultSymbols = exports.DateIntervalSymbols_lg;
    break;
  case 'lg_UG':
  case 'lg-UG':
    defaultSymbols = exports.DateIntervalSymbols_lg_UG;
    break;
  case 'lkt':
    defaultSymbols = exports.DateIntervalSymbols_lkt;
    break;
  case 'lkt_US':
  case 'lkt-US':
    defaultSymbols = exports.DateIntervalSymbols_lkt_US;
    break;
  case 'ln_AO':
  case 'ln-AO':
    defaultSymbols = exports.DateIntervalSymbols_ln_AO;
    break;
  case 'ln_CD':
  case 'ln-CD':
    defaultSymbols = exports.DateIntervalSymbols_ln_CD;
    break;
  case 'ln_CF':
  case 'ln-CF':
    defaultSymbols = exports.DateIntervalSymbols_ln_CF;
    break;
  case 'ln_CG':
  case 'ln-CG':
    defaultSymbols = exports.DateIntervalSymbols_ln_CG;
    break;
  case 'lo_LA':
  case 'lo-LA':
    defaultSymbols = exports.DateIntervalSymbols_lo_LA;
    break;
  case 'lrc':
    defaultSymbols = exports.DateIntervalSymbols_lrc;
    break;
  case 'lrc_IQ':
  case 'lrc-IQ':
    defaultSymbols = exports.DateIntervalSymbols_lrc_IQ;
    break;
  case 'lrc_IR':
  case 'lrc-IR':
    defaultSymbols = exports.DateIntervalSymbols_lrc_IR;
    break;
  case 'lt_LT':
  case 'lt-LT':
    defaultSymbols = exports.DateIntervalSymbols_lt_LT;
    break;
  case 'lu':
    defaultSymbols = exports.DateIntervalSymbols_lu;
    break;
  case 'lu_CD':
  case 'lu-CD':
    defaultSymbols = exports.DateIntervalSymbols_lu_CD;
    break;
  case 'luo':
    defaultSymbols = exports.DateIntervalSymbols_luo;
    break;
  case 'luo_KE':
  case 'luo-KE':
    defaultSymbols = exports.DateIntervalSymbols_luo_KE;
    break;
  case 'luy':
    defaultSymbols = exports.DateIntervalSymbols_luy;
    break;
  case 'luy_KE':
  case 'luy-KE':
    defaultSymbols = exports.DateIntervalSymbols_luy_KE;
    break;
  case 'lv_LV':
  case 'lv-LV':
    defaultSymbols = exports.DateIntervalSymbols_lv_LV;
    break;
  case 'mas':
    defaultSymbols = exports.DateIntervalSymbols_mas;
    break;
  case 'mas_KE':
  case 'mas-KE':
    defaultSymbols = exports.DateIntervalSymbols_mas_KE;
    break;
  case 'mas_TZ':
  case 'mas-TZ':
    defaultSymbols = exports.DateIntervalSymbols_mas_TZ;
    break;
  case 'mer':
    defaultSymbols = exports.DateIntervalSymbols_mer;
    break;
  case 'mer_KE':
  case 'mer-KE':
    defaultSymbols = exports.DateIntervalSymbols_mer_KE;
    break;
  case 'mfe':
    defaultSymbols = exports.DateIntervalSymbols_mfe;
    break;
  case 'mfe_MU':
  case 'mfe-MU':
    defaultSymbols = exports.DateIntervalSymbols_mfe_MU;
    break;
  case 'mg':
    defaultSymbols = exports.DateIntervalSymbols_mg;
    break;
  case 'mg_MG':
  case 'mg-MG':
    defaultSymbols = exports.DateIntervalSymbols_mg_MG;
    break;
  case 'mgh':
    defaultSymbols = exports.DateIntervalSymbols_mgh;
    break;
  case 'mgh_MZ':
  case 'mgh-MZ':
    defaultSymbols = exports.DateIntervalSymbols_mgh_MZ;
    break;
  case 'mgo':
    defaultSymbols = exports.DateIntervalSymbols_mgo;
    break;
  case 'mgo_CM':
  case 'mgo-CM':
    defaultSymbols = exports.DateIntervalSymbols_mgo_CM;
    break;
  case 'mk_MK':
  case 'mk-MK':
    defaultSymbols = exports.DateIntervalSymbols_mk_MK;
    break;
  case 'ml_IN':
  case 'ml-IN':
    defaultSymbols = exports.DateIntervalSymbols_ml_IN;
    break;
  case 'mn_MN':
  case 'mn-MN':
    defaultSymbols = exports.DateIntervalSymbols_mn_MN;
    break;
  case 'mr_IN':
  case 'mr-IN':
    defaultSymbols = exports.DateIntervalSymbols_mr_IN;
    break;
  case 'ms_BN':
  case 'ms-BN':
    defaultSymbols = exports.DateIntervalSymbols_ms_BN;
    break;
  case 'ms_MY':
  case 'ms-MY':
    defaultSymbols = exports.DateIntervalSymbols_ms_MY;
    break;
  case 'ms_SG':
  case 'ms-SG':
    defaultSymbols = exports.DateIntervalSymbols_ms_SG;
    break;
  case 'mt_MT':
  case 'mt-MT':
    defaultSymbols = exports.DateIntervalSymbols_mt_MT;
    break;
  case 'mua':
    defaultSymbols = exports.DateIntervalSymbols_mua;
    break;
  case 'mua_CM':
  case 'mua-CM':
    defaultSymbols = exports.DateIntervalSymbols_mua_CM;
    break;
  case 'my_MM':
  case 'my-MM':
    defaultSymbols = exports.DateIntervalSymbols_my_MM;
    break;
  case 'mzn':
    defaultSymbols = exports.DateIntervalSymbols_mzn;
    break;
  case 'mzn_IR':
  case 'mzn-IR':
    defaultSymbols = exports.DateIntervalSymbols_mzn_IR;
    break;
  case 'naq':
    defaultSymbols = exports.DateIntervalSymbols_naq;
    break;
  case 'naq_NA':
  case 'naq-NA':
    defaultSymbols = exports.DateIntervalSymbols_naq_NA;
    break;
  case 'nb_NO':
  case 'nb-NO':
    defaultSymbols = exports.DateIntervalSymbols_nb_NO;
    break;
  case 'nb_SJ':
  case 'nb-SJ':
    defaultSymbols = exports.DateIntervalSymbols_nb_SJ;
    break;
  case 'nd':
    defaultSymbols = exports.DateIntervalSymbols_nd;
    break;
  case 'nd_ZW':
  case 'nd-ZW':
    defaultSymbols = exports.DateIntervalSymbols_nd_ZW;
    break;
  case 'nds':
    defaultSymbols = exports.DateIntervalSymbols_nds;
    break;
  case 'nds_DE':
  case 'nds-DE':
    defaultSymbols = exports.DateIntervalSymbols_nds_DE;
    break;
  case 'nds_NL':
  case 'nds-NL':
    defaultSymbols = exports.DateIntervalSymbols_nds_NL;
    break;
  case 'ne_IN':
  case 'ne-IN':
    defaultSymbols = exports.DateIntervalSymbols_ne_IN;
    break;
  case 'ne_NP':
  case 'ne-NP':
    defaultSymbols = exports.DateIntervalSymbols_ne_NP;
    break;
  case 'nl_AW':
  case 'nl-AW':
    defaultSymbols = exports.DateIntervalSymbols_nl_AW;
    break;
  case 'nl_BE':
  case 'nl-BE':
    defaultSymbols = exports.DateIntervalSymbols_nl_BE;
    break;
  case 'nl_BQ':
  case 'nl-BQ':
    defaultSymbols = exports.DateIntervalSymbols_nl_BQ;
    break;
  case 'nl_CW':
  case 'nl-CW':
    defaultSymbols = exports.DateIntervalSymbols_nl_CW;
    break;
  case 'nl_NL':
  case 'nl-NL':
    defaultSymbols = exports.DateIntervalSymbols_nl_NL;
    break;
  case 'nl_SR':
  case 'nl-SR':
    defaultSymbols = exports.DateIntervalSymbols_nl_SR;
    break;
  case 'nl_SX':
  case 'nl-SX':
    defaultSymbols = exports.DateIntervalSymbols_nl_SX;
    break;
  case 'nmg':
    defaultSymbols = exports.DateIntervalSymbols_nmg;
    break;
  case 'nmg_CM':
  case 'nmg-CM':
    defaultSymbols = exports.DateIntervalSymbols_nmg_CM;
    break;
  case 'nn':
    defaultSymbols = exports.DateIntervalSymbols_nn;
    break;
  case 'nn_NO':
  case 'nn-NO':
    defaultSymbols = exports.DateIntervalSymbols_nn_NO;
    break;
  case 'nnh':
    defaultSymbols = exports.DateIntervalSymbols_nnh;
    break;
  case 'nnh_CM':
  case 'nnh-CM':
    defaultSymbols = exports.DateIntervalSymbols_nnh_CM;
    break;
  case 'nus':
    defaultSymbols = exports.DateIntervalSymbols_nus;
    break;
  case 'nus_SS':
  case 'nus-SS':
    defaultSymbols = exports.DateIntervalSymbols_nus_SS;
    break;
  case 'nyn':
    defaultSymbols = exports.DateIntervalSymbols_nyn;
    break;
  case 'nyn_UG':
  case 'nyn-UG':
    defaultSymbols = exports.DateIntervalSymbols_nyn_UG;
    break;
  case 'om':
    defaultSymbols = exports.DateIntervalSymbols_om;
    break;
  case 'om_ET':
  case 'om-ET':
    defaultSymbols = exports.DateIntervalSymbols_om_ET;
    break;
  case 'om_KE':
  case 'om-KE':
    defaultSymbols = exports.DateIntervalSymbols_om_KE;
    break;
  case 'or_IN':
  case 'or-IN':
    defaultSymbols = exports.DateIntervalSymbols_or_IN;
    break;
  case 'os':
    defaultSymbols = exports.DateIntervalSymbols_os;
    break;
  case 'os_GE':
  case 'os-GE':
    defaultSymbols = exports.DateIntervalSymbols_os_GE;
    break;
  case 'os_RU':
  case 'os-RU':
    defaultSymbols = exports.DateIntervalSymbols_os_RU;
    break;
  case 'pa_Arab':
  case 'pa-Arab':
    defaultSymbols = exports.DateIntervalSymbols_pa_Arab;
    break;
  case 'pa_Arab_PK':
  case 'pa-Arab-PK':
    defaultSymbols = exports.DateIntervalSymbols_pa_Arab_PK;
    break;
  case 'pa_Guru':
  case 'pa-Guru':
    defaultSymbols = exports.DateIntervalSymbols_pa_Guru;
    break;
  case 'pa_Guru_IN':
  case 'pa-Guru-IN':
    defaultSymbols = exports.DateIntervalSymbols_pa_Guru_IN;
    break;
  case 'pl_PL':
  case 'pl-PL':
    defaultSymbols = exports.DateIntervalSymbols_pl_PL;
    break;
  case 'ps':
    defaultSymbols = exports.DateIntervalSymbols_ps;
    break;
  case 'ps_AF':
  case 'ps-AF':
    defaultSymbols = exports.DateIntervalSymbols_ps_AF;
    break;
  case 'pt_AO':
  case 'pt-AO':
    defaultSymbols = exports.DateIntervalSymbols_pt_AO;
    break;
  case 'pt_CH':
  case 'pt-CH':
    defaultSymbols = exports.DateIntervalSymbols_pt_CH;
    break;
  case 'pt_CV':
  case 'pt-CV':
    defaultSymbols = exports.DateIntervalSymbols_pt_CV;
    break;
  case 'pt_GQ':
  case 'pt-GQ':
    defaultSymbols = exports.DateIntervalSymbols_pt_GQ;
    break;
  case 'pt_GW':
  case 'pt-GW':
    defaultSymbols = exports.DateIntervalSymbols_pt_GW;
    break;
  case 'pt_LU':
  case 'pt-LU':
    defaultSymbols = exports.DateIntervalSymbols_pt_LU;
    break;
  case 'pt_MO':
  case 'pt-MO':
    defaultSymbols = exports.DateIntervalSymbols_pt_MO;
    break;
  case 'pt_MZ':
  case 'pt-MZ':
    defaultSymbols = exports.DateIntervalSymbols_pt_MZ;
    break;
  case 'pt_ST':
  case 'pt-ST':
    defaultSymbols = exports.DateIntervalSymbols_pt_ST;
    break;
  case 'pt_TL':
  case 'pt-TL':
    defaultSymbols = exports.DateIntervalSymbols_pt_TL;
    break;
  case 'qu':
    defaultSymbols = exports.DateIntervalSymbols_qu;
    break;
  case 'qu_BO':
  case 'qu-BO':
    defaultSymbols = exports.DateIntervalSymbols_qu_BO;
    break;
  case 'qu_EC':
  case 'qu-EC':
    defaultSymbols = exports.DateIntervalSymbols_qu_EC;
    break;
  case 'qu_PE':
  case 'qu-PE':
    defaultSymbols = exports.DateIntervalSymbols_qu_PE;
    break;
  case 'rm':
    defaultSymbols = exports.DateIntervalSymbols_rm;
    break;
  case 'rm_CH':
  case 'rm-CH':
    defaultSymbols = exports.DateIntervalSymbols_rm_CH;
    break;
  case 'rn':
    defaultSymbols = exports.DateIntervalSymbols_rn;
    break;
  case 'rn_BI':
  case 'rn-BI':
    defaultSymbols = exports.DateIntervalSymbols_rn_BI;
    break;
  case 'ro_MD':
  case 'ro-MD':
    defaultSymbols = exports.DateIntervalSymbols_ro_MD;
    break;
  case 'ro_RO':
  case 'ro-RO':
    defaultSymbols = exports.DateIntervalSymbols_ro_RO;
    break;
  case 'rof':
    defaultSymbols = exports.DateIntervalSymbols_rof;
    break;
  case 'rof_TZ':
  case 'rof-TZ':
    defaultSymbols = exports.DateIntervalSymbols_rof_TZ;
    break;
  case 'ru_BY':
  case 'ru-BY':
    defaultSymbols = exports.DateIntervalSymbols_ru_BY;
    break;
  case 'ru_KG':
  case 'ru-KG':
    defaultSymbols = exports.DateIntervalSymbols_ru_KG;
    break;
  case 'ru_KZ':
  case 'ru-KZ':
    defaultSymbols = exports.DateIntervalSymbols_ru_KZ;
    break;
  case 'ru_MD':
  case 'ru-MD':
    defaultSymbols = exports.DateIntervalSymbols_ru_MD;
    break;
  case 'ru_RU':
  case 'ru-RU':
    defaultSymbols = exports.DateIntervalSymbols_ru_RU;
    break;
  case 'ru_UA':
  case 'ru-UA':
    defaultSymbols = exports.DateIntervalSymbols_ru_UA;
    break;
  case 'rw':
    defaultSymbols = exports.DateIntervalSymbols_rw;
    break;
  case 'rw_RW':
  case 'rw-RW':
    defaultSymbols = exports.DateIntervalSymbols_rw_RW;
    break;
  case 'rwk':
    defaultSymbols = exports.DateIntervalSymbols_rwk;
    break;
  case 'rwk_TZ':
  case 'rwk-TZ':
    defaultSymbols = exports.DateIntervalSymbols_rwk_TZ;
    break;
  case 'sah':
    defaultSymbols = exports.DateIntervalSymbols_sah;
    break;
  case 'sah_RU':
  case 'sah-RU':
    defaultSymbols = exports.DateIntervalSymbols_sah_RU;
    break;
  case 'saq':
    defaultSymbols = exports.DateIntervalSymbols_saq;
    break;
  case 'saq_KE':
  case 'saq-KE':
    defaultSymbols = exports.DateIntervalSymbols_saq_KE;
    break;
  case 'sbp':
    defaultSymbols = exports.DateIntervalSymbols_sbp;
    break;
  case 'sbp_TZ':
  case 'sbp-TZ':
    defaultSymbols = exports.DateIntervalSymbols_sbp_TZ;
    break;
  case 'se':
    defaultSymbols = exports.DateIntervalSymbols_se;
    break;
  case 'se_FI':
  case 'se-FI':
    defaultSymbols = exports.DateIntervalSymbols_se_FI;
    break;
  case 'se_NO':
  case 'se-NO':
    defaultSymbols = exports.DateIntervalSymbols_se_NO;
    break;
  case 'se_SE':
  case 'se-SE':
    defaultSymbols = exports.DateIntervalSymbols_se_SE;
    break;
  case 'seh':
    defaultSymbols = exports.DateIntervalSymbols_seh;
    break;
  case 'seh_MZ':
  case 'seh-MZ':
    defaultSymbols = exports.DateIntervalSymbols_seh_MZ;
    break;
  case 'ses':
    defaultSymbols = exports.DateIntervalSymbols_ses;
    break;
  case 'ses_ML':
  case 'ses-ML':
    defaultSymbols = exports.DateIntervalSymbols_ses_ML;
    break;
  case 'sg':
    defaultSymbols = exports.DateIntervalSymbols_sg;
    break;
  case 'sg_CF':
  case 'sg-CF':
    defaultSymbols = exports.DateIntervalSymbols_sg_CF;
    break;
  case 'shi':
    defaultSymbols = exports.DateIntervalSymbols_shi;
    break;
  case 'shi_Latn':
  case 'shi-Latn':
    defaultSymbols = exports.DateIntervalSymbols_shi_Latn;
    break;
  case 'shi_Latn_MA':
  case 'shi-Latn-MA':
    defaultSymbols = exports.DateIntervalSymbols_shi_Latn_MA;
    break;
  case 'shi_Tfng':
  case 'shi-Tfng':
    defaultSymbols = exports.DateIntervalSymbols_shi_Tfng;
    break;
  case 'shi_Tfng_MA':
  case 'shi-Tfng-MA':
    defaultSymbols = exports.DateIntervalSymbols_shi_Tfng_MA;
    break;
  case 'si_LK':
  case 'si-LK':
    defaultSymbols = exports.DateIntervalSymbols_si_LK;
    break;
  case 'sk_SK':
  case 'sk-SK':
    defaultSymbols = exports.DateIntervalSymbols_sk_SK;
    break;
  case 'sl_SI':
  case 'sl-SI':
    defaultSymbols = exports.DateIntervalSymbols_sl_SI;
    break;
  case 'smn':
    defaultSymbols = exports.DateIntervalSymbols_smn;
    break;
  case 'smn_FI':
  case 'smn-FI':
    defaultSymbols = exports.DateIntervalSymbols_smn_FI;
    break;
  case 'sn':
    defaultSymbols = exports.DateIntervalSymbols_sn;
    break;
  case 'sn_ZW':
  case 'sn-ZW':
    defaultSymbols = exports.DateIntervalSymbols_sn_ZW;
    break;
  case 'so':
    defaultSymbols = exports.DateIntervalSymbols_so;
    break;
  case 'so_DJ':
  case 'so-DJ':
    defaultSymbols = exports.DateIntervalSymbols_so_DJ;
    break;
  case 'so_ET':
  case 'so-ET':
    defaultSymbols = exports.DateIntervalSymbols_so_ET;
    break;
  case 'so_KE':
  case 'so-KE':
    defaultSymbols = exports.DateIntervalSymbols_so_KE;
    break;
  case 'so_SO':
  case 'so-SO':
    defaultSymbols = exports.DateIntervalSymbols_so_SO;
    break;
  case 'sq_AL':
  case 'sq-AL':
    defaultSymbols = exports.DateIntervalSymbols_sq_AL;
    break;
  case 'sq_MK':
  case 'sq-MK':
    defaultSymbols = exports.DateIntervalSymbols_sq_MK;
    break;
  case 'sq_XK':
  case 'sq-XK':
    defaultSymbols = exports.DateIntervalSymbols_sq_XK;
    break;
  case 'sr_Cyrl':
  case 'sr-Cyrl':
    defaultSymbols = exports.DateIntervalSymbols_sr_Cyrl;
    break;
  case 'sr_Cyrl_BA':
  case 'sr-Cyrl-BA':
    defaultSymbols = exports.DateIntervalSymbols_sr_Cyrl_BA;
    break;
  case 'sr_Cyrl_ME':
  case 'sr-Cyrl-ME':
    defaultSymbols = exports.DateIntervalSymbols_sr_Cyrl_ME;
    break;
  case 'sr_Cyrl_RS':
  case 'sr-Cyrl-RS':
    defaultSymbols = exports.DateIntervalSymbols_sr_Cyrl_RS;
    break;
  case 'sr_Cyrl_XK':
  case 'sr-Cyrl-XK':
    defaultSymbols = exports.DateIntervalSymbols_sr_Cyrl_XK;
    break;
  case 'sr_Latn_BA':
  case 'sr-Latn-BA':
    defaultSymbols = exports.DateIntervalSymbols_sr_Latn_BA;
    break;
  case 'sr_Latn_ME':
  case 'sr-Latn-ME':
    defaultSymbols = exports.DateIntervalSymbols_sr_Latn_ME;
    break;
  case 'sr_Latn_RS':
  case 'sr-Latn-RS':
    defaultSymbols = exports.DateIntervalSymbols_sr_Latn_RS;
    break;
  case 'sr_Latn_XK':
  case 'sr-Latn-XK':
    defaultSymbols = exports.DateIntervalSymbols_sr_Latn_XK;
    break;
  case 'sv_AX':
  case 'sv-AX':
    defaultSymbols = exports.DateIntervalSymbols_sv_AX;
    break;
  case 'sv_FI':
  case 'sv-FI':
    defaultSymbols = exports.DateIntervalSymbols_sv_FI;
    break;
  case 'sv_SE':
  case 'sv-SE':
    defaultSymbols = exports.DateIntervalSymbols_sv_SE;
    break;
  case 'sw_CD':
  case 'sw-CD':
    defaultSymbols = exports.DateIntervalSymbols_sw_CD;
    break;
  case 'sw_KE':
  case 'sw-KE':
    defaultSymbols = exports.DateIntervalSymbols_sw_KE;
    break;
  case 'sw_TZ':
  case 'sw-TZ':
    defaultSymbols = exports.DateIntervalSymbols_sw_TZ;
    break;
  case 'sw_UG':
  case 'sw-UG':
    defaultSymbols = exports.DateIntervalSymbols_sw_UG;
    break;
  case 'ta_IN':
  case 'ta-IN':
    defaultSymbols = exports.DateIntervalSymbols_ta_IN;
    break;
  case 'ta_LK':
  case 'ta-LK':
    defaultSymbols = exports.DateIntervalSymbols_ta_LK;
    break;
  case 'ta_MY':
  case 'ta-MY':
    defaultSymbols = exports.DateIntervalSymbols_ta_MY;
    break;
  case 'ta_SG':
  case 'ta-SG':
    defaultSymbols = exports.DateIntervalSymbols_ta_SG;
    break;
  case 'te_IN':
  case 'te-IN':
    defaultSymbols = exports.DateIntervalSymbols_te_IN;
    break;
  case 'teo':
    defaultSymbols = exports.DateIntervalSymbols_teo;
    break;
  case 'teo_KE':
  case 'teo-KE':
    defaultSymbols = exports.DateIntervalSymbols_teo_KE;
    break;
  case 'teo_UG':
  case 'teo-UG':
    defaultSymbols = exports.DateIntervalSymbols_teo_UG;
    break;
  case 'th_TH':
  case 'th-TH':
    defaultSymbols = exports.DateIntervalSymbols_th_TH;
    break;
  case 'ti':
    defaultSymbols = exports.DateIntervalSymbols_ti;
    break;
  case 'ti_ER':
  case 'ti-ER':
    defaultSymbols = exports.DateIntervalSymbols_ti_ER;
    break;
  case 'ti_ET':
  case 'ti-ET':
    defaultSymbols = exports.DateIntervalSymbols_ti_ET;
    break;
  case 'to':
    defaultSymbols = exports.DateIntervalSymbols_to;
    break;
  case 'to_TO':
  case 'to-TO':
    defaultSymbols = exports.DateIntervalSymbols_to_TO;
    break;
  case 'tr_CY':
  case 'tr-CY':
    defaultSymbols = exports.DateIntervalSymbols_tr_CY;
    break;
  case 'tr_TR':
  case 'tr-TR':
    defaultSymbols = exports.DateIntervalSymbols_tr_TR;
    break;
  case 'twq':
    defaultSymbols = exports.DateIntervalSymbols_twq;
    break;
  case 'twq_NE':
  case 'twq-NE':
    defaultSymbols = exports.DateIntervalSymbols_twq_NE;
    break;
  case 'tzm':
    defaultSymbols = exports.DateIntervalSymbols_tzm;
    break;
  case 'tzm_MA':
  case 'tzm-MA':
    defaultSymbols = exports.DateIntervalSymbols_tzm_MA;
    break;
  case 'ug':
    defaultSymbols = exports.DateIntervalSymbols_ug;
    break;
  case 'ug_CN':
  case 'ug-CN':
    defaultSymbols = exports.DateIntervalSymbols_ug_CN;
    break;
  case 'uk_UA':
  case 'uk-UA':
    defaultSymbols = exports.DateIntervalSymbols_uk_UA;
    break;
  case 'ur_IN':
  case 'ur-IN':
    defaultSymbols = exports.DateIntervalSymbols_ur_IN;
    break;
  case 'ur_PK':
  case 'ur-PK':
    defaultSymbols = exports.DateIntervalSymbols_ur_PK;
    break;
  case 'uz_Arab':
  case 'uz-Arab':
    defaultSymbols = exports.DateIntervalSymbols_uz_Arab;
    break;
  case 'uz_Arab_AF':
  case 'uz-Arab-AF':
    defaultSymbols = exports.DateIntervalSymbols_uz_Arab_AF;
    break;
  case 'uz_Cyrl':
  case 'uz-Cyrl':
    defaultSymbols = exports.DateIntervalSymbols_uz_Cyrl;
    break;
  case 'uz_Cyrl_UZ':
  case 'uz-Cyrl-UZ':
    defaultSymbols = exports.DateIntervalSymbols_uz_Cyrl_UZ;
    break;
  case 'uz_Latn':
  case 'uz-Latn':
    defaultSymbols = exports.DateIntervalSymbols_uz_Latn;
    break;
  case 'uz_Latn_UZ':
  case 'uz-Latn-UZ':
    defaultSymbols = exports.DateIntervalSymbols_uz_Latn_UZ;
    break;
  case 'vai':
    defaultSymbols = exports.DateIntervalSymbols_vai;
    break;
  case 'vai_Latn':
  case 'vai-Latn':
    defaultSymbols = exports.DateIntervalSymbols_vai_Latn;
    break;
  case 'vai_Latn_LR':
  case 'vai-Latn-LR':
    defaultSymbols = exports.DateIntervalSymbols_vai_Latn_LR;
    break;
  case 'vai_Vaii':
  case 'vai-Vaii':
    defaultSymbols = exports.DateIntervalSymbols_vai_Vaii;
    break;
  case 'vai_Vaii_LR':
  case 'vai-Vaii-LR':
    defaultSymbols = exports.DateIntervalSymbols_vai_Vaii_LR;
    break;
  case 'vi_VN':
  case 'vi-VN':
    defaultSymbols = exports.DateIntervalSymbols_vi_VN;
    break;
  case 'vun':
    defaultSymbols = exports.DateIntervalSymbols_vun;
    break;
  case 'vun_TZ':
  case 'vun-TZ':
    defaultSymbols = exports.DateIntervalSymbols_vun_TZ;
    break;
  case 'wae':
    defaultSymbols = exports.DateIntervalSymbols_wae;
    break;
  case 'wae_CH':
  case 'wae-CH':
    defaultSymbols = exports.DateIntervalSymbols_wae_CH;
    break;
  case 'xog':
    defaultSymbols = exports.DateIntervalSymbols_xog;
    break;
  case 'xog_UG':
  case 'xog-UG':
    defaultSymbols = exports.DateIntervalSymbols_xog_UG;
    break;
  case 'yav':
    defaultSymbols = exports.DateIntervalSymbols_yav;
    break;
  case 'yav_CM':
  case 'yav-CM':
    defaultSymbols = exports.DateIntervalSymbols_yav_CM;
    break;
  case 'yi':
    defaultSymbols = exports.DateIntervalSymbols_yi;
    break;
  case 'yi_001':
  case 'yi-001':
    defaultSymbols = exports.DateIntervalSymbols_yi_001;
    break;
  case 'yo':
    defaultSymbols = exports.DateIntervalSymbols_yo;
    break;
  case 'yo_BJ':
  case 'yo-BJ':
    defaultSymbols = exports.DateIntervalSymbols_yo_BJ;
    break;
  case 'yo_NG':
  case 'yo-NG':
    defaultSymbols = exports.DateIntervalSymbols_yo_NG;
    break;
  case 'yue':
    defaultSymbols = exports.DateIntervalSymbols_yue;
    break;
  case 'yue_HK':
  case 'yue-HK':
    defaultSymbols = exports.DateIntervalSymbols_yue_HK;
    break;
  case 'zgh':
    defaultSymbols = exports.DateIntervalSymbols_zgh;
    break;
  case 'zgh_MA':
  case 'zgh-MA':
    defaultSymbols = exports.DateIntervalSymbols_zgh_MA;
    break;
  case 'zh_Hans':
  case 'zh-Hans':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hans;
    break;
  case 'zh_Hans_CN':
  case 'zh-Hans-CN':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hans_CN;
    break;
  case 'zh_Hans_HK':
  case 'zh-Hans-HK':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hans_HK;
    break;
  case 'zh_Hans_MO':
  case 'zh-Hans-MO':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hans_MO;
    break;
  case 'zh_Hans_SG':
  case 'zh-Hans-SG':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hans_SG;
    break;
  case 'zh_Hant':
  case 'zh-Hant':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hant;
    break;
  case 'zh_Hant_HK':
  case 'zh-Hant-HK':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hant_HK;
    break;
  case 'zh_Hant_MO':
  case 'zh-Hant-MO':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hant_MO;
    break;
  case 'zh_Hant_TW':
  case 'zh-Hant-TW':
    defaultSymbols = exports.DateIntervalSymbols_zh_Hant_TW;
    break;
  case 'zu_ZA':
  case 'zu-ZA':
    defaultSymbols = exports.DateIntervalSymbols_zu_ZA;
    break;
}

if (defaultSymbols != null) {
  dateIntervalSymbols.setDateIntervalSymbols(defaultSymbols);
}
