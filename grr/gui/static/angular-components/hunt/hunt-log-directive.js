'use strict';

goog.provide('grrUi.hunt.huntLogDirective.HuntLogController');
goog.provide('grrUi.hunt.huntLogDirective.HuntLogDirective');

goog.scope(function() {



/**
 * Controller for HuntLogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntLogDirective.HuntLogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};

var HuntLogController =
    grrUi.hunt.huntLogDirective.HuntLogController;


/**
 * Handles huntUrn attribute changes.
 * @export
 */
HuntLogController.prototype.onHuntUrnChange = function() {
  if (angular.isDefined(this.scope_.huntUrn)) {
    var huntUrnComponents = this.scope_.huntUrn.split('/');
    var huntId = huntUrnComponents[huntUrnComponents.length - 1];
    this.logsUrl = 'hunts/' + huntId + '/log';
  }
};


/**
 * Marks even groups of neighboring records with same client IDs as
 * highlighted.
 * Fills short_urn attribute of every item with a last component of
 * a full item's URN.
 *
 * @param {!Array<Object>} items Array of log items.
 * @return {!Array<Object>} Transformed items.
 * @export
 * @suppress {missingProperties} as we're working with JSON data.
 */
HuntLogController.prototype.transformItems = function(items) {
  var clientId = null;
  var highlighted = false;
  for (var i = 0; i < items.length; ++i) {
    var item = items[i];

    // Truncate full URN to just the last component.
    if (item.value.urn !== undefined) {
      var components = item.value.urn.value.split('/');
      if (components.length > 0) {
        item.shortUrn = components[components.length - 1];
      }
    }

    // Highlight rows with a similar client id with the same
    // highlight. Also show the client id only once per group
    // of messages.
    var itemClientId = null;
    if (item.value.client_id !== undefined) {
      itemClientId = item.value.client_id.value;
    }

    if (clientId !== itemClientId) {
      clientId = itemClientId;
      highlighted = !highlighted;
    } else {
      item.value.client_id = null;
    }

    item.highlighted = highlighted;
  }

  return items;
};



/**
 * Directive for displaying log records of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntLogDirective.HuntLogDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-log.html',
    controller: HuntLogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name = 'grrHuntLog';

});  // goog.scope
