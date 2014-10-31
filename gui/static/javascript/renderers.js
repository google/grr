var grr = window.grr || {};

/**
 * Namespace for renderers.
 */
grr.renderers = grr.renderers || {};

/**
 * Registers javascript methods for the particular renderer.
 *
 * @param {string} name Name of the renderer.
 * @param {Object} spec Dictionary of functions - i.e. javascript methods
 *     corresponding to to the renderer.
 */
grr.Renderer = function(name, spec) {
  grr.renderers[name] = spec;
};

/**
 * Exception that is thrown when a particular renderer is not found.
 *
 * @param {string} renderer Name of the renderer.
 * @constructor
 */
grr.NoSuchRendererException = function(renderer) {
  this.description = 'No renderer with name: ' + renderer;
  this.renderer = renderer;
};

/**
 * Executes given method of a given renderer, passing 'state' as an argument.
 * @param {string} objMethod Renderer and its' method to be called. I.e.
       "SomeRenderer.Layout" or "SomeOtherRenderer.RenderAjax".
 * @param {Object} state Dictionary that is passed as a single argument to
       the corresponding renderer's function.
 */
grr.ExecuteRenderer = function(objMethod, state) {
  var parts = objMethod.split('.');
  var renderer = parts[0];
  var method = parts[1];

  var rendererObj = grr.renderers[renderer];

  if (!rendererObj) {
    grr.log('No such renderer: ' + renderer);
    throw new grr.NoSuchRendererException(renderer);
  }

  if (rendererObj[method]) {
    rendererObj[method](state);
  }
};


grr.Renderer('ConfirmationDialogRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    // Present system messages in the dialog box for easy viewing.
    grr.subscribe('grr_messages', function(message) {
      if (message) {
        $('#footer_message_' + unique).text(
            message).show().delay(5000).fadeOut('fast');
      }
    }, 'footer_message_' + unique);

    $('#proceed_' + unique).click(function() {
      var jthis = $(this);
      var data = $.extend({}, grr.state, state,
                          jthis.closest('.FormData').data());

      var submit_function = function() {
        grr.update(
          state.renderer, 'results_' + unique, data,
          function(result) {
            $('#results_' + unique).html(result);
            jthis.hide();
          }, null, function(data) {
            jthis.attr('disabled', false);
            grr.publish('grr_messages', data.message);
            });
      };

      jthis.attr('disabled', true);

      if (state.check_access_subject) {
        // We execute CheckAccess renderer with silent=true. Therefore it
        // searches for an approval and sets correct reason if approval is
        // found. When CheckAccess completes, we execute specified renderer,
        // which. If the approval wasn't found on CheckAccess stage, it will
        // fail due to unauthorized access and proper ACLDialog will be
        // displayed.
        grr.layout('CheckAccess', 'check_access_results_' + unique, {
            silent: true,
            subject: state.check_access_subject
          }, submit_function);
      } else {
        submit_function();
      }
    });
  }
});

/**
 *  Stores last error reported by ErrorHandler renderer.
 */
grr._lastError = null;
/**
 * Stores last error backtrace reported by ErrorHandler renderer.
 */
grr._lastBacktrace = null;

grr.Renderer('ErrorHandler', {
  Layout: function(state) {
    var error = state.error;
    var backtrace = state.backtrace;

    grr._lastError = error;
    grr._lastBacktrace = backtrace;

    grr.publish('grr_messages', 'Error: ' + error);
    grr.publish('grr_traceback', 'Error: ' + backtrace);
  }
});


grr.Renderer('TableRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var table_state = state.table_state;
    var message = state.message;

    grr.table.newTable(renderer, 'table_' + id,
                       unique, table_state);

    grr.publish('grr_messages', message);
    $('#table_' + id).attr(table_state);
  },

  RenderAjax: function(state) {
    var id = state.id;
    var message = state.message;

    var table = $('#' + id);
    grr.publish('grr_messages', message);
  }
});


grr.Renderer('TreeRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;
    var publish_select_queue = state.publish_select_queue;
    var tree_state = state.tree_state;

    grr.grrTree(renderer, unique, publish_select_queue, tree_state);
  }
});


