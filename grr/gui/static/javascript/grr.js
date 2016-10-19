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
 * All AJAX calls must be in POST for CSRF protection. This is here so when
 *  debugging its possible to switch to GET mode for easier debugging.
 */
grr.ajax_method = 'POST';

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
 *  Do we still need to install XSSI protection?
 */
grr.installXssiProtection = true;

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

  //Update the hash location from this message queue.
  grr.subscribe('hash_state', function(key, value) {
    if (value != undefined) {
      grr.hash[key] = value;
    } else {
      delete(grr.hash[key]);
    }
  }, 'body');

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
   * This is a global state object. The state is a collection of query
   * parameters which are passed to the server in each request.
   */
  if (!grr.state) {
    grr.state = {};
  }

  /**
   * This holds timers for delayedSubscribe
   * @type {Object.<number>}
   */
  grr.timers = {};

  /**
   * Installs global XSSI protection. This has to be done exactly once. It
   * basically patches the jQuery.ajax method to remove the XSSI preamble.
   */
  if (grr.installXssiProtection) {
    var json_converter = function(data) {
      if (typeof data !== 'string' || !data) {
        return null;
      }

      if (data.substring(0, 4) != ')]}\n') {
        return jQuery.error('JSON object not properly protected.');
      }

      return $.parseJSON(data.substring(4, data.length));
    };

    var test = function(data) {
      return window.String(data);
    };

    $.ajaxSetup({
      crossDomain: false,
      converters: {
        '* application': window.String,
        'application json': json_converter,
        'application javascript': json_converter,
        'text json': json_converter
      }
    });
    grr.installXssiProtection = false;
  }


  /* This is required to send the csrf token as per
   https://docs.djangoproject.com/en/1.4/ref/contrib/csrf/
  */
  var csrftoken = grr.getCookie('csrftoken');

  $(document).ajaxSend(function(event, xhr, settings) {
    // Officially crossdomain should be covered by ajaxSetup call, but that
    // appears to not apply to tree renderers, so belt and braces here.
    if (!grr.csrfSafeMethod(settings.type)) {
      xhr.setRequestHeader('X-CSRFToken', csrftoken);
    }
  });

  window.setInterval(function() {
    grr.publish('timer', 'timer');
  }, 500);

  /**
   * This object holds the current url location hash state.
   */
  grr.hash = grr.parseHashState();

  /* Initialize the reason from the hash. */
  grr.state.reason = grr.hash.reason;
};


/**
 * Create a new tree on the domId provided.
 *
 * @param {string} renderer The name of the RenderTree responsible for this
 *     tree.
 * @param {string} unique_id The id of the div element that will contain the
 *     tree.
 * @param {string=} opt_publishEvent The name of the GRR event queue where
 *     select events will be published. DEFAULT: "tree_select".
 * @param {Object=} opt_state An optional state object to pass to the
 *     server. DEFAULT: global state.
 * @param {Function=} opt_success_cb an optional function to handle ajax stream.
 * @return {Object} jQuery-wrapped tree.
 */
