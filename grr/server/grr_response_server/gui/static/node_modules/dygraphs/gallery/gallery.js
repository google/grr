/*jshint loopfunc:true */
/*global Dygraph,$,TextArea,jQuery */
var Gallery = {};

Gallery.entries = {};
Gallery.entryOrder = [];
Gallery.runningDemo = null;

/*
 * Shortcut for creating HTML associated with a parent.
 */
Gallery.create = function(type, parent, className) {
  var elem = document.createElement(type);
  parent.appendChild(elem);
  if (className) {
    elem.className = className;
  }
  return elem;
};

Gallery.start = function() {
  Gallery.toc = document.getElementById("toc");
  Gallery.workarea = document.getElementById("workarea");
  Gallery.subtitle = Gallery.create("div", Gallery.workarea);
  Gallery.subtitle.id = "subtitle";
  Gallery.workareaChild = Gallery.create("div", Gallery.workarea);
  Gallery.demotitle = document.getElementById("demotitle");
  Gallery.textarea = new TextArea();
  Gallery.textarea.cancel.style.display = "none";
  Gallery.textarea.width = 600;
  Gallery.textarea.height = 400;

  for (var idx in Gallery.entryOrder) {
    var id = Gallery.entryOrder[idx];
    var demo = Gallery.entries[id];

    var div = Gallery.create("div", Gallery.toc, "entry");
    div.id = id + "-toc";
    var innerDiv = Gallery.create("div", div, "");

    // Storing extra data in the demo object.
    demo.div = div;
    demo.innerDiv = innerDiv;

    innerDiv.textContent = demo.name;
    div.onclick = function(demo, id) { return function() {
      if (Gallery.runningDemo !== null) {
        Gallery.runningDemo.innerDiv.className = "";
        if (Gallery.runningDemo.clean) {
          Gallery.runningDemo.clean(Gallery.workareaChild);
        }
      }
      Gallery.subtitle.innerHTML = "";

      Gallery.workareaChild.id = id;
      location.hash = "g/" + id;

      Gallery.workareaChild.innerHTML='';
      if (demo.setup) {
        demo.setup(Gallery.workareaChild);
      }

      Gallery.demotitle.textContent = demo.title ? demo.title : "";
      demo.innerDiv.className = "selected";

      var codeSpan = Gallery.create("span", Gallery.subtitle);
      codeSpan.id = "code";

      var htmlLink = Gallery.create("a", codeSpan);
      htmlLink.textContent = "HTML";

      Gallery.create("span", codeSpan).textContent = " | ";

      var javascriptLink = Gallery.create("a", codeSpan);
      javascriptLink.textContent = "Javascript";

      var css = getCss(id);
      var cssLink;
      if (css) {
        Gallery.create("span", codeSpan).textContent = " | ";
        cssLink = Gallery.create("a", codeSpan);
        cssLink.textContent = "CSS";
      }

      var jsFiddleForm = Gallery.create("form", codeSpan);
      var jsfs = $(jsFiddleForm);
      jsFiddleForm.method = "post";
      jsFiddleForm.action = "http://jsfiddle.net/api/post/jquery/1.4/";

      jsfs.html("<input type='submit' value='Edit in jsFiddle'/>\n" +
      "<span style='display:none'>\n" +
      "<textarea name='resources'>http://dygraphs.com/dygraph-combined.js</textarea>\n" +
      "<input type='text' name='dtd' value='html 5'/></span>\n");

      var javascript = demo.run.toString();
      var html = Gallery.workareaChild.innerHTML;

      // tweak for use in jsfiddle
      javascript = " $(document).ready(" + javascript + "\n);";
      jQuery('<textarea/>', { name: 'html' })
        .val(html)
        .hide()
        .appendTo(jsfs);

      jQuery('<textarea/>', { name: 'js' })
        .val(javascript)
        .hide()
        .appendTo(jsfs);

      if (css) {
        jQuery('<textarea/>', { name: 'css' })
          .val(css)
          .hide()
          .appendTo(jsfs);
      }
      jQuery('<input/>', {
        type: 'text',
        name: 'title',
        value: 'title tbd'
      })
        .hide()
        .appendTo(jsfs);
      jQuery('<input/>', {
        type: 'text',
        name: 'description',
        value: 'desc tbd'
      })
        .hide()
        .appendTo(jsfs);

      htmlLink.onclick = function() {
        Gallery.textarea.show("HTML", html);
      };

      javascriptLink.onclick = function() {
        Gallery.textarea.show("Javascript", javascript);
      };

      if (css) {
        cssLink.onclick = function() {
          Gallery.textarea.show("CSS", css);
        };
      }

      demo.run(Gallery.workareaChild);
      Gallery.runningDemo = demo;
    }; }(demo, id);
  }

  Gallery.hashChange();

  window.onhashchange = Gallery.setHash;
};

var getCss = function(id) {
  for (var i = 0; i < document.styleSheets.length; i++) {
    var ss = document.styleSheets[i];
    if (ss.title == "gallery") {
      try {
        var rules = ss.rules || ss.cssRules;
        if (rules) {
          var arry = [];
          for (var j = 0; j < rules.length; j++) {
            var rule = rules[j];
            var cssText = rule.cssText;
            var key = "#workarea #" + id + " ";
            if (cssText.indexOf(key) === 0) {
              arry.push(cssText.substr(key.length));
            }
          }
          return arry.join("\n\n");
        }
      } catch(e) { // security error
        console.log(e);
      }
    }
  }
  return "not found";
};

Gallery.register = function(id, demo) {
  if (Gallery.entries[id]) {
    throw id + " already registered";
  }
  Gallery.entries[id] = demo;
  Gallery.entryOrder.push(id);
};

Gallery.hashChange = function(event) {
  if (location.hash) {
    if (location.hash.indexOf("#g/") === 0) {
      var id = location.hash.substring(3) + "-toc";
      var elem = document.getElementById(id);
      elem.onclick();
      return;
    }
  }
  Gallery.workareaChild.innerHTML = "<h3>Select a demo from the gallery on the left</h3>";
};
