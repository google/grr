var grr = window.grr || {};

grr.Renderer('ConfigFileTableToolbar', {
  Layout: function(state) {
    var unique = state.unique;

    grr.subscribe('file_select', function(aff4_path, age) {
      var state = {aff4_path: aff4_path};
      grr.downloadHandler($('#' + unique + '_download'), state,
                          safe_extension = true,
                          '/render/Download/DownloadView');
    }, 'toolbar_' + unique);

    $('#upload_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('ConfigBinaryUploadView',
                 'upload_dialog_body_' + unique);
    });
  }
});
