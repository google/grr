'use strict';

goog.provide('grrUi.flow.flowsListDirectiveTest');
goog.require('grrUi.flow.flowsListDirective.flattenFlowsList');
goog.require('grrUi.flow.flowsListDirective.toggleFlowExpansion');
goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('grr-flows-list directive', function() {

  describe('flattenFlowsList()', function() {
    var flattenFlowsList = grrUi.flow.flowsListDirective.flattenFlowsList;

    it('assigns zero depth when flows have no nested_flows', function() {
      var source = [
        {value: {foo: 1}},
        {value: {foo: 2}},
        {value: {foo: 3}}
      ];
      expect(flattenFlowsList(source)).toEqual([
        {value: {foo: 1}, depth: 0},
        {value: {foo: 2}, depth: 0},
        {value: {foo: 3}, depth: 0}
      ]);
    });

    it('assigns depths correctly for flows with nested_flows', function() {
      var source = [
        {
          value: {
            foo: 1
          }
        },
        {
          value: {
            foo: 2,
            nested_flows: [
              {
                value: {
                  foo: 21
                }
              },
              {
                value: {
                  foo: 22,
                  nested_flows: [
                    {
                      value: {
                        foo: 223
                      }
                    },
                    {
                      value: {
                        foo: 224
                      }
                    }
                  ]
                }
              }
            ]
          }
        },
        {
          foo: 3
        }
      ];

      expect(flattenFlowsList(source)).toEqual([
        {value: {foo: 1}, depth: 0},
        {value: {foo: 2}, depth: 0},
        {value: {foo: 21}, depth: 1},
        {value: {foo: 22}, depth: 1},
        {value: {foo: 223}, depth: 2},
        {value: {foo: 224}, depth: 2},
        {foo: 3, depth: 0}
      ]);
    });
  });

  describe('toggleFlowExpansion()', function() {
    var toggleFlowExpansion = grrUi.flow.flowsListDirective.toggleFlowExpansion;

    it('expands node with 2 children correctly', function() {
      var source = [
        {value: {foo: 2}, depth: 0, shown: true},
        {value: {foo: 21}, depth: 1, shown: false},
        {value: {foo: 22}, depth: 1, shown: false},
      ];
      expect(toggleFlowExpansion(source, 0)).toEqual([
        {value: {foo: 2}, depth: 0, shown: true, expanded: true},
        {value: {foo: 21}, depth: 1, shown: true},
        {value: {foo: 22}, depth: 1, shown: true},
      ]);
    });

    it('does not show adjacent items', function() {
      var source = [
        {value: {foo: 2}, depth: 0, shown: true},
        {value: {foo: 21}, depth: 1, shown: false},
        {value: {foo: 3}, depth: 0, shown: false},
      ];
      expect(toggleFlowExpansion(source, 0)).toEqual([
        {value: {foo: 2}, depth: 0, shown: true, expanded: true},
        {value: {foo: 21}, depth: 1, shown: true},
        {value: {foo: 3}, depth: 0, shown: false},
      ]);
    });

    it('collapses node with 2 children correctly', function() {
      var source = [
        {value: {foo: 2}, depth: 0, shown: true, expanded: true},
        {value: {foo: 21}, depth: 1, shown: true},
        {value: {foo: 22}, depth: 1, shown: true}
      ];
      expect(toggleFlowExpansion(source, 0)).toEqual([
        {value: {foo: 2}, depth: 0, shown: true, expanded: false},
        {value: {foo: 21}, depth: 1, shown: false},
        {value: {foo: 22}, depth: 1, shown: false}
      ]);
    });

    it('recursively shows expanded children', function() {
      var source = [
        {value: {foo: 2}, depth: 0, shown: true, expanded: false},
        {value: {foo: 21}, depth: 1, shown: false},
        {value: {foo: 22}, depth: 1, shown: false, expanded: true},
        {value: {foo: 223}, depth: 2, shown: false},
        {value: {foo: 224}, depth: 2, shown: false}
      ];
      expect(toggleFlowExpansion(source, 0)).toEqual([
        {value: {foo: 2}, depth: 0, shown: true, expanded: true},
        {value: {foo: 21}, depth: 1, shown: true},
        {value: {foo: 22}, depth: 1, shown: true, expanded: true},
        {value: {foo: 223}, depth: 2, shown: true},
        {value: {foo: 224}, depth: 2, shown: true},
      ]);
    });

    it('does not recursively show collapsed children', function() {
      var source = [
        {value: {foo: 2}, depth: 0, shown: true, expanded: false},
        {value: {foo: 21}, depth: 1, shown: false},
        {value: {foo: 22}, depth: 1, shown: false, expanded: false},
        {value: {foo: 223}, depth: 2, shown: false},
        {value: {foo: 224}, depth: 2, shown: false}
      ];
      expect(toggleFlowExpansion(source, 0)).toEqual([
        {value: {foo: 2}, depth: 0, shown: true, expanded: true},
        {value: {foo: 21}, depth: 1, shown: true},
        {value: {foo: 22}, depth: 1, shown: true, expanded: false},
        {value: {foo: 223}, depth: 2, shown: false},
        {value: {foo: 224}, depth: 2, shown: false},
      ]);
    });
  });

  // TODO(user): implement better way of testing directives that use
  // grr-infinite-table and grr-api-items-provider and test the directive
  // itself, not just the basic logic functions.
});
