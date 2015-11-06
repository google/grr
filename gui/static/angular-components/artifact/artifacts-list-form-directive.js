'use strict';

goog.provide('grrUi.artifact.artifactsListFormDirective.ArtifactsListFormController');
goog.provide('grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective');


goog.scope(function() {

/**
 * Controller for ArtifactsListFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.artifact.artifactsListFormDirective.ArtifactsListFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Array<Object>} */
  this.descriptorsList = [];

  /** @export {Object<string, Object>} */
  this.descriptors;

  /** @export {string} */
  this.descriptorsError;

  /** @export {Object} */
  this.selectedName;

  /** @export {Array<string>} */
  this.platforms = ['', 'Darwin', 'Linux', 'Windows'];

  /** @export {string} */
  this.selectedPlatform = '';

  /** @export {string} */
  this.search = '';

  /** @export {Function} Bound function to be used as a filter. */
  this.searchFilterRef = this.searchFilter.bind(this);

  /** @export {Function} Bound function to be used as a filter. */
  this.platformFilterRef = this.platformFilter.bind(this);

  this.grrApiService_.get('/artifacts').then(
      this.onArtifactsResponse_.bind(this),
      this.onArtifactsRequestFailure_.bind(this));

  this.scope_.$watch('controller.descriptors',
                     this.onDescriptorsOrValueChange_.bind(this));
  this.scope_.$watchCollection('value',
                               this.onDescriptorsOrValueChange_.bind(this));
};
var ArtifactsListFormController = grrUi.artifact.artifactsListFormDirective
    .ArtifactsListFormController;


/**
 * Filters artifacts by search string (case-insenstive).
 *
 * @param {!Object} descriptor Artifact descriptor to check.
 * @return {boolean} True if artifacts's name matches current search
 *     string, false otherwise.
 * @export
 */
ArtifactsListFormController.prototype.searchFilter = function(descriptor) {
  return !this.search ||
      descriptor.value.artifact.value.name.value
      .toLowerCase().indexOf(this.search.toLowerCase()) != -1;
};

/**
 * Filters artifacts by platform.
 *
 * @param {!Object} descriptor Artifact descriptor to check.
 * @return {boolean} True if list of artifact's platforms contains
 *     currently selected platform, false otherwise.
 * @export
 */
ArtifactsListFormController.prototype.platformFilter = function(descriptor) {
  if (!this.selectedPlatform) {
    return true;
  }

  var checkOsList = function(osList) {
    for (var i in osList) {
      var os = osList[i];
      if (os.value == this.selectedPlatform) {
        return true;
      }
    }
    return false;
  }.bind(this);

  if (checkOsList(
          descriptor['value']['artifact']['value']['supported_os'] || [])) {
    return true;
  }

  var sourceList = descriptor['value']['artifact']['value']['sources'] || [];
  for (var index in sourceList) {
    var source = sourceList[index];
    if (checkOsList(source['value']['supported_os'] || [])) {
      return true;
    }
  }

  return false;
};

/**
 * Handles server's response with a list of artifacts.
 *
 * @param {Object} response
 * @private
 */
ArtifactsListFormController.prototype.onArtifactsResponse_ = function(
    response) {
  this.descriptors = {};
  angular.forEach(response['data']['items'], function(descriptor) {
    this.descriptors[descriptor.value.artifact.value.name.value] = descriptor;
  }.bind(this));
};


/**
 * Handles errors that happen when requesting list of available artifacts.
 *
 * @param {Object} response
 * @private
 */
ArtifactsListFormController.prototype.onArtifactsRequestFailure_ = function(
    response) {
  this.descriptorsError = response.data['message'];
};

/**
 * Adds artifact with a given name to the list of selected names and
 * removes artifact descriptor with this name from selectable artifacts
 * list.
 *
 * @param {!Object} name Typed name of the artifact to add to the selected
 *     list.
 * @export
 */
ArtifactsListFormController.prototype.add = function(name) {
  var index = -1;
  for (var i = 0; i < this.scope_.value.length; ++i) {
    if (this.scope_.value[i]['value'] == name['value']) {
      index = i;
      break;
    }
  }
  if (index == -1) {
    this.scope_.value.push(name);
  }
};

/**
 * Removes given name from the list of selected artifacts names and
 * adds artifact descriptor with this name back to the list of selectable
 * artifacts.
 *
 * @param {!Object} name Typed name to be removed from the list of selected
 *     names.
 * @export
 */
ArtifactsListFormController.prototype.remove = function(name) {
  var index = -1;
  for (var i = 0; i < this.scope_.value.length; ++i) {
    if (this.scope_.value[i]['value'] == name['value']) {
      index = i;
      break;
    }
  }

  if (index != -1) {
    this.scope_.value.splice(index, 1);
  }
};

/**
 * Removes all names from the list of selected artifacts names.
 *
 * @export
 */
ArtifactsListFormController.prototype.clear = function() {
  angular.forEach(angular.copy(this.scope_.value), function(name) {
    this.remove(name);
  }.bind(this));
};

/**
 * Handles either controller.descriptors or value bindings updates.
 *
 * This function keeps controller.descriptorsList up to date.
 * controller.descriptorsList is used to show list of artifacts available for
 * selection. So whenever selection list changes we have to regenerate this
 * list.
 *
 * @private
 **/
ArtifactsListFormController.prototype.onDescriptorsOrValueChange_ = function() {
  if (angular.isDefined(this.descriptors) &&
      angular.isDefined(this.scope_.value)) {
    this.descriptorsList = [];
    angular.forEach(this.descriptors, function(descriptor, name) {
      var index = -1;
      for (var i = 0; i < this.scope_.value.length; ++i) {
        if (this.scope_.value[i]['value'] == name) {
          index = i;
          break;
        }
      }

      if (index == -1) {
        this.descriptorsList.push(descriptor);
      }
    }.bind(this));
  }
};

/**
 * OutputPluginDescriptorFormDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      descriptor: '=',
      value: '='
    },
    templateUrl: '/static/angular-components/artifact/' +
        'artifacts-list-form.html',
    controller: ArtifactsListFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
    .directive_name = 'grrArtifactsListForm';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.artifact.artifactsListFormDirective.ArtifactsListFormDirective
    .semantic_type = 'ArtifactName';


});  // goog.scope
