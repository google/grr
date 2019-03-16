/*global Gallery,Dygraph,data */
Gallery.register(
  'dynamic-update',
  {
    name: 'Dynamic Update',
    title: 'Live random data',
    setup: function(parent) {
      parent.innerHTML = [
          "<div id='div_g' style='width:600px; height:300px;'></div>",
          "<p>This test is modeled after a ",
          "<a href='http://www.highcharts.com/demo/?example=dynamic-update&theme=default'>highcharts",
          "test</a>. New points should appear once per second. Try zooming and ",
          "panning over to the right edge to watch them show up.</p>"].join("\n");
    },
    run: function() {
      var data = [];
      var t = new Date();
      for (var i = 10; i >= 0; i--) {
        var x = new Date(t.getTime() - i * 1000);
        data.push([x, Math.random()]);
      }

      var g = new Dygraph(document.getElementById("div_g"), data,
                          {
                            drawPoints: true,
                            showRoller: true,
                            valueRange: [0.0, 1.2],
                            labels: ['Time', 'Random']
                          });
      // It sucks that these things aren't objects, and we need to store state in window.
      window.intervalId = setInterval(function() {
        var x = new Date();  // current time
        var y = Math.random();
        data.push([x, y]);
        g.updateOptions( { 'file': data } );
      }, 1000);
    },
    clean: function() {
      clearInterval(window.intervalId);
    }
  });
