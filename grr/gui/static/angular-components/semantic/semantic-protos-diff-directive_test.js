'use strict';

goog.require('grrUi.semantic.semanticProtosDiffDirective.diffAnnotate');

describe('grrSemanticProtosDiff directive', function() {

  describe('diffAnnotate()', function() {
    var diffAnnotate = grrUi.semantic.semanticProtosDiffDirective.diffAnnotate;

    it('does nothing for 2 plain equal data structures', function() {
      var value = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          },
          b: {
            type: 'RDFInteger',
            value: 42
          }
        }
      };

      var originalValue = angular.copy(value);
      var newValue = angular.copy(value);
      diffAnnotate(originalValue, newValue);

      // Check that the values haven't changed.
      expect(originalValue).toEqual(value);
      expect(newValue).toEqual(value);
    });

    it('marks changed primitive attribute as changed', function() {
      var originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          }
        }
      };
      var newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'bar'
          }
        }
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
            _diff: 'changed'
          }
        }
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'bar',
            _diff: 'changed'
          }
        }
      });
    });

    it('marks primitive attribute as changed on type change', function() {
      var originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          }
        }
      };
      var newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'ClientURN',
            value: 'foo'
          }
        }
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
            _diff: 'changed'
          }
        }
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'ClientURN',
            value: 'foo',
            _diff: 'changed'
          }
        }
      });
    });

    it('marks added primitive attribute as added', function() {
      var originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          }
        }
      };
      var newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          },
          b: {
            type: 'RDFString',
            value: 'bar'
          }
        }
      };

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          }
        }
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
            _diff: 'added'
          }
        }
      });
    });

    it('marks removed primitive attribute as removed', function() {
      var originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          },
          b: {
            type: 'RDFString',
            value: 'bar'
          }
        }
      };
      var newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          }
        }
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
            _diff: 'removed'
          }
        }
      });
      expect(newValue).toEqual({
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo',
          }
        }
      });
    });

    it('marks added and removed primitive attributes in the same value', function() {
      var originalValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          },
          b: {
            type: 'RDFString',
            value: 'bar'
          }
        }
      };
      var newValue = {
        type: 'Foo',
        value: {
          a: {
            type: 'RDFString',
            value: 'foo'
          },
          c: {
            type: 'RDFString',
            value: 'aha'
          }
        }
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
            _diff: 'removed'
          }
        }
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
            _diff: 'added'
          }
        }
      });
    });

    it('marks primitive item added to a list as added', function() {
      var originalValue = [
        {
          type: 'RDFString',
          value: 'foo'
        }
      ];
      var newValue = [
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'bar'
        }
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo'
        }
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'added'
        }
      ]);
    });

    it('marks primitive item removed from a list as removed', function() {
      var originalValue = [
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'bar'
        }
      ];
      var newValue = [
        {
          type: 'RDFString',
          value: 'foo'
        }
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'removed'
        }
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo'
        }
      ]);
    });

    it('marks changed list item as added and removed', function() {
      var originalValue = [
        {
          type: 'RDFString',
          value: 'foo'
        }
      ];
      var newValue = [
        {
          type: 'RDFString',
          value: 'bar'
        }
      ];

      diffAnnotate(originalValue, newValue);

      expect(originalValue).toEqual([
        {
          type: 'RDFString',
          value: 'foo',
          _diff: 'removed'
        }
      ]);
      expect(newValue).toEqual([
        {
          type: 'RDFString',
          value: 'bar',
          _diff: 'added'
        }
      ]);
    });

    it('treats lists as unchanged if the order of items changed', function() {
      var originalValue = [
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'bar'
        }

      ];
      var savedOriginalValue = angular.copy(originalValue);

      var newValue = [
        {
          type: 'RDFString',
          value: 'bar'
        },
        {
          type: 'RDFString',
          value: 'foo'
        },
      ];
      var savedNewValue = angular.copy(newValue);

      diffAnnotate(originalValue, newValue);

      // Ensure no '_diff' annotations were added.
      expect(originalValue).toEqual(savedOriginalValue);
      expect(newValue).toEqual(savedNewValue);
    });

    it('treats lists as unchanged if duplicate items were added', function() {
      var originalValue = [
        {
          type: 'RDFString',
          value: 'foo'
        }
      ];
      var savedOriginalValue = angular.copy(originalValue);

      var newValue = [
        {
          type: 'RDFString',
          value: 'foo'
        },
        {
          type: 'RDFString',
          value: 'foo'
        }
      ];
      var savedNewValue = angular.copy(newValue);

      diffAnnotate(originalValue, newValue);

      // Ensure no '_diff' annotations were added.
      expect(originalValue).toEqual(savedOriginalValue);
      expect(newValue).toEqual(savedNewValue);
    });
  });
});
