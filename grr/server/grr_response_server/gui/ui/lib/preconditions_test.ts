import {initTestEnvironment} from '@app/testing';

import {assertKeyNonNull, assertKeyTruthy, assertNonNull, assertTruthy, PreconditionError} from './preconditions';

initTestEnvironment();

describe('assertNonNull', () => {
  it('throws if value is null', () => {
    expect(() => {
      assertNonNull(null);
    }).toThrowError(PreconditionError);
  });

  it('throws if value is undefined', () => {
    expect(() => {
      assertNonNull(undefined);
    }).toThrowError(PreconditionError);
  });

  it('does not throw for falsey values', () => {
    assertNonNull(0);
    assertNonNull(false);
    assertNonNull('');
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertNonNull(5);
    assertNonNull({});
    assertNonNull([]);
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });
});

describe('assertTruthy', () => {
  it('throws if value is null', () => {
    expect(() => {
      assertTruthy(null);
    }).toThrowError(PreconditionError);
  });

  it('throws if value is undefined', () => {
    expect(() => {
      assertTruthy(undefined);
    }).toThrowError(PreconditionError);
  });

  it('throws if value is falsy', () => {
    expect(() => {
      assertTruthy(0);
    }).toThrowError(PreconditionError);
    expect(() => {
      assertTruthy(false);
    }).toThrowError(PreconditionError);
    expect(() => {
      assertTruthy('');
    }).toThrowError(PreconditionError);
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertTruthy(5);
    assertTruthy({});
    assertTruthy([]);
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });
});

interface TestObject {
  a?: string;
  b: boolean;
}

describe('assertKeyNonNull', () => {
  it('throws if value is null', () => {
    expect(() => {
      assertKeyNonNull({a: null, b: true}, 'a');
    }).toThrowError(PreconditionError);
  });

  it('throws if value is undefined', () => {
    expect(() => {
      assertKeyNonNull({a: undefined, b: true}, 'a');
    }).toThrowError(PreconditionError);
    expect(() => {
      assertKeyNonNull({b: true} as TestObject, 'a');
    }).toThrowError(PreconditionError);
  });

  it('does not throw for falsey values', () => {
    assertKeyNonNull({a: 0}, 'a');
    assertKeyNonNull({a: false}, 'a');
    assertKeyNonNull({a: ''}, 'a');
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertKeyNonNull({a: 5}, 'a');
    assertKeyNonNull({a: {}}, 'a');
    assertKeyNonNull({a: []}, 'a');
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });
});

describe('assertKeyTruthy', () => {
  it('throws if value is null', () => {
    expect(() => {
      assertKeyTruthy({a: null, b: true}, 'a');
    }).toThrowError(PreconditionError);
  });

  it('throws if value is undefined', () => {
    expect(() => {
      assertKeyTruthy({a: undefined, b: true}, 'a');
    }).toThrowError(PreconditionError);
  });

  it('throws if value is falsy', () => {
    expect(() => {
      assertKeyTruthy({a: 0, b: true}, 'a');
    }).toThrowError(PreconditionError);
    expect(() => {
      assertKeyTruthy({a: false, b: true}, 'a');
    }).toThrowError(PreconditionError);
    expect(() => {
      assertKeyTruthy({a: '', b: true}, 'a');
    }).toThrowError(PreconditionError);
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertKeyTruthy({a: 5, b: false}, 'a');
    assertKeyTruthy({a: {}, b: false}, 'a');
    assertKeyTruthy({a: [], b: false}, 'a');
    expect(true).toBeTruthy();  // Have at least one expect() to remove warning.
  });
});
