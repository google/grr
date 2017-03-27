/* Copyright 2011 Google Inc. All Rights Reserved.
*/

/**
 * @fileoverview Base functions for GRR frontend.
 */

/**
 * Namespace for all GRR javascript code.
 */
var grr = window.grr || {};

/**
 *  Flag to indicate if debugging messages go to the console.
 */
grr.debug = false;

/**
 * Wrapper for console.log in case it does not exist.
 */
grr.log = function() {
  var published_arguments = arguments;
  /* Suppress debugging. */
  if (grr.debug) {
    try {
      console.log(Array.prototype.slice.call(arguments));
    } catch (e) {}
  }
};

/**
 * Initializer for the grr object. Clears all message queues and state.
 */
grr.init = function() {
  /**
   * This is the grr publisher/subscriber queue.
   */
  if (!grr.queue_) {
    grr.queue_ = {};
  }

  grr.subscribe('grr_messages', function(serverError) {
    if (grr.angularInjector) {
      var $rootScope = grr.angularInjector.get('$rootScope');
      $rootScope.$broadcast('ServerError', serverError);
    }
  }, 'body');

  // TODO(user): get rid of GRR publish/subscribe queue.
  grr.subscribe('unauthorized', function(subject, message) {
    if (subject) {
      var grrAclDialogService =
          grr.angularInjector.get('grrAclDialogService');

      // TODO(user): get rid of this code as soon as we stop passing
      // information about objects by passing URNs and guessing the
      // object type.
      subject = subject.replace(/^aff4:\//, '');
      var components = subject.split('/');
      if (/^C\.[0-9a-fA-F]{16}$/.test(components[0])) {
        grrAclDialogService.openRequestClientApprovalDialog(
            components[0], message);
      } else if (components[0] == 'hunts') {
        grrAclDialogService.openRequestHuntApprovalDialog(
            components[1], message);
      } else if (components[0] == 'cron') {
        grrAclDialogService.openRequestCronJobApprovalDialog(
            components[1], message);
      } else {
        throw new Error('Can\'t determine type of resources.');
      }
    }
  }, 'body');

  /**
   * This holds timers for delayedSubscribe
   * @type {Object.<number>}
   */
  grr.timers = {};

  window.setInterval(function() {
    grr.publish('timer', 'timer');
  }, 500);
};

/**
 * Subscribes for a grr event.
 *
 * @param {string} name The name of the queue to subscribe to.
 * @param {Function} handle a function that will be called when an
 *                 event is published on that queue.
 * @param {string} domId of the widget which is subscribed to this event.
*/
grr.subscribe = function(name, handle, domId) {
  var queue_name = 'queue_' + name;
  var queue = grr.queue_[queue_name] || [];
  var new_queue = [];

  if (domId == null) {
    alert('Programming error: subscribed function must depend on a dom node.');
  }

  // Clean up the queue from events that no longer apply
  for (var i = 0; i < queue.length; i++) {
    var old_handler = queue[i];
    var activeDomId = old_handler.activeDomId;

    if ($('#' + activeDomId).length) {
      new_queue.push(old_handler);
    }
  }

  handle.activeDomId = domId;
  new_queue.push(handle);

  grr.queue_[queue_name] = new_queue;

  if (new_queue.length > 5) {
    //alert('Queue ' + queue_name + ' seems full');
  }
};

/**
 * Subscribes for a grr event with a timer.
 *
 * When an event is published on the queue we start a timer and only call the
 * handle after timer expiration. If another event is published to the queue
 * before the timer fires we cancel the first timer and start a new one. This is
 * mainly used for debouncing incremental search.
 *
 * @param {string} name The name of the queue to subscribe to.
 * @param {number} delay The delay for the timer (in secs).
 * @param {string} domId A unique ID to store the timer object.
 * @param {Function} handle a function that will be called when an
 *     event is published on that queue.
 */
grr.delayedSubscribe = function(name, delay, domId, handle) {
  grr.subscribe(name, function() {
    // These are the args that were published
    var published_arguments = arguments;

    // Cancel the previous timer.
    if (grr.timers['timer_' + domId]) {
      window.clearTimeout(grr.timers['timer_' + domId]);
    }

    // Set a future timer to call the handle with the
    // original_arguments. But this only happens if the
    grr.timers['timer_' + domId] = window.setTimeout(function() {
      if ($('#' + domId)) {
        handle.apply(this, published_arguments);
      } else {
        grr.timers['timer_' + domId] = undefined;
      }
    }, delay * 1000);
  }, 'body');
};


/**
 * Publish to a grr event.
 *
 * Note that event and data can be obtained from a standard JS event handler
 * (e.g. onclick).
 *
 * @param {string} name The name of the queue to publish to.
 * @param {string} value A value to publish.
 * @param {Event=} event an optional JS event object.
 * @param {Object=} data The data object passed in the event.
 */
grr.publish = function(name, value, event, data) {
  var queue_name = 'queue_' + name;
  var queue = grr.queue_[queue_name];

  grr.log('grr.publish', name, value, data);
  if (queue) {
    var new_queue = [];

    for (var i = 0; i < queue.length; i++) {
      var handler = queue[i];

      // Make sure the activeDomId still exits
      if ($('#' + handler.activeDomId).length) {
        queue[i](value, event, data);
        new_queue.push(handler);
      }
    }

    grr.queue_[queue_name] = new_queue;
  }
};


/**
 * This is the queue of ajax requests which are currently in flight. If another
 * query occurs for this same domId, it is canceled until the first request
 * returns. This makes it safe to fire off ajax requests based on events, since
 * there can be many requests in flight for the same element.
 *
 */
grr.inFlightQueue = {}; //TODO(user): kept for compatibility with legacy JS code. Remove later.


/**
 * Broadcasts an event on the Angular rootScope.
 * @param {string} eventName The event name
 * @param {Object} data The event data
 */
grr.broadcastAngularEvent = function(eventName, data){
  if (grr.angularInjector) {
    var $rootScope = grr.angularInjector.get('$rootScope');
    $rootScope.$broadcast(eventName, data);
  }
};

/**
 * Push an ajax request to the inflight queue so we can display the spinner icon
 * until this request has completed.
 * @param {string} element The key to use for this entry.
 * @param {Object} value The value to store in the queue.
 *
 */
grr.PushToAjaxQueue = function(element, value) {
  grr.inFlightQueue[element] = value;
  grr.broadcastAngularEvent('grrLoadingStartedEvent', element);
};

/**
 * Remove an ajax request from the inflight queue so we can stop displaying the
 * spinner icon.
 * @param {string} element The key to delete from the queue.
 *
 */
grr.RemoveFromAjaxQueue = function(element) {
  delete grr.inFlightQueue[element];
  grr.broadcastAngularEvent('grrLoadingFinishedEvent', element);
};

/**
 * Check if there is an outstanding ajax request in the inflight queue.
 * @param {string} element The key to retrieve from the queue.
 * @return {Object} The value stored in the queue for key <element>.
 */
grr.GetFromAjaxQueue = function(element) {
  return grr.inFlightQueue[element];
};


/**
  * Determine if a method is safe to add CSRF token to.
  * As per https://docs.djangoproject.com/en/1.4/ref/contrib/csrf/#using-csrf
  * @param {string} method Method the request uses.
  * @return {boolean} whether or not the method is safe from csrf.
**/
grr.csrfSafeMethod = function(method) {
  // these HTTP methods do not require CSRF protection.
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
};


/**
 * Helper function to retrieve the value of a cookie, in lieu of an extra
 * dependency on jquery.cookie.
 * @param {string} name The cookie we want the value for.
 * @return {string} value of the cookie.
 */
grr.getCookie = function(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};


/**
 * Pushes the state from the Javascript state dict to html tags.
 * @param {string} domId of the widget which will receive the state.
 * @param {Object} state The state to push.
 */
grr.pushState = function(domId, state) {
  keys = Object.keys(state);
  attrs = {};
  for (var i = 0; i < keys.length; i++) {
    attrs['state-' + keys[i]] = state[keys[i]];
  }
  $('#' + domId).attr(attrs);
};

/**
 * Namespace for the glob completer.
 */
grr.glob_completer = {};

/**
 * A filter function which matches the start of the completion list.
 *
 * @param {Array} completions the completion list
 * @param {string} term is the term to match.
 *
 * @return {Array} a list of matches.
 */
grr.glob_completer.filter = function(completions, term) {
  var matcher = new RegExp('^' + $.ui.autocomplete.escapeRegex(term), 'i');
  return $.grep(completions, function(value) {
    return matcher.test(value.label || value.value || value);
  });
};

/**
 * Build a completer on top of a text input.
 *
 * @param {string|Element} element is the DOM id of the text input field or the
 *     DOM element itself.
 * @param {Array} completions are possible completions for %% sequences.
 */
grr.glob_completer.Completer = function(element, completions) {
  if (angular.isString(element)) {
    element = $('#' + element);
  }
  element.bind('keydown', function(event) {
    if (event.keyCode === $.ui.keyCode.TAB &&
        $(this).data('ui-autocomplete').menu.active) {
      event.preventDefault();
    }
  }).autocomplete({
    minLength: 0,
    source: function(request, response) {
      var terms = request.term.split(/%%/);
      if (terms.length % 2) {
        response([]);
      } else {
        response(grr.glob_completer.filter(completions, terms.pop()));
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      var terms = this.value.split(/%%/);
      // remove the current input
      terms.pop();

      // add the selected item
      terms.push(ui.item.value);
      terms.push('');

      this.value = terms.join('%%');
      // Angular code has to be notificed of the change.
      $(this).change();
      return false;
    }
  }).wrap('<abbr title="Type %% to open a list of possible completions."/>');
};


/** Initialize the grr object */
grr.init();

/**
 *  Initialize Angular GRR app. AngularJS has no problems coexisting with
 *  existing set of GRR renderers.
 */
var grrUiApp = angular.module('grrUi', ['ngCookies',
                                        'grrUi.appController']);

grrUiApp.config(function($httpProvider, $interpolateProvider,
                         $rootScopeProvider) {
  // Set templating braces to be '{$' and '$}' to avoid conflicts with Django
  // templates.
  $interpolateProvider.startSymbol('{$');
  $interpolateProvider.endSymbol('$}');

  // Ensuring that Django plays nicely with Angular-initiated requests
  // (see http://www.daveoncode.com/2013/10/17/how-to-
  // make-angularjs-and-django-play-nice-together/).
  $httpProvider.defaults.headers.post[
    'Content-Type'] = 'application/x-www-form-urlencoded';

  // We use recursive data model generation when rendering forms. Therefore
  // have to increase the digestTtl limit to 50.
  $rootScopeProvider.digestTtl(50);
});

grrUiApp.run(function($injector, $http, $cookies, grrFirebaseService, grrReflectionService) {
  grr.angularInjector = $injector;

  // Ensure CSRF token is in place for Angular-initiated HTTP requests.
  $http.defaults.headers.post['X-CSRFToken'] = $cookies.get('csrftoken');
  $http.defaults.headers.delete = $http.defaults.headers.patch = {
    'X-CSRFToken': $cookies.get('csrftoken')
  };

  grrFirebaseService.setupIfNeeded();

  // Call reflection service as soon as possible in the app lifetime to cache
  // the values. "ACLToken" is picked up here as an arbitrary name.
  // grrReflectionService loads all RDFValues definitions on first request
  // and then caches them.
  grrReflectionService.getRDFValueDescriptor('ACLToken');
});


/**
 * TODO(user): Remove when dependency on jQuery-migrate is removed.
 */
jQuery.migrateMute = true;

/**
 * Hardcoding jsTree themes folder so that it works correctly when used
 * from a JS bundle file.
 */
$.jstree._themes = '/static/third-party/jstree/themes/';
