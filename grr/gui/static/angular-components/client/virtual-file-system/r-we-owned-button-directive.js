'use strict';

goog.module('grrUi.client.virtualFileSystem.rWeOwnedButtonDirective');
goog.module.declareLegacyNamespace();



var phrases = ["It is certain",
               "You were eaten by a Grue!",
               "中国 got you!!",
               "All your bases are belong to us!",
               "Maybe it was the Russians?",
               "It is decidedly so",
               "Without a doubt",
               "Yes - definitely",
               "You may rely on it",
               "As I see it, yes",
               "Most likely",
               "Outlook good",
               "Signs point to yes",
               "Yes",
               "Reply hazy, try again",
               "Ask again later",
               "Better not tell you now",
               "Cannot predict now",
               "Concentrate and ask again",
               "Don't count on it",
               "My reply is no",
               "My sources say no",
               "Outlook not so good",
               "Very doubtful"];

/**
 * Controller for RWeOwnedButtonDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @ngInject
 */
const RWeOwnedButtonController = function(
    $scope, $uibModal) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @type {string} */
  this.phrase;
};


/**
 * Handles mouse clicks on itself.
 *
 * @export
 */
RWeOwnedButtonController.prototype.onClick = function() {
  var randomIndex = Math.floor(Math.random() * phrases.length);
  this.scope_.phrase = phrases[randomIndex];

  this.uibModal_.open({
    templateUrl: '/static/angular-components/client/virtual-file-system/' +
        'r-we-owned-button-modal.html',
    scope: this.scope_
  });
};


/**
 * RWeOwnedButtonDirective renders a button that shows a dialog that tells
 * us whether we are owned or not.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.RWeOwnedButtonDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/virtual-file-system/r-we-owned-button.html',
    controller: RWeOwnedButtonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.RWeOwnedButtonDirective.directive_name = 'grrRWeOwnedButton';
