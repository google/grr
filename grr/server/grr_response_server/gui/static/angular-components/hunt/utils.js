goog.module('grrUi.hunt.utils');
goog.module.declareLegacyNamespace();

/**
 * @typedef {{
 *   type: string,
 *   value: number,
 * }}
 */
let DurationSeconds;

/**
 * @typedef {{
 *   type: string,
 *   value: number,
 * }}
 */
let Timestamp;

/**
 * @typedef {{
 *   type: string,
 *   value: {
 *     init_start_time: (!Timestamp|undefined),
 *     duration: (!DurationSeconds|undefined),
 *   },
 * }}
 */
let Hunt;

/**
 * Computes the expiration time of a given hunt object.
 *
 * @param {!Hunt} hunt An RDF wrapper for a hunt object.
 * @return {(!Timestamp|undefined)} An RDF wrapper for a timestamp object.
 */
exports.huntExpirationTime = (hunt) => {
  const initStartTime = hunt.value.init_start_time;
  const duration = hunt.value.duration;

  if (initStartTime === undefined || duration === undefined) {
    return undefined;
  }

  // DurationSeconds are given in seconds, whereas timestamps use microseconds
  // since epoch. Thus, we have to convert the duration value.
  return {
    type: 'RDFDatetime',
    value: initStartTime.value + duration.value * 1000000,
  };
};

exports.DurationSeconds = DurationSeconds;
exports.Timestamp = Timestamp;
exports.Hunt = Hunt;
