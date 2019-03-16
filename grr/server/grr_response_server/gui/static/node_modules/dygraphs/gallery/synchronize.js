/*global Gallery,Dygraph,data */
/*jshint loopfunc:true */
/*global NoisyData */
Gallery.register(
  'synchronize',
  {
    name: 'Synchronization',
    title: 'Multiple graphs in sync',
    setup: function(parent) {
      parent.innerHTML = [
        '<style>',
        '  .chart { width: 500px; height: 300px; }',
        '  .chart-container { overflow: hidden; }',
        '  #div1 { float: left; }',
        '  #div2 { float: left; }',
        '  #div3 { float: left; clear: left; }',
        '  #div4 { float: left; }',
        '</style>',
        '<p>Zooming and panning on any of the charts will zoom and pan all the',
        'others. Selecting points on one will select points on the others.</p>',
        '<p>To use this, source <a href="https://github.com/danvk/dygraphs/blob/master/extras/synchronizer.js"><code>extras/synchronizer.js</code></a> on your page.',
        'See the comments in that file for usage.</p>',
        '<div class="chart-container">',
        '  <div id="div1" class="chart"></div>',
        '  <div id="div2" class="chart"></div>',
        '  <div id="div3" class="chart"></div>',
        '  <div id="div4" class="chart"></div>',
        '</div>',
        '<p>',
        '  Synchronize what?',
        '  <input type=checkbox id="chk-zoom" checked><label for="chk-zoom"> Zoom</label>',
        '  <input type=checkbox id="chk-selection" checked><label for="chk-selection"> Selection</label>',
        '</p>'
        ].join("\n");
    },
    run: function() {
      var gs = [];
      var blockRedraw = false;
      for (var i = 1; i <= 4; i++) {
        gs.push(
          new Dygraph(
            document.getElementById("div" + i),
            NoisyData, {
              rollPeriod: 7,
              errorBars: true,
            }
          )
        );
      }
      var sync = Dygraph.synchronize(gs);
      
      function update() {
        var zoom = document.getElementById('chk-zoom').checked;
        var selection = document.getElementById('chk-selection').checked;
        sync.detach();
        sync = Dygraph.synchronize(gs, {
          zoom: zoom,
          selection: selection
        });
      }
      $('#chk-zoom, #chk-selection').change(update);
    }
  });
