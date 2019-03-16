/*global Gallery,Dygraph,data */
/*jshint evil:true */
/*global fn */
Gallery.register(
  'plotter',
  {
    name: 'Function Plotter',
    title: 'Define your data with functions',
    setup: function(parent) {
      parent.innerHTML = [
        "<p><b>Equation: </b><br/>",
        "<textarea cols='80' rows='10' id='eq'>function(x) {",
        "  return [0.1 * x, 0.1 * x + Math.sin(x), 0.1*x + Math.cos(x)];",
        "}</textarea><br/>",
        "<b>Preset functions:</b> <select id='presets'>",
        "<option selected id='custom'>(custom)</option>",
        "<option id='id'>Identity</option>",
        "<option id='sine'>Sine Wave</option>",
        "<option id='taylor'>Taylor series</option>",
        "<option id='sawtooth'>Sawtooth</option>",
        "</select>",
        "</p>",
        "",
        "<p><b>x range: </b> <input type='text' width='5' id='x1' value='-10' />",
        "to <input type='text' width='5' id='x2' value='10' /></p>",
        "<p><button id='plot'>Plot</button></p>",
        "",
        "<div id='graph_div' style='width:600px; height:300px;'></div>"].join("\n");

    },
    run: function() {
      var plot;  // defined below
      var select = document.getElementById("presets");
      var presets = {
        'id': [ -10, 10, 'function(x) {\n  return x;\n}' ],
        'sine': [ -10, 10, 'function(x) {\n  return Math.sin(x);\n}' ],
        'taylor': [ -3, 3, 'function(x) {\n  return [Math.cos(x), 1 - x*x/2 + x*x*x*x/24];\n}' ],
        'sawtooth': [-10, 10, 'function(x) {\n  var y = 0;\n  for (var i = 1; i < 20; i+=2) {\n    y += Math.sin(i * x)/i;\n  }\n  var final = 1 - 2*(Math.abs(Math.floor(x / Math.PI)) % 2);\n  return [4/Math.PI * y, final];\n}' ]
      };
      select.onchange = function() {
        var sel = select.selectedIndex;
        var id = select.options[sel].id;

        if (id == "custom") { return; }
        document.getElementById("x1").value = presets[id][0];
        document.getElementById("x2").value = presets[id][1];
        document.getElementById("eq").value = presets[id][2];
        plot();
      };

      var plotButton = document.getElementById("plot");
      plot = function() {
        var eq = document.getElementById("eq").value;
        eval("fn = " + eq);

        var graph = document.getElementById("graph_div");
        var width = parseInt(graph.style.width, 10);
        var x1 = parseFloat(document.getElementById("x1").value);
        var x2 = parseFloat(document.getElementById("x2").value);
        var xs = 1.0 * (x2 - x1) / width;

        var data = [];
        for (var i = 0; i < width; i++) {
          var x = x1 + i * xs;
          var y = fn(x);
          var row = [x];
          if (y.length > 0) {
            for (var j = 0; j < y.length; j++) {
              row.push(y[j]);
            }
          } else {
            row.push(y);
          }
          data.push(row);
        }

        new Dygraph(graph, data);
      };
      plotButton.onclick = plot;
      plot();
    }
  });
