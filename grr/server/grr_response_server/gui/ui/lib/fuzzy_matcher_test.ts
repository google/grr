import {initTestEnvironment} from '../testing';

import {FuzzyMatcher, Match, stringWithHighlightsFromMatch} from './fuzzy_matcher';

initTestEnvironment();

describe('FuzzyMatcher', () => {
  const SINGLE_STRING_SET: ReadonlyArray<string> = ['blah and wah'];

  const MULTIPLE_STRINGS_SET: ReadonlyArray<string> = [
    'foo bar',
    'blah and wah1',
    'blah and wah2',
  ];

  it('does not match anything when no subjects registered', () => {
    const matcher = new FuzzyMatcher([]);
    expect(matcher.match('blah')).toEqual([]);
  });

  it('matches everything when user input is empty', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);
    expect(matcher.match('')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 0]],
    }]);
  });

  it('correctly matches single subjects by a proper substring', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);

    expect(matcher.match('blah')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 4]],
    }]);
    expect(matcher.match('wah')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[9, 12]],
    }]);
    expect(matcher.match('d w')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[7, 10]],
    }]);
  });

  it('does substring-based match in case-insensitive way', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);

    expect(matcher.match('BLAH')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 4]],
    }]);
  });

  it('correctly matches single string by set of prefixes', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);

    expect(matcher.match('bw')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 1], [9, 10]],
    }]);
    expect(matcher.match('blw')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 2], [9, 10]],
    }]);
    expect(matcher.match('baw')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 1], [5, 6], [9, 10]],
    }]);
  });

  it('does prefix-based match in case-insensitive way', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);

    expect(matcher.match('BW')).toEqual([{
      subject: SINGLE_STRING_SET[0],
      matchRanges: [[0, 1], [9, 10]],
    }]);
  });

  it('does not match single string when no prefix or substring match', () => {
    const matcher = new FuzzyMatcher(SINGLE_STRING_SET);

    expect(matcher.match('foo')).toEqual([]);
  });

  it('correctly matches multiple strings by a proper substring', () => {
    const matcher = new FuzzyMatcher(MULTIPLE_STRINGS_SET);

    expect(matcher.match('oo')).toEqual([{
      subject: MULTIPLE_STRINGS_SET[0],
      matchRanges: [[1, 3]],
    }]);
    expect(matcher.match('la')).toEqual([
      {
        subject: MULTIPLE_STRINGS_SET[1],
        matchRanges: [[1, 3]],
      },
      {
        subject: MULTIPLE_STRINGS_SET[2],
        matchRanges: [[1, 3]],
      }
    ]);
  });

  it('correctly matches multiple strings by a set of prefixes', () => {
    const matcher = new FuzzyMatcher(MULTIPLE_STRINGS_SET);

    expect(matcher.match('blaw')).toEqual([
      {
        subject: MULTIPLE_STRINGS_SET[1],
        matchRanges: [[0, 3], [9, 10]],
      },
      {
        subject: MULTIPLE_STRINGS_SET[2],
        matchRanges: [[0, 3], [9, 10]],
      }
    ]);
  });


  it('returns the matches alphabetically sorted', () => {
    const matcher = new FuzzyMatcher(MULTIPLE_STRINGS_SET);

    expect(matcher.match('a')).toEqual([
      {
        subject: MULTIPLE_STRINGS_SET[1],
        matchRanges: [[2, 3]],
      },
      {
        subject: MULTIPLE_STRINGS_SET[2],
        matchRanges: [[2, 3]],
      },
      {
        subject: MULTIPLE_STRINGS_SET[0],
        matchRanges: [[5, 6]],
      },
    ]);
  });

  it('treats substring-based matches as preferred to prefix-based', () => {
    const stringSet = ['foo bar fb'];
    const matcher = new FuzzyMatcher(stringSet);

    /**
     * Even though both a prefix-based match and a substring-based match exist
     * for 'foo bar fb' when matching it against 'fb', substring matches
     * are preferred to prefix matches.
     */
    expect(matcher.match('fb')).toEqual([{
      subject: stringSet[0],
      matchRanges: [[8, 10]],
    }]);
  });

  it('correctly matches "set ticket priority to p0" to "setp0"', () => {
    const stringSet = ['Set ticket priority to P0'];
    const matcher = new FuzzyMatcher(stringSet);

    expect(matcher.match('setp0')).toEqual([{
      subject: stringSet[0],
      matchRanges: [[0, 3], [23, 25]],
    }]);
  });

  it('does not match "set ticket priority to p0" to "SST"', () => {
    const stringSet = ['Set ticket priority to P0'];
    const matcher = new FuzzyMatcher(stringSet);

    expect(matcher.match('SST')).toEqual([]);
  });

  it('correctly matches "set ticket priority to p0" to "STT"', () => {
    const stringSet = ['Set ticket priority to P0'];
    const matcher = new FuzzyMatcher(stringSet);

    expect(matcher.match('STT')).toEqual([{
      subject: stringSet[0],
      matchRanges: [[0, 1], [4, 5], [20, 21]],
    }]);
  });

  it('respects the order of prefixes (VSCode style)', () => {
    const stringSet = ['setting X: set'];
    const matcher = new FuzzyMatcher(stringSet);

    expect(matcher.match('set sett')).toEqual([]);
    expect(matcher.match('sett set')).toEqual([{
      subject: stringSet[0],
      matchRanges: [[0, 4], [11, 14]],
    }]);
  });
});

