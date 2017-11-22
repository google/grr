'use strict';

goog.require('grrUi.forms.utils.valueHasErrors');

describe('forms utils', function() {

  describe('valueHasErrors', function() {
    var valueHasErrors = grrUi.forms.utils.valueHasErrors;

    it('returns false for a primitive value without errors', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: 'blah'
      })).toBe(false);
    });

    it('returns true for a primitive value with an error', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: 'blah',
        validationError: 'Oh no!'
      })).toBe(true);
    });

    it('returns false for a value with a struct field without errors', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: {
            type: 'RDFInteger',
            value: 42
          }
        }
      })).toBe(false);
    });

    it('returns true for a value with a struct field with an error', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: {
            type: 'RDFInteger',
            value: 42,
            validationError: 'Oh no!'
          }
        }
      })).toBe(true);
    });

    it('returns false for a value with an array field without errors', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: [
            {
              type: 'RDFInteger',
              value: 42
            }
          ]
        }
      })).toBe(false);
    });

    it('returns true for a value with an array field with an error', function() {
      expect(valueHasErrors({
        type: 'RDFString',
        value: {
          foo: [
            {
              type: 'RDFInteger',
              value: 42,
              validationError: 'Oh no!'
            }
          ]
        }
      })).toBe(true);
    });
  });

});
