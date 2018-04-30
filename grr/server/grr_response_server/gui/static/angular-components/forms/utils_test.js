'use strict';

goog.module('grrUi.forms.utilsTest');

const {valueHasErrors} = goog.require('grrUi.forms.utils');

describe('forms utils', () => {
  describe('valueHasErrors', () => {

    it('returns false for a primitive value without errors', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: 'blah',
      })).toBe(false);
    });

    it('returns true for a primitive value with an error', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: 'blah',
        validationError: 'Oh no!',
      })).toBe(true);
    });

    it('returns false for a value with a struct field without errors', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: {
            type: 'RDFInteger',
            value: 42,
          },
        },
      })).toBe(false);
    });

    it('returns true for a value with a struct field with an error', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: {
            type: 'RDFInteger',
            value: 42,
            validationError: 'Oh no!',
          },
        },
      })).toBe(true);
    });

    it('returns false for a value with an array field without errors', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: [
            {
              type: 'RDFInteger',
              value: 42,
            },
          ],
        },
      })).toBe(false);
    });

    it('returns true for a value with an array field with an error', () => {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: [
            {
              type: 'RDFInteger',
              value: 42,
              validationError: 'Oh no!',
            },
          ],
        },
      })).toBe(true);
    });
  });
});


exports = {};
