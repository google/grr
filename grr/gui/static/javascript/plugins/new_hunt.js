var grr = window.grr || {};

grr.Renderer('HuntInformation', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;

    $('#' + unique).closest('.WizardPage').on('show', function() {
      grr.update(renderer, unique, $('#' + unique).closest('.FormData').data());
    });
  }
});

grr.Renderer('HuntConfigureOutputPlugins', {
  Layout: function(state) {
    var unique = state.unique;
    var defaultOutputPlugin = state.default_output_plugin;

    if (defaultOutputPlugin) {
      $('#AddButton' + unique).trigger('addItem', [defaultOutputPlugin]);
    }
  }
});

grr.Renderer('AFF4ObjectLabelNameFormRenderer', {
  Layout: function(state) {
    var prefix = state.prefix;

    grr.forms.inputOnChange($('#' + prefix));
  }
});
