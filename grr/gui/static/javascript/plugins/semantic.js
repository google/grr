var grr = window.grr || {};

grr.Renderer('ClientURNRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    $('#ClientInfoButton_' + unique).click(function(event) {
      $('#ClientInfo_' + unique).modal();

      event.preventDefault();
    });

    $('#ClientInfo_' + unique).on('show.bs.modal', function() {
      grr.update(state.renderer, 'ClientInfoContent_' + unique,
                 {urn: state.urn});
    });
  }
});


grr.Renderer('KeyValueFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('#' + unique).find('a[data-type]').on('click', function() {
      var jthis = $(this);
      var target = jthis.closest('ul').data('name');
      var json_store = jthis.closest('.FormData').data();
      var value = jthis.data('type');

      json_store[target] = value;
      jthis.closest('div').find('button span.Type').text(value);
    });
  }
});


grr.Renderer('RDFValueArrayRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var next_start = state.next_start;
    var cache_urn = state.cache_urn;
    var array_length = state.array_length;

    $('#' + unique + ' a').click(function() {
      grr.layout('RDFValueArrayRenderer', unique, {
        start: next_start,
        cache: cache_urn,
        length: array_length
      });
    });
  }
});


grr.Renderer('AES128KeyFormRenderer', {
  Layout: function(state) {
    var prefix = state.prefix;

    $('#' + prefix).change();
  }
});