grr.grrTree = function(renderer, unique_id, opt_publishEvent, opt_state,
                       opt_success_cb) {
  var state = $.extend({}, grr.state, opt_state);
  var publishEvent = opt_publishEvent || 'tree_select';

  state.path = '/';
  state.reason = state.reason || grr.state.reason;
  state.client_id = state.client_id || grr.state.client_id;

  var tree = $('#' + unique_id);
  tree.html('');

  tree.jstree({
    'core' : {
      'data' : {
        'url' : 'render/RenderAjax/' + renderer,
        'type': grr.ajax_method,
        dataType: '*', // Let the server decide on the mime type.
        beforeSend: function(xhr) {
          grr.PushToAjaxQueue('#' + unique_id);
        },
        'data' : function(n) {
          var new_state = $.extend({}, state);

          if (n.li_attr) {
            new_state.path = '/' + this.get_path(n).join('/');
            new_state.id = n.li_attr.id;
          }

          return new_state;
        },
        'error': function(data, textStatus, jqXHR) {
          grr.RemoveFromAjaxQueue('#' + unique_id);
        },
        'success': function(data, textStatus, jqXHR) {
          grr.RemoveFromAjaxQueue('#' + unique_id);

          if (opt_success_cb) {
            opt_success_cb(data, textStatus, jqXHR);
          }
        }
      }
    }
  }).on('changed.jstree', function(e, data) {
    // This is needed so that when user clicks on an already opened node,
    // it gets refreshed.
    data.instance.refresh_node(data.node);
  });

  /* Bind the select event to the publish queue */
  tree.on('select_node.jstree', function(event, data) {
    var path = data.node.li_attr.path;
    var selected_id = data.node.li_attr.id;
    var update_hash = true;

    // Publish the full AFF4 path of the object the user clicked on.
    var root = (state.aff4_root || '/');
    var new_path = (root + path).replace(/\/+/, '/');

    grr.publish(publishEvent, new_path, selected_id, update_hash);

    // Selecting a node automatically opens it
    $(this).jstree('open_node', '#' + selected_id);
    return true;
  });

  /* Open the tree if the hash says to. */
  tree.on('loaded.jstree', function() {
    if (grr.hash.t) {
      grr.openTree(tree, grr.hash.t);
    }
  });

  /* Each node that is opened will update the hash */
  tree.on('select_node.jstree', function(e, data) {
    var selected_id = data.node.id;
    grr.broadcastAngularEvent('grrTreeSelectionChanged', selected_id);
  });

  /* We do not want jstree to cache the leafs when a tree is closed. */
  tree.on('close_node.jstree', function(e, data) {
    $('#' + data.node.id).children('ul').html('');
  });

  grr.subscribe('client_selection', function(message) {
    // Make a new one
    grr.grrTree(renderer, unique_id, opt_publishEvent, opt_state,
                opt_success_cb);
    grr.publish(publishEvent, '/');
  }, unique_id);

  return tree;
};


/**
 * This function recursively opens a tree to reveal a specified node. Node id
 * must be of the form path components encoded in hex separated by -.
 *
 * @param {Object} tree A jQuery selected object representing the tree.
 * @param {string} nodeId id for the node to open.
 **/
