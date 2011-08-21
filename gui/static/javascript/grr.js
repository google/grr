/* Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
 * Initializer for the grr object. Clears all message queues and state.
 */
grr.init = function() {
  /**
   * This is the grr publisher/subscriber queue.
   * @type {Object.<function(Object)>}
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

    window.location.hash = $.param(grr.hash);
  }, 'body');

  grr.subscribe('grr_messages', function(message) {
        $('#footer').text(message);
  }, 'footer');

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
    grr.installXssiProtection();
    grr.installXssiProtection = false;

    /* This is required to send the csrf token as per
     https://docs.djangoproject.com/en/1.1/ref/contrib/csrf/
     */
    $('html').ajaxSend(function(event, xhr, settings) {
      // Only send the token to relative URLs i.e. locally.
      if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        xhr.setRequestHeader('X-CSRFToken', $('#csrfmiddlewaretoken').val());
      }
    });
  }

  /**
   * This object holds the current url location hash state.
   */
  grr.hash = grr.parseHashState();
};

/**
 * Create a new tree on the domId provided.
 *
 * @param {string} renderer The name of the RenderTree responsible for this
 *     tree.
 * @param {string} domId The domId of the div element that will contain the
 *     tree.
 * @param {string=} opt_publishEvent The name of the GRR event queue where
 *     select events will be published. DEFAULT: "tree_select".
 * @param {Object=} opt_state An optional state object to pass to the
 *     server. DEFAULT: global state.
 * @param {Function=} opt_success_cb an optional function to handle ajax stream.
 */
