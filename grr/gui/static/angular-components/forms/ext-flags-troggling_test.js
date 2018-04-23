'use strict';

goog.module('grrUi.forms.extFlagsTrogglingTest');
goog.module.declareLegacyNamespace();


const {TroggableFlags} = goog.require('grrUi.forms.extFlagsTroggling');
const {TroggleState} = goog.require('grrUi.core.troggleDirective');


describe('TroggableFlags', () => {

  let flags;

  beforeEach(() => {
    flags = new TroggableFlags([
      {
        name: 'FOO',
        identifier: 'foo',
        mask: 0b001,
        description: 'foo',
      },
      {
        name: 'BAR',
        identifier: 'bar',
        mask: 0b010,
        description: 'bar',
      },
      {
        name: 'BAZ',
        identifier: 'baz',
        mask: 0b100,
        description: 'baz',
      },
    ]);
  });

  it('should update itself if children state changes', () => {
    flags.children[1].state = TroggleState.SET;
    expect(flags.bitsSet).toBe(0b010);

    flags.children[0].state = TroggleState.SET;
    expect(flags.bitsSet).toBe(0b011);

    flags.children[2].state = TroggleState.UNSET;
    expect(flags.bitsUnset).toBe(0b100);
  });

  it('should update children on bits change', () => {
    flags.bitsSet = 0b000;
    flags.bitsUnset = 0b000;

    for (const flag of flags.children) {
      expect(flag.state).toBe(TroggleState.VOID);
    }

    flags.bitsSet = 0b100;
    expect(flags.children[2].state).toBe(TroggleState.SET);
    expect(flags.children[0].state).toBe(TroggleState.VOID);

    flags.bitsSet = 0b101;
    expect(flags.children[2].state).toBe(TroggleState.SET);
    expect(flags.children[2].state).toBe(TroggleState.SET);

    flags.bitsUnset = 0b010;
    expect(flags.children[1].state).toBe(TroggleState.UNSET);
  });

  it('should throw if conflicting masks are set', () => {
    flags.bitsSet = 0b110;
    flags.bitsUnset = 0b010;

    expect(() => flags.children[1].state).toThrow();
  });

});
