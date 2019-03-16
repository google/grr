/*global Gallery,Dygraph,data */
Gallery.register(
  'negative',
  {
    name: 'Negative values',
    setup: function(parent) {
      parent.innerHTML = 
          "<p>All negatives (x-axis on top):</p>" +
          "<div id='g1' style='width:600px; height:200px;'></div>" +

          "<p>Mixed (x-axis in middle):</p>" +
          "<div id='g2' style='width:600px; height:200px;'></div>" +

          "<p>All positives (x-axis on bottom):</p>" +
          "<div id='g3' style='width:600px; height:200px;'></div>";
    },
    run: function() {
      var negs = [];
      var mixed = [];
      var pos = [];
      for (var i = 0; i < 100; i++) {
        negs.push([i, -210 + i, -110 - i]);
        mixed.push([i, -50 + i, 50 - i]);
        pos.push([i, 1000 + 2 * i, 1100 + i]);
      }

      new Dygraph(
        document.getElementById("g1"),
        negs, { labels: [ 'x', 'y1', 'y2' ] }
      );

      new Dygraph(
        document.getElementById("g2"),
        mixed, { labels: [ 'x', 'y1', 'y2' ] }
      );

      new Dygraph(
        document.getElementById("g3"),
        pos, { labels: [ 'x', 'y1', 'y2' ] }
      );
    }
  });
