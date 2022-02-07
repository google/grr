import {initTestEnvironment} from '../testing';

import {addToMap, compareAlphabeticallyBy, compareDateNewestFirst, compareDateOldestFirst, mergeMaps, toMap} from './type_utils';

initTestEnvironment();

const mapOf = <K extends {}>(obj: K) => new Map(Object.entries(obj));

describe('mergeMaps', () => {
  it('merges two maps', () => {
    expect(mergeMaps(mapOf({a: 1, b: 2}), mapOf({c: 3})))
        .toEqual(mapOf({a: 1, b: 2, c: 3}));
  });

  it('merges many maps', () => {
    expect(mergeMaps(mapOf({a: 1, b: 2}), mapOf({c: 3}), mapOf({d: 4})))
        .toEqual(mapOf({a: 1, b: 2, c: 3, d: 4}));
  });

  it('ignores null and undefined', () => {
    expect(
        mergeMaps(
            null, mapOf({a: 1, b: 2}), undefined, mapOf({c: 3}), null,
            mapOf({d: 4}), undefined),
        )
        .toEqual(mapOf({a: 1, b: 2, c: 3, d: 4}));

    expect(mergeMaps(null)).toEqual(new Map());
    expect(mergeMaps(undefined)).toEqual(new Map());
    expect(mergeMaps()).toEqual(new Map());
  });

  it('overwrites duplicate values from left to right', () => {
    expect(mergeMaps(
               mapOf({a: 1, b: 1}),
               mapOf({b: 2, c: 2, d: 2}),
               mapOf({b: 3, c: 3}),
               ))
        .toEqual(mapOf({a: 1, b: 3, c: 3, d: 2}));
  });
});

describe('toMap', () => {
  it('applies keymapper', () => {
    expect(toMap([1, 2, 3], (i) => `key${i}`))
        .toEqual(mapOf({'key1': 1, 'key2': 2, 'key3': 3}));
  });

  it('handles empty array', () => {
    expect(toMap([], () => {
      throw new Error();
    })).toEqual(new Map());
  });
});

describe('addToMap', () => {
  it('adds entry to map', () => {
    expect(addToMap(mapOf({a: 1}), 'b', 2)).toEqual(mapOf({'a': 1, 'b': 2}));
  });

  it('handles null and undefined', () => {
    expect(addToMap(null, 'b', 2)).toEqual(mapOf({'b': 2}));
    expect(addToMap(undefined, 'b', 2)).toEqual(mapOf({'b': 2}));
  });

  it('overwrites the value with the same key', () => {
    expect(addToMap(mapOf({a: 1}), 'a', 2)).toEqual(mapOf({'a': 2}));
  });
});

describe('compareDateOldestFirst', () => {
  it('sorts old to new', () => {
    const list =
        [{date: new Date(5)}, {date: new Date(1)}, {date: new Date(3)}];
    list.sort(compareDateOldestFirst(obj => obj.date));

    expect(list).toEqual(
        [{date: new Date(1)}, {date: new Date(3)}, {date: new Date(5)}]);
  });
});

describe('compareDateNewestFirst', () => {
  it('sorts new to old', () => {
    const list =
        [{date: new Date(5)}, {date: new Date(1)}, {date: new Date(3)}];
    list.sort(compareDateNewestFirst(obj => obj.date));

    expect(list).toEqual(
        [{date: new Date(5)}, {date: new Date(3)}, {date: new Date(1)}]);
  });
});

describe('compareAlphabeticallyBy', () => {
  it('sorts alphabetically', () => {
    const list = [{s: '5'}, {s: '1'}, {s: '3'}];
    list.sort(compareAlphabeticallyBy(obj => obj.s));

    expect(list).toEqual([{s: '1'}, {s: '3'}, {s: '5'}]);
  });
});