grr.openTree = function(tree, nodeId) {
  var parts = nodeId.split('-');
  var i = 1;

  var cb = function(i, prev_node) {
    var id_to_open = parts.slice(0, i + 1).join('-');
    var node = $('#' + id_to_open);

    if (node.length) {
      // There are more nodes to go, proceed recursively.
      if (parts[i + 1]) {
        tree.jstree('open_node', node, function() { cb(i + 1, node); },
            'no_hash');
      } else {
        // Ultimate node, when its done we want to select it
        tree.jstree('select_node', node, 'no_hash');
        grr.broadcastAngularEvent('grrTreeSelectionChanged', node.attr('id'));
      }
    } else if (prev_node) {
      // If node can't be found, finish by selecting previous successful one
      tree.jstree('select_node', prev_node, 'no_hash');
      grr.broadcastAngularEvent('grrTreeSelectionChanged', prev_node.attr('id'));
    }
  };

  cb(0, null);
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
 * Refreshes an element.

 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into
 *         the AJAX request (as query parameters).
*/
grr.refresh = function(domId, opt_state) {
  // Use global state by default
  var state = opt_state || grr.state;
  var renderer = $('#' + domId).data().renderer;

  if (renderer) {
    grr.layout(renderer, domId, state);
  }
};

/**
 * This is an implementation of a table widget for GRR.
 */
grr.table = {};

/**
 * Adjust the alternate colored rows in the table.
 *
 * @param {Object} jtable is a jqueried table node.
 */
grr.table.colorTable = function(jtable) {
  // Color the rows nicely.
  jtable.find('tr:even').addClass('even');
  jtable.find('tr:odd').addClass('odd');
};

/**
 * An event handler for scrolling.
 *
 * If we notice an uncovered "Loading ..." element appear within the view port,
 * we launch an ajax call to replace it with data.
 *
 * @param {string} renderer is the renderer which will be used to fill the ajax
 * call.
 *
 * @param {Object} tbody is the jqueried object corresponding to the tbody
 * element.
 *
 * @param {Object=} opt_state A data object which will be serialiased into the
 *     AJAX request (as query parameters).
 */
grr.table.scrollHandler = function(renderer, tbody, opt_state) {
  var loading = tbody.find('.table_loading');
  var bottom = tbody.scrollTop() + tbody[0].offsetHeight;
  var loading_id = loading.attr('id');
  var value = loading.attr('data');
  var depth = loading.attr('depth');
  var start_row = loading.attr('start_row');

  $('.table_loading', tbody).each(function() {
    loading_offset = $(this).offset();
    elem = document.elementFromPoint(
        loading_offset.left - $(window).scrollLeft() + 1,
        loading_offset.top - $(window).scrollTop() + 1);
    if ($(elem).hasClass('table_loading')) {
      // Prevent scrollHandler from being called again for this "Loading..."
      // row.
      $(elem).removeClass('table_loading');

      var next_row;
      if (start_row == undefined) {
        var previous_row_id = (tbody.find('tr[row_id]').last().attr('row_id') ||
            -1);
        next_row = parseInt(previous_row_id) + 1;
      } else {
        next_row = start_row;
      }
      var state = $.extend({start_row: next_row, value: value, depth: depth},
                           grr.state, opt_state);
      var filter = tbody.parent().find('th[filter]');
      var sort = tbody.parent().find('th[sort]');

      if (filter.length && filter.attr('filter')) {
        state.filter = filter.text() + ':' + filter.attr('filter');
      }

      if (sort.length && sort.attr('sort')) {
        state.sort = sort.text() + ':' + sort.attr('sort');
      }

      // Insert the new data after the table loading message, and wipe it.
      grr.update(renderer, loading_id, state,
        function(data) {
          // Make sure to insert this data only after its corresponding
          // loading placer.
          var table_loading;

          if (loading_id) {
            table_loading = tbody.find('#' + loading_id);
          } else {
            table_loading = tbody.find('.table_loading');
          }

          var loading_row = table_loading.parent('tr');

          // Prevent a possible race: a scroll event can fire here after
          // inserting the data, but before being able to remove the loading
          // row. We remove the loading td first to prevent this.
          loading_row.find('.table_loading').remove();

          loading_row.after(data);
          loading_row.remove();

          tbody.scroll();
        }, loading_id + previous_row_id);
    }
  });
};


/**
 * Create a new table on the specified domId.
 *
 * @param {string} renderer is the name of the renderer we use.
 * @param {string} domId is the id of the table element.
 * @param {string} unique is a unique id for this element.
 * @param {Object=} opt_state A data object which will be serialiased into the
 *     AJAX request (as query parameters).
 */
grr.table.newTable = function(renderer, domId, unique, opt_state) {
  var me = $('#' + domId);

  var rowHandler = function(event) {
    /* Find the next TR above the clicked point */
    var node = $(event.target).closest('tr');
    var row_id = node.attr('row_id');
    if (row_id) {
      // Clear all the selected rows
      $(this).find('tr').each(function() {
        $(this).removeClass('row_selected');
      });

      node.addClass('row_selected');

      // Publish the selected node
      grr.publish(event.data, node);
    }
    event.stopPropagation();
  };

  // Click handler.
  $('#' + unique).click('select_' + domId, rowHandler);
  $('#' + unique).dblclick('double_click_' + domId, rowHandler);

  $('#' + unique).on('refresh', function() {
    var selected_row = $('tr.row_selected', me).first();
    var selected_row_id = selected_row.attr('row_id');

    var tbody = $('tbody', me).first();
    var tbody_id = tbody.attr('id');
    grr.update(renderer, tbody_id, null, function(data) { /* on_success */
      $('#' + tbody_id, me).html(data);

      if (selected_row_id) {
        // If we can select previously selected row, select it.
        // Otherwise - select the first one.
        $('tr[row_id=' + selected_row_id + ']', me).each(function() {
          $(this).click();
        });
        if ($('tr.selected', me).length == 0) {
          $('tr', me).first().click();
        }
      }
    });
  });

  // Add search buttons for columns.
  me.find('th').each(function(i) {
    var jthis = $(this);
    if (jthis.attr('sortable')) {
      var image = $('<img src="/static/images/forward_enabled.jpg"' +
          'style="float: right">');
      jthis.append(image);
      image.click(grr.table.sortableDialog);
    }
  });

  grr.subscribe('timer', function() {
    grr.table.scrollHandler(renderer, me, opt_state);
  }, unique);
};

/**
 * Function to update a dom node via an AJAX call to a renderer.
 *
 * This is similar to the grr.layout() method but it calls the RenderAjax method
 * and is suitable to repeatedly being applied to the same element.
 *
 * @param {string} renderer The rernderer name to call via ajax.
 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into the
 *     AJAX request (as query parameters).
 * @param {Function=} on_success If provided this function will be called on
 *     completion.
 * @param {string} inflight_key The key to use for the inflight queue. If null,
 *     we use the domId.
 * @param {Function=} on_error If provided this function will be called on
 *     errors.
 * @param {string} method Method used for rendering (i.e. RenderAjax or Layout).
 */
grr._update = function(renderer, domId, opt_state, on_success, inflight_key,
                      on_error, method) {
  var state = opt_state || grr.state;
  var inflight_key = inflight_key || domId;

  state.id = domId;
  state.reason = state.reason || grr.state.reason;
  state.client_id = state.client_id || grr.state.client_id;

  // If there is already an in flight request for this domId, drop this one.
  var concurrentRequest = grr.GetFromAjaxQueue(inflight_key);
  if (concurrentRequest) {
    grr.RemoveFromAjaxQueue(inflight_key);
    concurrentRequest.abort();
  }

  var xhr = $.ajax({
    data: (state || grr.state),
    type: grr.ajax_method,
    url: 'render/' + method + '/' + renderer,
    complete: function(jqXHR) {
      if (grr.GetFromAjaxQueue(inflight_key) === jqXHR) {
        // Remove the lock for this domId
        grr.RemoveFromAjaxQueue(inflight_key);
      }
    },
    error: function(jqXHR) {
      if (grr.GetFromAjaxQueue(inflight_key) === jqXHR) {
        var jsonData = false;
        if (jqXHR.status == 500) {
          var data = jqXHR.responseText;
          try {
            data = $.parseJSON(data.substring(4, data.length));
            jsonData = true;
          } catch (e) {
            // Usually renderers get a <script>...</script> code when error
            // happens. We handle this here.
            $(document.body).append(data);
            data = {
              message: grr._lastError,
              traceback: grr._lastBacktrace
            };
          }
        } else {
          var data = {message: 'Server Error',
                      traceback: jqXHR.responseText};
        }

        if (!on_error) {
          if (jsonData) {
            grr.publish('grr_error', {
              message: data.message,
              traceBack: data.traceBack
            });
          }
        }
        else {
          on_error(data);
        }
      }
    },
    success: function(data, status, jqXHR) {
      if (grr.GetFromAjaxQueue(inflight_key) === jqXHR) {
        // Remove the lock for this domId
        grr.RemoveFromAjaxQueue(inflight_key);

        // Load the new table DOM
        on_success(data);
      }
    }
  });
  // Create a lock on this domId to prevent another ajax call while
  // this one is inflight.
  grr.PushToAjaxQueue(inflight_key, xhr);
};

/**
 * Function to update a dom node via an AJAX call to a renderer. Please note
 * that if on_success handler is specified, AJAX response is not htmled into
 * the container div.
 *
 * This is similar to the grr.layout() method but it calls the RenderAjax method
 * and is suitable to repeatedly being applied to the same element.
 *
 * @param {string} renderer The rernderer name to call via ajax.
 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into the
 *     AJAX request (as query parameters).
 * @param {Function=} on_success If provided this function will be called on
 *     completion.
 * @param {string} inflight_key The key to use for the inflight queue. If null,
 *     we use the domId.
 * @param {Function=} on_error If provided this function will be called on
 *     errors.
 * @param {string} method_name If provided we call this method (default
 * RenderAjax).
 */
grr.update = function(renderer, domId, opt_state, on_success, inflight_key,
                      on_error, method_name) {
  if (!on_success) {
    on_success = function(data) {
      $('#' + domId).html(data);
      grr.publish('on_renderer_load', domId);
    };
  }

  grr._update(renderer, domId, opt_state, on_success, inflight_key,
              on_error, method_name || 'RenderAjax');
};

/**
 * Lays out a GRR object by rendering the object into a div. Please note that
 * layout() always puts received html into a container div, no matter if
 * on_success handler is specified or not.
 *
 * @param {string} renderer The renderer name to call via ajax.
 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into
 *     the AJAX request (as query parameters).
 * @param {Function=} on_success If provided this function will be called on
 *     completion.
 */
grr.layout = function(renderer, domId, opt_state, on_success) {
  success_handler = function(data) {
    $('#' + domId).html(data);
    grr.publish('on_renderer_load', domId);
    if (on_success) {
      on_success(domId);
    }
  };

  $('#' + domId).html("<p class='muted'>Loading...</p>");
  grr._update(renderer, domId, opt_state, success_handler, '#' + domId, null,
              'Layout');
};


/**
 * Create the popup menu dialog.
 *
 * @param {string} renderer The renderer used to render the element.
 * @param {string} domId The element we attach the events to.
 * @param {string} openerId The id of the element acting as an opener.
 * @param {Object=} opt_options dialog options.
 */
grr.dialog = function(renderer, domId, openerId, opt_options) {
  // Create the dialog
  $('#' + openerId).click(function() {
    var dialog = $('#' + domId);

    if (dialog.is(':visible')) {
      dialog.modal('hide');
    } else {
      grr.layout(renderer, domId);
      dialog.modal('show');
    }

    return false;
  });
};


/**
 * Sumbits a form to a renderer.
 *
 * @param {string} renderer The renderer to submit to.
 * @param {string} formId The form to submit.
 * @param {string} resultId The renderer will render to this div.
 * @param {string=} opt_state Optional state to merge with the form (default
 *     grr.state).
 * @param {Function=} opt_refreshMethod Optional method for refresh (default
 *     grr.layout).
 * @return {boolean} false.
 */
grr.submit = function(renderer, formId, resultId, opt_state,
    opt_refreshMethod) {
  var new_state = {};
  var method = opt_refreshMethod || grr.layout;
  var state = opt_state || grr.state;

  /* Also support any select tags */
  $('#' + formId + ' input, select').each(function() {
    var name = this.name;
    var value = $(this).val();

    if (name && value) {

      if (this.type == 'checkbox') {
        // Check boxes need to be read like this.
        value = $(this).attr('checked') ? 'true' : 'false';

        // Multiple checkboxes can be concatenated to the same name.
        if (!(name in new_state)) {
          new_state[name] = value;
        } else {
          new_state[name] += ',' + value;
        }
      } else {
        new_state[name] = value;
      }
    }
  });

  /* Merge the global state into the form. */
  $.extend(new_state, state || grr.state);

  // Now send this to the renderer and put the result on result_id
  method(renderer, resultId, new_state);

  return false;
};


/**
 * Parses the location bar's #hash value into an object.
 *
 * @param {Object=} hash Optional hash to be parsed. If not passed,
 *                       window.location.hash will be parsed instead.
 * @return {Object} an associative array of encoded values.
 */
grr.parseHashState = function(hash) {
  if (!hash) {
    hash = window.location.hash;
  }

  if (hash.indexOf('#') == 0) {
    hash = hash.substr(1);
  }

  var result = {};
  var parts = hash.split('&');

  for (var i = 0; i < parts.length; i++) {
    var kv = parts[i].split('=');
    if (kv[0] && kv[1]) {
      result[kv[0]] = decodeURIComponent(kv[1].replace(/\+/g, ' ') || '');
    }
  }

  return result;
};

/**
 * Load the main content pane from the hash provided.
 *
 * @param {string=} opt_hash to load from. If null, use the current window hash.
 */
grr.loadFromHash = function(opt_hash) {
  if (opt_hash) {
    window.location.hash = opt_hash;
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
  $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

  // We use recursive data model generation when rendering forms. Therefore
  // have to increase the digestTtl limit to 50.
  $rootScopeProvider.digestTtl(50);
});

grrUiApp.run(function($injector, $http, $cookies, grrReflectionService) {
  grr.angularInjector = $injector;

  // Ensure CSRF token is in place for Angular-initiated HTTP requests.
  $http.defaults.headers.post['X-CSRFToken'] = $cookies.get('csrftoken');
  $http.defaults.headers.delete = $http.defaults.headers.patch = {
    'X-CSRFToken': $cookies.get('csrftoken')
  };

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
