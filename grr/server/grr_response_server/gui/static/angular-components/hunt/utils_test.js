goog.module('grrUi.hunt.utilsTest');
goog.setTestOnly();

const {huntExpirationTime} = goog.require('grrUi.hunt.utils');


describe('hunt utils', () => {
  describe('huntExpirationTime', () => {
    const getDuration = (millis) => ({
      type: 'DurationSeconds',
      value: millis / 1000000,
    });

    const getTimestamp = (epoch_millis) => ({
      type: 'RDFDatetime',
      value: epoch_millis,
    });

    const getHunt = (value) => ({
      type: 'ApiHunt',
      value: value,
    });

    it('returns `undefined` if initial start time is not defined', () => {
      const hunt = getHunt({
        duration: getDuration(42),
      });

      expect(huntExpirationTime(hunt)).toBeUndefined();
    });

    it('returns `undefined` if duration is not defined', () => {
      const hunt = getHunt({
        init_start_time: getTimestamp(1337),
      });

      expect(huntExpirationTime(hunt)).toBeUndefined();
    });

    it('returns a value if both start time and duration are defined', () => {
      const hunt = getHunt({
        init_start_time: getTimestamp(10800),
        duration: getDuration(2000),
      });

      expect(huntExpirationTime(hunt)).toEqual(getTimestamp(12800));
    });
  });
});
