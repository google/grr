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
