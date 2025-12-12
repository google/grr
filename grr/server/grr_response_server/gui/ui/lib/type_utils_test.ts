import {compareAlphabeticallyBy, compareDateNewestFirst} from './type_utils';

describe('compareDateNewestFirst', () => {
  it('sorts new to old', () => {
    const list = [
      {date: new Date(5)},
      {date: new Date(1)},
      {date: new Date(3)},
    ];
    list.sort(compareDateNewestFirst((obj) => obj.date));

    expect(list).toEqual([
      {date: new Date(5)},
      {date: new Date(3)},
      {date: new Date(1)},
    ]);
  });
});

describe('compareAlphabeticallyBy', () => {
  it('sorts alphabetically', () => {
    const list = [{s: '5'}, {s: '1'}, {s: '3'}];
    list.sort(compareAlphabeticallyBy((obj) => obj.s));

    expect(list).toEqual([{s: '1'}, {s: '3'}, {s: '5'}]);
  });
});