grr.grrTree = function(renderer, domId, opt_publishEvent, opt_state,
                       opt_success_cb) {
  var state = opt_state || grr.state;
  var publishEvent = opt_publishEvent || 'tree_select';

  state.path = '/';

  /* Build the tree navigator */
  var container = $('#' + domId);
  var unique_id = (new Date()).getTime();

  /* We attach the tree to a unique dom node so that when the tree is removed,
   * subscribed events will also disappear. */
  container.append("<div class='grr_default' id='" + unique_id + "'></div>");
  var tree = $('#' + unique_id);

  tree.jstree({
    'json_data' : {
      'ajax' : {
        'url' : 'render/RenderAjax/' + renderer,
        'type': grr.ajax_method,
        beforeSend: function(xhr) {
          xhr.setRequestHeader('X-CSRFToken', $('#csrfmiddlewaretoken').val());
        },
        'data' : function(n) {
          var new_state = $.extend({}, state);

          if (n.attr) {
            new_state.path = '/' + this.get_path(n).join('/');
            new_state.id = n.attr('id');
          }

          return new_state;
        },

        'success': function(data, textStatus, jqXHR) {
          var tree = this;

          if (opt_success_cb) {
            opt_success_cb(data, textStatus, jqXHR);
          }

          return data.data;
        }
      }
     },
     'plugins' : ['themes', 'json_data', 'ui']
  });

  /* Bind the select event to the publish queue */
  tree.bind('select_node.jstree', function(event, data) {
    var path = '/' + data.inst.get_path(data.rslt.obj).join('/');
    var selected_id = $(data.rslt.obj).attr('id');
    var update_hash = data.args[1];

    grr.publish(publishEvent, path, selected_id, update_hash);

    if (update_hash != 'no_hash') {
      grr.publish('hash_state', 't', selected_id);
    }
    return true;
  });

  /* Open the tree if the hash says to. */
  tree.bind('loaded.jstree', function() {
    if (grr.hash.t) {
      grr.openTree(tree, grr.hash.t);
    }
  });

  /* Each node that is opened will update the hash */
  tree.bind('open_node.jstree', function(e, data) {
    var selected_id = data.args[0][0].id;
    var update_hash = data.args[2];

    if (selected_id && update_hash != 'no_hash') {
      grr.publish('hash_state', 't', selected_id);
    }
  });

  /* We do not want jstree to cache the leafs when a tree is closed. */
  tree.bind('close_node.jstree', function(e, data) {
    $(data.args[0]).children('ul').text('');
  });

  grr.subscribe('client_selection', function(message) {
    // Kill the tree
    container.html('');
    // Make a new one
    grr.grrTree(renderer, domId, opt_publishEvent, opt_state,
      opt_success_cb);
    grr.publish(publishEvent, '/');
  }, unique_id);
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

  var cb = function(i) {
    var id_to_open = parts.slice(0, i + 1).join('-');
    var node = $('#' + id_to_open);

    if (node.length && parts[i + 1]) {
      tree.jstree('open_node', node, function() { cb(i + 1);}, 'no_hash');
    } else {
      // Ultimate node, when its done we want to select it
      tree.jstree('select_node', node, 'no_hash');
      grr.publish('hash_state', 't', node.attr('id'));
    }
  };

  cb(0);
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
 * Lays out a GRR object by rendering the object into a div.
 *
 * @param {string} renderer The rernderer name to call via ajax.
 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into
 *     the AJAX request (as query parameters).
 */
grr.layout = function(renderer, domId, opt_state) {
  // Use global state by default
  var state = $.extend({}, opt_state || grr.state);

  state.id = domId;
  $.ajax({
    dataType: 'html',
    data: state,
    type: grr.ajax_method,
    url: 'render/Layout/' + renderer,
    success: function(data) {
      // Load the new table DOM
      var node = $('#' + domId);

      if (node) {
        node.html(data).
          // Let the element know which is its renderer
          data().renderer = renderer;

        grr.publish('GeometryChange');
      }
    }
  });
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
 * Build a table using a renderer on a div node.
 *
 * @param {string} name The name of the renderer to call.
 * @param {string} domId The element which will host the html.
 * @param {string=} opt_domFormat A data table sDom Format string to control the
 *     layout of the table.
 * @param {string=} opt_state a state object to pass to the server.
 * @param {Object=} opt_options Options to pass to the dataTable.
 */
grr.grrTable = function(name, domId, opt_domFormat, opt_state, opt_options) {
  var domFormat = opt_domFormat || '<\'H\'lrp>t<\'F\'>';
  var state = opt_state || grr.state;
  var dataTableOptions = $.extend({}, opt_options || {});
  var table_hash = opt_options.table_hash;

  /**
   * This function filters the AJAX call to the server and adds the attributes
   * to it.
   * @param {string} source the url to call.
   * @param {Object} data Data to send to the server.
   * @param {Function} completion Function to be called when the request
   *     completes.
   */
  var dataTableAJAXFilter = function(source, data, completion) {
    /* Add the attributes to send to the source */
    for (i in state) {
      data.push({ 'name': i, 'value': state[i] });
    }

    $.ajax({
      'dataType': 'json',
      'type': grr.ajax_method,
      'url': source,
      'data': data,
      // Hook the data table handle to allow row updates to indicate errors.
      'success': function (data, textStatus, jqXHR) {
        var message = data.message;

        if (message) {
            grr.publish("grr_messages", message);
        };
        completion(data, textStatus, jqXHR);
      }
    });
  };

  /**
   * Unhighlights all the tr elements in the table and only Highlight the tr
   * element directly above the clicked element. This event handler is attached
   * to the table body.
   * @param {Event} event The click event which was generated.
   * @this The element that generated the event.
   */
  var tableClickHandler = function(event) {
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
      grr.publish('table_selection_' + domId, node);

      // Update the table hash
      if (table_hash) {
        grr.publish('hash_state', table_hash, row_id);
      }
    }
  };

  jQuery.fn.dataTableExt.oPagination.iFullNumbersShowPages = 15;
  dataTableOptions = $.extend({
    'bAutoWidth': true,
    'bJQueryUI': true,
    'sDom': domFormat,
    'sPaginationType': 'full_numbers',
    'bProcessing': true,
    'bServerSide': true,
    'fnDrawCallback': function(settings, data) {
      if (table_hash && grr.hash[table_hash] != undefined) {
        $('#' + domId + ' tr[row_id="' +
          parseInt(grr.hash[table_hash]) + '"]').click();
      }
      grr.publish('GeometryChange');
    },
    'fnRowCallback': function(row, data, displayIndex) {
      var settings = this.fnSettings();
      // Make each row remember its row ID
      $(row).attr('row_id', displayIndex + settings._iDisplayStart);

      return row;
    },
    'sAjaxSource': 'render/RenderAjax/' + name,
    'fnServerData': dataTableAJAXFilter
  }, dataTableOptions);

  var table = $('#' + domId + ' table').dataTable(dataTableOptions);
  table.click(tableClickHandler);
};


/**
 * Makes a table listen to published events.
 *
 * @param {string} domId The dom id of the table.
 * @param {string} queue Name of the queue to listen on.
 * @param {string} parameter Events received from the queue are
 *     assigned to this CGI parameter which will be passed to the server.
*/
grr.subscribeUpdateTable = function(domId, queue, parameter) {
  grr.delayedSubscribe(queue, 1, domId, function(event) {
    grr.state[parameter] = event;

    //Redraw the table
    var table = $('#table_' + domId);
    table.dataTable({'bRetrieve': true}).fnDraw();
  });
};

/**
 * Redraw the table and possibly sync up to a particular hash state.
 *
 * @param {string} domId The dom id of the table.
 */
grr.redrawTable = function(domId) {
  var table = $('#' + domId).dataTable();
  var settings = table.fnSettings();
  var tb = grr.hash.tb || 0;

  // If we need to go to a certain place we do so now
  var page = parseInt(tb / settings._iDisplayLength);
  settings._iDisplayStart = page * settings._iDisplayLength;
  settings._iDisplayEnd = settings._iDisplayStart + settings._iDisplayLength;

  // Do not let dataTable to sort or filter for us (This will reset the start
  // position).
  var old_filter = settings.oFeatures.bFilter;
  settings.oFeatures.bSort = false;
  settings.oFeatures.bFilter = false;

  table.fnDraw();
  settings.oFeatures.bFilter = old_filter;
};

/**
 * Creates a periodic polling clock for updating certain elements on
 * the page.
 * @param {string} renderer - The rernderer name to call via ajax.
 * @param {string} domId - This callback will be called as long as domId exists.
 * @param {Function} callback will be called each time with the data returned.
 * @param {number} timeout number of seconds between polls.
 * @param {Object} state the state to pass to the server.
 * @param {string=} opt_datatype Expected data type "html" (default),
 *          "json", "xml".
*/
grr.poll = function(renderer, domId, callback, timeout, state, opt_datatype) {
  /* Enforce a minimum timeout */
  if (!timeout || timeout < 1000) {
    timeout = 1000;
  }

  /** We deliberately not call window.setInterval to avoid overrunning
     the server if its too slow.
   */
  function update() {
    $.ajax({
      url: 'render/RenderAjax/' + renderer,
      data: state,
      type: grr.ajax_method,
      dataType: opt_datatype || 'html',
      success: function(data) {
        // Load the new table DOM
        var result = callback(data);

        // Schedule another update
        if (result && $('#' + domId).html()) {
          window.setTimeout(update, timeout);
        }
      },

      // In case of error just keep trying
      error: function(event) {
        window.setTimeout(update, timeout);
      }
    });
  };

  // First one to kick off
  window.setTimeout(update, timeout);
};

/**
 * Function to update a dom node via an AJAX call to a renderer.
 *
 * This is similar to the grr.layout() method but it calls the RenderAjax method
 * and is suitable to repeatadely being applied to the same element.
 *
 * @param {string} renderer The rernderer name to call via ajax.
 * @param {string} domId The element which will host the html.
 * @param {Object=} opt_state A data object which will be serialiased into the
 *     AJAX request (as query parameters).
 *
 */
grr.update = function(renderer, domId, opt_state) {
  var target = $('#' + domId);
  var state = opt_state || grr.state;

  state.id = domId;

  $.ajax({
    dataType: 'html',
    data: (state || grr.state),
    type: grr.ajax_method,
    url: 'render/RenderAjax/' + renderer,
    success: function(data) {
      // Load the new table DOM
      target.html(data);
    }
  });
};

/**
 * Function sets up event handlers on text elements.
 *
 * @param {string} domId The element we attach the events to.
 * @param {string} queue The name of the queue to send key down
 *     events to.
*/
grr.installEventsForText = function(domId, queue) {
  var node = $('#' + domId);

  // Stops event bubbling
  var blocker = function(event) {
    event.stopPropagation();
    node.focus();
  };

  // Install events on this node.
  node.keyup(function(event) {
    grr.publish(queue, this.value);
    blocker(event);
  });

  // Block bubbling of these events.
  node.mousedown(blocker);
  node.click(blocker);
};

/**
 * Override the jQuery parser to remove XSSI protections.
 *
 * @return {?Object} JSON object or null if parsing failed.
 */
grr.installXssiProtection = function() {
  var oldParseJSON = jQuery.parseJSON;

  jQuery.parseJSON = function(data) {
    if (typeof data !== 'string' || !data) {
      return null;
    }

    if (data.substring(0, 4) != ')]}\n') {
      return jQuery.error('JSON object not properly protected.');
    }

    return oldParseJSON(data.substring(4, data.length));
  };

  return null;
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
  $('#' + domId).dialog($.extend(
    { autoOpen: false,
      show: 'blind',
      hide: 'explode',
      width: parseInt($('body').css('width')) * 0.90,
      height: parseInt($('body').css('height')) * 0.90
    }, opt_options))
  .bind('dialogresizestop', function() {
    grr.publish('GeometryChange');
  });

  grr.layout(renderer, domId);

  $('#' + openerId).click(function() {
    var dialog = $('#' + domId);

    if (dialog.dialog('isOpen')) {
       dialog.dialog('close');
    } else {
       dialog.dialog('open');
    }

    grr.publish('GeometryChange');
    return false;
  });
};

/**
 * Creates an extruder (A foldable collapsible menu) as in:
 * @see http://pupunzi.open-lab.com/mb-jquery-components/jquery-mb-extruder/
 *
 * @param {string} renderer The renderer used to render the element.
 * @param {string} domId The element we turn into an extruder.
 * @param {string=} opt_extruderPosition Optional position of the extruder
 *     (default top, can be left, right, bottom).
 * @param {Object=} opt_state Optional state to use (default grr.state).
 */
grr.extruder = function(renderer, domId, opt_extruderPosition, opt_state) {
  var selector = '#' + domId;
  var extruder = $(selector);
  var position = opt_extruderPosition || 'top';
  var state = opt_state || grr.state;

  state.id = domId;

  extruder.buildMbExtruder({
    position: position,
    extruderOpacity: 0.8,
    flapDim: 100
  });

  // Set the title of the flap from the title attribute
  $(selector + ' .flap span').text($(selector).attr('title'));
  extruder.setMbExtruderContent({
    url: '/render/Layout/' + renderer,
    data: state
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
      new_state[name] = value;
    }
  });

  /* Merge the global state into the form. */
  $.extend(new_state, state || grr.state);

  // Now send this to the renderer and put the result on result_id
  method(renderer, resultId, new_state);

  return false;
};

