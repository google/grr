import {initTestEnvironment} from '../testing';

import {
  assertEnum,
  assertKeyNonNull,
  assertKeyTruthy,
  assertNonNull,
  assertNumber,
  assertTruthy,
  isEnum,
  PreconditionError,
} from './preconditions';

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
    // TypeScript's unreachable code detection has a bug with `false` < v4.0.
    // See: https://github.com/microsoft/TypeScript/issues/40017
    assertNonNull(false as boolean);
    assertNonNull('');
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertNonNull(5);
    assertNonNull({});
    assertNonNull([]);
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
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
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertTruthy(5);
    assertTruthy({});
    assertTruthy([]);
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
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
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertKeyNonNull({a: 5}, 'a');
    assertKeyNonNull({a: {}}, 'a');
    assertKeyNonNull({a: []}, 'a');
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
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
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });

  it('does not throw for truthy values', () => {
    assertKeyTruthy({a: 5, b: false}, 'a');
    assertKeyTruthy({a: {}, b: false}, 'a');
    assertKeyTruthy({a: [], b: false}, 'a');
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });
});

enum TestEnum {
  FOO_KEY = 'FOO',
  BAR = 'BAR',
}

describe('isEnum', () => {
  it('returns true if string is in enum', () => {
    expect(isEnum('FOO', TestEnum)).toBeTrue();
    expect(isEnum('BAR', TestEnum)).toBeTrue();
  });

  it('returns false if string is not in enum', () => {
    expect(isEnum('foo', TestEnum)).toBeFalse();
    expect(isEnum('FOO_KEY', TestEnum)).toBeFalse();
    expect(isEnum('', TestEnum)).toBeFalse();
  });
});

describe('assertEnum', () => {
  it('throws if string is not in enum', () => {
    expect(() => {
      assertEnum('foo', TestEnum);
    }).toThrowError(PreconditionError);
    expect(() => {
      assertEnum('FOO_KEY', TestEnum);
    }).toThrowError(PreconditionError);
    expect(() => {
      assertEnum('', TestEnum);
    }).toThrowError(PreconditionError);
  });

  it('does not throw if string is in enum', () => {
    assertEnum('FOO', TestEnum);
    assertEnum('BAR', TestEnum);
    expect(true).toBeTruthy(); // Have at least one expect() to remove warning.
  });
});

describe('assertNumber', () => {
  it('throws if string cannot be converted', () => {
    expect(() => {
      assertNumber('foo');
    }).toThrowError(PreconditionError);
  });

  it('returns number value when the field is number', () => {
    assertNumber(100.0);
    expect(true).toBeTruthy();
  });
});
