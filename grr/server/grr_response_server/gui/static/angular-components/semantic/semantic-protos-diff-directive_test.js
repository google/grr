'use strict';

goog.module('grrUi.semantic.semanticProtosDiffDirectiveTest');

const {diffAnnotate} = goog.require('grrUi.semantic.semanticProtosDiffDirective');

describe('grrSemanticProtosDiff directive', () => {
  describe('diffAnnotate()', () => {

    it('does nothing for 2 plain equal data structures', () => {
      const value = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFInteger',
            value: 42,
          },
        },
      };

      const originalValue = angular.copy(value);
      const newValue = angular.copy(value);
      diffAnnotate(originalValue, newValue);

      // Check that the values haven't changed.
      expect(originalValue).toEqual(value);
      expect(newValue).toEqual(value);
    });

    it('marks changed primitive attribute as changed', () => {
      const originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      };
      const newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'bar',
          },
        },
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
            _diff: 'changed',
          },
        },
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'bar',
            _diff: 'changed',
          },
        },
      });
    });

    it('marks primitive attribute as changed on type change', () => {
      const originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      };
      const newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'ClientURN',
            value: 'foo',
          },
        },
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
            _diff: 'changed',
          },
        },
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'ClientURN',
            value: 'foo',
            _diff: 'changed',
          },
        },
      });
    });

    it('marks added primitive attribute as added', () => {
      const originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      };
      const newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
          },
        },
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
            _diff: 'added',
          },
        },
      });
    });

    it('marks removed primitive attribute as removed', () => {
      const originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
          },
        },
      };
      const newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
            _diff: 'removed',
          },
        },
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
        },
      });
    });

    it('marks added and removed primitive attributes in the same value', () => {
      const originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
          },
        },
      };
      const newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          c: {
            type: 'RDFString',
            value: 'aha',
          },
        },
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          b: {
            type: 'RDFString',
            value: 'bar',
            _diff: 'removed',
          },
        },
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          },
          c: {
            type: 'RDFString',
            value: 'aha',
            _diff: 'added',
          },
        },
      });
    });

    it('marks primitive item added to a list as added', () => {
      const originalValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];
      const newValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'bar',
        },
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
        },
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'added',
        },
      ]);
    });

    it('marks primitive item removed from a list as removed', () => {
      const originalValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'bar',
        },
      ];
      const newValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'removed',
        },
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
        },
      ]);
    });

    it('marks changed list item as added and removed', () => {
      const originalValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];
      const newValue = [
        {
          type: 'RDFString',
          value: 'bar',
        },
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
          _diff: 'removed',
        },
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'added',
        },
      ]);
    });

    it('treats lists as unchanged if the order of items changed', () => {
      const originalValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'bar',
        },

      ];
      const savedOriginalValue = angular.copy(originalValue);

      const newValue = [
        {
          type: 'RDFString',
          value: 'bar',
        },
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];
      const savedNewValue = angular.copy(newValue);

      diffAnnotate(originalValue, newValue);

      // Ensure no '_diff' annotations were added.
      expect(originalValue).toEqual(savedOriginalValue);
      expect(newValue).toEqual(savedNewValue);
    });

    it('treats lists as unchanged if duplicate items were added', () => {
      const originalValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];
      const savedOriginalValue = angular.copy(originalValue);

      const newValue = [
        {
          type: 'RDFString',
          value: 'foo',
        },
        {
          type: 'RDFString',
          value: 'foo',
        },
      ];
      const savedNewValue = angular.copy(newValue);

      diffAnnotate(originalValue, newValue);

      // Ensure no '_diff' annotations were added.
      expect(originalValue).toEqual(savedOriginalValue);
      expect(newValue).toEqual(savedNewValue);
    });
  });
});


exports = {};
