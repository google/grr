goog.module('grrUi.semantic.osqueryTableDirective');
goog.module.declareLegacyNamespace();


/**
 * A table column.
 *
 * For now this is just a string. In the future this will also contain column
 * type which can be used to improve things like formatting.
 *
 * @typedef {string}
 */
let Column;

/**
 * Parses a typed JSON representation into a column.
 *
 * @param {!Object} column A typed JSON object representing the column to parse.
 * @return {!Column}
 */
const parseColumn = (column) => {
  return column['value']['name']['value'];
};


/**
 * A table row (list of values).
 *
 * @typedef {!Array<string>}
 */
let Row;

/**
 * Parses a typed JSON representation into a row.
 *
 * @param {!Object} row A typed JSON object representing the row to parse.
 * @return {!Row}
 */
const parseRow = (row) => {
  return row['value']['values'].map(value => value['value']);
};


/**
 * A controller for osquery output tables.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const OsqueryTableController = function($scope) {
  /**
   * @type {string}
   */
  this.query;

  /**
   * @type {!Array<!Column>}
   */
  this.columns;

  /**
   * @type {!Array<!Row>}
   */
  this.rows;

  $scope.$watch('::value', (table) => this.onValueChange_(table));
};

/**
 * Handles changes of the value.
 *
 * @param {!Object} table A typed object corresponding to the osquery table.
 * @private
 */
OsqueryTableController.prototype.onValueChange_ = function(table) {
  if (table === undefined) {
    return;
  }

  this.query = table['value']['query']['value'];
  this.columns = table['value']['header']['value']['columns'].map(parseColumn);
  this.rows = table['value']['rows'].map(parseRow);
};

/**
 * A directive that displays osquery output tables.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.OsqueryTableDirective = function() {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/osquery-table.html',
    controller: OsqueryTableController,
    controllerAs: 'controller',
  };
};

/**
 * An Angular name of the directive .
 *
 * @const {string}
 */
exports.OsqueryTableDirective.directive_name = 'grrOsqueryTable';

/**
 * Semantic type supported by the directive.
 *
 * @const {string}
 */
exports.OsqueryTableDirective.semantic_type = 'OsqueryTable';