grr.Renderer('TabLayout', {
  Layout: function(state) {
    var unique = state.unique;
    var disabled = state.disabled;
    var tab_layout_state = state.tab_layout_state;
    var tab_hash = state.tab_hash;
    var selected_tab = state.selected_tab;

    // Disable the tabs which need to be disabled.
    $('li').removeClass('disabled');
    $('li a').removeClass('disabled');

    for (var i = 0; i < disabled.length; ++i) {
      $('li[renderer=' + disabled[i] + ']').addClass('disabled');
      $('li a[renderer=' + disabled[i] + ']').addClass('disabled');
    }

    // Store the state of this widget.
    $('#' + unique).data().state = tab_layout_state;

    grr.pushState(unique, tab_layout_state);

    // Add click handlers to switch tabs.
    $('#' + unique + ' li a').click(function(e) {
      e.preventDefault();
      if ($(this).hasClass('disabled')) return false;

      var renderer = this.attributes['renderer'].value;
      if (tab_hash) {
        grr.publish('hash_state', tab_hash, renderer);
      }

      // Make a new div to accept the content of the tab rather than drawing
      // directly on the content area. This prevents spurious drawings due to
      // latent ajax calls.
      content_area = $('#tab_contents_' + unique);
      content_area.html('<div id="' + renderer + '_' + unique + '">');
      update_area = $('#' + renderer + '_' + unique);

      // We append the state of this widget which is stored on the unique
      // element.
      grr.layout(renderer, renderer + '_' + unique,
                 $('#' + unique).data().state);

      // Clear previously selected tab.
      $('#' + unique).find('li').removeClass('active');

      // Select the new one.
      $(this).parent().addClass('active');
    });

    // Find first enabled tab (the default selection).
    var enabledTabs = $.map(
        $('#' + unique + ' > li:not(.disabled)'),
        function(val) {
          return $(val).attr('renderer');
        });

    // Select the first tab at first.
    if (tab_hash) {
      var selected = grr.hash[tab_hash] || selected_tab;
    } else {
      var selected = selected_tab;
    }

    if (enabledTabs.indexOf(selected) == -1) {
      selected = enabledTabs.length > 0 ? enabledTabs[0] : null;
    }
    if (selected) {
      $($('#' + unique + " li a[renderer='" + selected + "']")).click();
    }
  }
});


grr.Renderer('Splitter', {
  Layout: function(state) {
    var id = state.id;
    var min_left_pane_width = state.min_left_pane_width;
    var max_left_pane_width = state.max_left_pane_width;

    $('#' + id)
        .splitter({
          minAsize: min_left_pane_width,
          maxAsize: max_left_pane_width,
          splitVertical: true,
          A: $('#' + id + '_leftPane'),
          B: $('#' + id + '_rightPane'),
          animSpeed: 50,
          closeableto: 0});

      $('#' + id + '_rightSplitterContainer')
          .splitter({
            splitHorizontal: true,
            A: $('#' + id + '_rightTopPane'),
            B: $('#' + id + '_rightBottomPane'),
            animSpeed: 50,
            closeableto: 100});

    // Triggering resize event here to ensure that splitters will position
    // themselves correctly.
    $('#' + id).resize();
  }
});


grr.Renderer('Splitter2Way', {
  Layout: function(state) {
    var id = state.id;

    $('#' + id)
        .splitter({
          splitHorizontal: true,
          A: $('#' + id + '_topPane'),
          B: $('#' + id + '_bottomPane'),
          animSpeed: 50,
          closeableto: 100});
  }
});


grr.Renderer('Splitter2WayVertical', {
  Layout: function(state) {
    var id = state.id;
    var min_left_pane_width = state.min_left_pane_width;
    var max_left_pane_width = state.max_left_pane_width;

    $('#' + id)
        .splitter({
          minAsize: min_left_pane_width,
          maxAsize: max_left_pane_width,
          splitVertical: true,
          A: $('#' + id + '_leftPane'),
          B: $('#' + id + '_rightPane'),
          animSpeed: 50,
          closeableto: 0});
  }
});


grr.Renderer('ErrorRenderer', {
  Layout: function(state) {
    var value = state.value;

    grr.publish('messages', value);
  }
});

grr.Renderer('AngularDirectiveRenderer', {
  // Compiles Angular code within a div with current unique id. Used by
  // AngularTestRenderer.
  Compile: function(state) {
    var unique = state.unique;
    var template = $('#' + unique);

    var injector = angular.injector(['ng', 'grrUi']);
    var $compile = injector.get('$compile');
    var $rootScope = injector.get('$rootScope');

    var linkFn = $compile(template);
    var element = linkFn($rootScope);
  },

  Layout: function(state) {
    var unique = state.unique;
    var directive = state.directive;
    var directive_args = state.directive_args;

    var template = $(document.createElement(directive));
    template.attr(directive_args);

    var injector = angular.injector(['ng', 'grrUi']);
    var $compile = injector.get('$compile');
    var $rootScope = injector.get('$rootScope');

    var linkFn = $compile(template);
    var element = linkFn($rootScope);

    $rootScope.$apply(function() {
      var parent = $('#' + unique);
      parent.append(element);
    });
  }
});
