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
