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
