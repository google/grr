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

    grr.publish('grr_messages', { message: error, traceBack: backtrace });
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

    grr.publish('grr_messages', { message: message });
    $('#table_' + id).attr(table_state);
  },

  RenderAjax: function(state) {
    var id = state.id;
    var message = state.message;

    var table = $('#' + id);
    grr.publish('grr_messages', { message: message });
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


// There should be only one injector instance per app, otherwise
// Angular services which are meant to be singletos, will be created
// multiple times.
var getAngularInjector = function() {
  if (!grr.angularInjector) {
    grr.angularInjector = angular.injector(['ng', 'grrUi']);
  }
  return grr.angularInjector;
};

grr.Renderer('AngularDirectiveRenderer', {

  // Compiles Angular code within a div with current unique id. Used by
  // AngularTestRenderer.
  Compile: function(state) {
    var unique = state.unique;
    var template = $('#' + unique);

    var injector = getAngularInjector();
    var $compile = injector.get('$compile');
    var $rootScope = injector.get('$rootScope');

    var linkFn = $compile(template);
    var element = linkFn($rootScope);
  },

  Layout: function(state) {
    var unique = state.unique;
    var directive = state.directive;
    var directive_args = state.directive_args;

    var injector = getAngularInjector();
    var $compile = injector.get('$compile');
    var $rootScope = injector.get('$rootScope');

    var isolatedScope = $rootScope.$new(true, $rootScope);

    var template = $(document.createElement(directive));
    if (angular.isDefined(directive_args)) {
      var index = 0;
      for (var key in directive_args) {
        var value = directive_args[key];
        var valueName = 'var' + index.toString();
        isolatedScope[valueName] = value;
        template.attr(key, valueName);
        ++index;
      }
    }

    var templateFn = $compile(template);
    templateFn(isolatedScope, function(cloned) {
      var parent = $('#' + unique);
      parent.append(cloned);
    });

    // When parent item goes away destroy the scope. Otherwise we'll have a
    // leak. In Angular-only application Angular handles this itself
    // (TODO: double check that it does), but here, because we remove DOM
    // elements outside of normal Angular workflow, we have to delete
    // the scope manually.
    var poll = function() {
      setTimeout(function() {
        if ($('#' + unique).length == 0) {
          isolatedScope.$destroy();
        } else {
          poll();
        }
      }, 1000);
    };
    poll();
  }
});
