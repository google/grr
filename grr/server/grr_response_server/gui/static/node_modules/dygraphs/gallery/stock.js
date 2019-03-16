/*global Gallery,Dygraph,data */
/*global stockData */
Gallery.register(
  'stock',
  {
    name: 'Stock Chart Demo',
    title: 'Stock Chart Demo',
    setup: function(parent) {
      parent.innerHTML = [
          "<div id='stock_div' style='width: 600px; height: 300px;'></div><br/>",
          "<div style='width: 600px; text-align: center;'>",
          "  <button id='linear'>Linear Scale</button>&nbsp;",
          "  <button id='log' disabled='true'>Log Scale</button>",
          "</div>"].join("\n");
    },
    run: function() {
      var g = new Dygraph(document.getElementById("stock_div"), stockData,
          {
            customBars: true,
            logscale: true
          });

      var linear = document.getElementById("linear");
      var log = document.getElementById("log");
      var setLog = function(val) {
        g.updateOptions({ logscale: val });
        linear.disabled = !val;
        log.disabled = val;
      };
      linear.onclick = function() { setLog(false); };
      log.onclick = function() { setLog(true); };
    }
  });
