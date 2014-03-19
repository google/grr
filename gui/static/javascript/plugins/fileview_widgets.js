var grr = window.grr || {};

grr.Renderer('HexView', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;
    var table_width = state.table_width;
    var aff4_path = state.aff4_path;
    var age = state.age;

    $('#' + unique).resize(function() {
      grr.hexview.HexViewer(renderer, unique, table_width,
                            {aff4_path: aff4_path, age: age });
    });
    $('#' + unique).resize();
  }
});

grr.Renderer('TextView', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;
    var default_codec = state.default_codec;
    var aff4_path = state.aff4_path;
    var age = state.age;

    grr.textview.TextViewer(renderer, unique, default_codec,
                            {aff4_path: aff4_path, age: age });
  }
});
