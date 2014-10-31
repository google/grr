'use strict';

goog.provide('grrUi.hunt.huntLogDirective.HuntLogDirective');

goog.scope(function() {


/**
 * Marks even groups of neighboring records with same client IDs as
 * highlighted.
 * Fills short_urn attribute of every item with a last component of
 * a full item's URN.
 *
 * @param {Array} items Array of log items.
 * @private
 */
grrUi.hunt.huntLogDirective.transformItems_ = function(items) {
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
      huntUrn: '@'
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/hunt/hunt-log.html',
    link: function(scope, element) {
      scope.$watch('huntUrn', function() {
        scope.logsUrn = scope.huntUrn + '/Logs';
      });

      scope.transformItems = grrUi.hunt.huntLogDirective.transformItems_;
    }
  };
};


/**
 * Directive's name in Angular.
 */
grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name = 'grrHuntLog';

});  // goog.scope
