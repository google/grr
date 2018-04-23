'use strict';

goog.module('grrUi.forms.extFlagsTroggling');
goog.module.declareLegacyNamespace();


const {Flag} = goog.require('grrUi.client.extFlags');
const {TroggleState} = goog.require('grrUi.core.troggleDirective');


class TroggableFlag {
  /**
   * @param {!TroggableFlags} owner
   * @param {!Flag} flag
   */
  constructor(owner, flag) {
    /** @type {!TroggableFlags} */
    this.owner = owner;

    /** @type {string} */
    this.name = flag.name;
    /** @type {string} */
    this.identifier = flag.identifier;
    /** @type {number} */
    this.mask = flag.mask;
    /** @type {string} */
    this.description = flag.description;
  }

  /**
   * @return {!TroggleState}
   */
  get state() {
    const bitsSet = this.owner.bitsSet;
    const bitsUnset = this.owner.bitsUnset;

    if ((this.mask & bitsSet & bitsUnset) !== 0) {
      throw new Error(`${this.name} required to be both set and unset`);
    }
    if ((this.mask & bitsSet) !== 0) {
      return TroggleState.SET;
    }
    if ((this.mask & bitsUnset) !== 0) {
      return TroggleState.UNSET;
    }
    return TroggleState.VOID;
  }

  /**
   * @param {!TroggleState} value
   */
  set state(value) {
    switch (value) {
      case TroggleState.SET:
        this.owner.bitsSet |= this.mask;
        this.owner.bitsUnset &= ~this.mask;
        break;
      case TroggleState.UNSET:
        this.owner.bitsSet &= ~this.mask;
        this.owner.bitsUnset |= this.mask;
        break;
      case TroggleState.VOID:
        this.owner.bitsSet &= ~this.mask;
        this.owner.bitsUnset &= ~this.mask;
        break;
      default:
        throw new Error(`unexpected state value: ${value}`);
    }
  }
}

class TroggableFlags {
  /**
   * @param {!Array<!Flag>} flags
   */
  constructor(flags) {
    /** @type {number} */
    this.bitsSet = 0;
    /** @type {number} */
    this.bitsUnset = 0;

    /** @type {!Array<!TroggableFlag>} */
    this.children = [];
    for (const flag of flags) {
      this.children.push(new TroggableFlag(this, flag));
    }
  }
}


exports.TroggableFlag = TroggableFlag;
exports.TroggableFlags = TroggableFlags;