/**
 * Updates the form from an object.
 *
 * @param {string} formId The form to update.
 * @param {object=} state Optional state to merge with the form (default
 *     grr.state).
 */
grr.update_form = function(formId, state) {
  $('#' + formId + ' input, select').each(function() {
    if (state[this.name]) {
      // Make sure the change event is fired after the value changed.
      $(this).val(state[this.name]).change();
    }
  });
};

/**
 * Updates the height of the element so it and all its siblings fit within their
 * parent.
 *
 * @param {Object} element A JQuery selected object for the element to fix.
 *
 */
grr.fixHeight = function(element) {
  var height = element.parent().height();
  var calculate_height = function() {
    var tag_name = this.tagName;

    // For some reason script tags report a non zero height in chrome.
    if (tag_name != 'SCRIPT') {
      height -= $(this).outerHeight();
    }
  };

  element.prevAll().each(calculate_height);
  element.nextAll().each(calculate_height);

  height -= parseInt(element.css('padding-top'));
  height -= parseInt(element.css('padding-bottom'));

  element.height(height + 'px');
};

/**
 * Parses the location bar's #hash value into an object.
 *
 * @return {Object} an associative array of encoded values.
 */
grr.parseHashState = function() {
  var result = {};
  var parts = window.location.hash.substr(1).split('&');

  for (var i = 0; i < parts.length; i++) {
    var kv = parts[i].split('=');
    if (kv[0]) {
      result[kv[0]] = decodeURIComponent(kv[1] || '');
    }
  }

  return result;
};

/**
 * Store the state of the foreman form.
 *
 * @param {Object} state of the foreman form.
 *
 */
grr.foreman = {regex_rules: 0, action_rules: 0};

/**
 * Adds another condition stanza to the Foreman rule form.
 *
 * @param {Object} defaults value filled in from the server filling in the js
 *  template.
 */
grr.foreman.add_condition = function(defaults) {
  defaults.rule_number = grr.foreman.regex_rules;
  $('#addRuleTemplate').tmpl(defaults).appendTo('#ForemanFormRuleBody');
  grr.foreman.regex_rules += 1;
};

/**
 * Adds another action stansa to the Foreman rule form.
 *
 * @param {Object} defaults value filled in from the server filling in the js
 *  template.
 */
grr.foreman.add_action = function(defaults) {
  defaults.rule_number = grr.foreman.action_rules;
  $('#addActionTemplate').tmpl(defaults).appendTo('#ForemanFormActionBody');
  grr.foreman.action_rules += 1;
};


/** Initialize the grr object */
grr.init();

