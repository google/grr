/*global Gallery,Dygraph,data */
Gallery.register(
  'edge-padding',
  {
    name: 'Edge Padding',
    title: 'Graph edge padding and axis position',
    setup: function(parent) {
      parent.innerHTML = (
          "<p>" +
          "  <b>Mode:</b>" +
          "    <input type='radio' name='mode'>use {x,y}RangePad</input>" +
          "    <input type='radio' name='mode'>original</input>" +
          " <br /><b>Settings:</b>" +
          "    <input type='checkbox' id='yrange'>valueRange=[-2,2]</input>" +
          "</p>" +
          "<div id='demodiv'></div>"
          );
    },
    run: function() {
      var parent = document.getElementById("demodiv");

      var graphs = [];
      var nrows = 50;

      for (var oy = -2; oy <= 2; ++oy) {
        for (var ox = -1; ox <= 1; ++ox) {
          var gdiv = document.createElement('div');
          gdiv.style.display = 'inline-block';
          gdiv.style.margin = '2px';
          parent.appendChild(gdiv);

          var data = [];
          for (var row = 0; row < nrows; ++row) {
            var x = row * 5 / (nrows - 1);
            data.push([ox * 2.5 + x - 2.5,
                    oy + Math.sin(x),
                    oy + Math.round(Math.cos(x))]);
          }

          var g = new Dygraph(gdiv, data, {
              labels: ['x', 'A', 'B'],
              labelDivWidth: 100,
              gridLineColor: '#ccc',
              includeZero: true,
              width: 250,
              height: 130
          });
          graphs.push(g);
        }
        parent.appendChild(document.createElement('br'));
      }

      var updateGraphOpts = function(opts) {
        for (var i = 0; i < graphs.length; ++i) {
          graphs[i].updateOptions(opts);
        }
      };

      var mode = document.getElementsByName('mode');
      mode[0].onchange = function() {
        updateGraphOpts({
          avoidMinZero: false,
          xRangePad: 3,
          yRangePad: 10,
          drawAxesAtZero: true});
      };
      mode[1].onchange = function() {
        updateGraphOpts({
          avoidMinZero: true,
          xRangePad: 0,
          yRangePad: null,
          drawAxesAtZero: false});
      };
      mode[0].checked = true;
      mode[0].onchange();

      var yrange = document.getElementById('yrange');
      yrange.onchange = function(ev) {
        updateGraphOpts({
          valueRange: ev.target.checked ? [-2, 2] : null});
      };

    }
  });
