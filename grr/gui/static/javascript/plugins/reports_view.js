var grr = window.grr || {};

grr.Renderer('ReportNameRenderer', {
  Layout: function(state) {
    var prefix = state.prefix;

    // Force a state update as the default should be usable. Cleaner way?
    grr.forms.inputOnChange($('#' + prefix));
  }
});