describe('stringWithHighlightsFromMatch', () => {
  it('correctly converts single matched range in the middle', () => {
    const match: Match = {
      subject: 'foo xyz bar',
      matchRanges: [
        [4, 7],
      ],
    };

    const result = stringWithHighlightsFromMatch(match);
    expect(result).toEqual({
      value: 'foo xyz bar',
      parts: [
        {
          value: 'foo ',
          highlight: false,
        },
        {
          value: 'xyz',
          highlight: true,
        },
        {
          value: ' bar',
          highlight: false,
        }
      ]
    });
  });

  it('correctly converts single matched range in the beginning', () => {
    const match: Match = {
      subject: 'foo xyz bar',
      matchRanges: [
        [0, 3],
      ],
    };

    const result = stringWithHighlightsFromMatch(match);
    expect(result).toEqual({
      value: 'foo xyz bar',
      parts: [
        {
          value: 'foo',
          highlight: true,
        },
        {
          value: ' xyz bar',
          highlight: false,
        },
      ]
    });
  });

  it('correctly converts single matched range in the end', () => {
    const match: Match = {
      subject: 'foo xyz bar',
      matchRanges: [
        [8, 11],
      ],
    };

    const result = stringWithHighlightsFromMatch(match);
    expect(result).toEqual({
      value: 'foo xyz bar',
      parts: [
        {
          value: 'foo xyz ',
          highlight: false,
        },
        {
          value: 'bar',
          highlight: true,
        },
      ]
    });
  });

  it('correctly converts two matched ranged in the middle', () => {
    const match: Match = {
      subject: 'foo xyz bar',
      matchRanges: [
        [1, 3],
        [5, 7],
      ],
    };

    const result = stringWithHighlightsFromMatch(match);
    expect(result).toEqual({
      value: 'foo xyz bar',
      parts: [
        {
          value: 'f',
          highlight: false,
        },
        {
          value: 'oo',
          highlight: true,
        },
        {
          value: ' x',
          highlight: false,
        },
        {
          value: 'yz',
          highlight: true,
        },
        {
          value: ' bar',
          highlight: false,
        },
      ]
    });
  });

  it('correcrly converts two matched ranged in the beginning and end', () => {
    const match: Match = {
      subject: 'foo xyz bar',
      matchRanges: [
        [0, 2],
        [9, 11],
      ],
    };

    const result = stringWithHighlightsFromMatch(match);
    expect(result).toEqual({
      value: 'foo xyz bar',
      parts: [
        {
          value: 'fo',
          highlight: true,
        },
        {
          value: 'o xyz b',
          highlight: false,
        },
        {
          value: 'ar',
          highlight: true,
        },
      ]
    });
  });
});
