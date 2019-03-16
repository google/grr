/*global Gallery,Dygraph,data */
/*global NoisyData */
Gallery.register(
  'resize',
  {
    name: 'Resizable Graph',
    title: 'Resize the window. The dygraph will resize with it.',
    setup: function(parent) {
      parent.innerHTML = "<div id='div_g'>";
    },
    run: function() {
      new Dygraph(
            document.getElementById("div_g"),
            NoisyData, {
              rollPeriod: 7,
              errorBars: true
            }
          );
    }
  });
