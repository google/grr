

goog.setTestOnly();
goog.require('goog.string.html.HtmlParser');
goog.require('goog.string.html.HtmlSaxHandler');
goog.require('goog.testing.LooseMock');
goog.require('goog.testing.jsunit');

var handler;

function setUp() {
  handler = new goog.testing.LooseMock(
      new goog.string.html.HtmlSaxHandler());
  handler.$reset();
}

function tearDown() {
  handler.$verify();
}

function testHtmlParsingBasicText() {
  handler.startDoc();
  handler.pcdata('hello world');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, 'hello world');
}

function testHtmlParsingDoesntDestroyInitialDocument() {
  var text = 'hello world';
  handler.startDoc();
  handler.pcdata('hello world');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, text);

  assertEquals('hello world', text);
}

function testHtmlParsingImageTag() {
  handler.startDoc();
  handler.startTag('img', ['src', 'hello.gif']);
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<img src="hello.gif">');
}

function testHtmlParsingTagsInsideTags() {
  handler.startDoc();
  handler.startTag('div', []);
  handler.startTag('span', []);
  handler.pcdata('hello world');
  handler.endTag('span');
  handler.endTag('div');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<div><span>hello world</span></div>');
}

function testHtmlParsingTagWithMultipleArguments() {
  handler.startDoc();
  handler.startTag('img', ['src', 'hello.gif', 'width', '400px']);
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<img src="hello.gif" width="400px">');
}

function testHtmlParsingTagWithOneArgument() {
  handler.startDoc();
  handler.startTag('input', ['type', 'checkbox', 'checked', 'checked']);
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<input type=checkbox checked>');
}

function testHtmlParsingUnclosedTag() {
  handler.startDoc();
  handler.startTag('span', []);
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<span>');
}

function testParsingStyle() {
  handler.startDoc();
  handler.startTag('span', ['style', 'background-color: black;']);
  handler.endTag('span');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<span style="background-color: black;"></span>');
}

function testParsingCData() {
  handler.startDoc();
  handler.startTag('script', []);
  handler.cdata('<![CDATA[alert("hey");]]>');
  handler.endTag('script');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<script><![CDATA[alert("hey");]]><\/script>');
}

function testParsingSeveralTagsOnTheSameLevel() {
  handler.startDoc();
  handler.startTag('img', []);
  handler.startTag('p', []);
  handler.pcdata('hello');
  handler.startTag('img', []);
  handler.startTag('div', []);
  handler.endTag('p');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<img><p>hello<img><div/></p>');
}

function testParserDoesntHoldStateBetweenTwoParseCalls() {
  handler.startDoc();
  handler.startTag('div', []);
  handler.endDoc();

  handler.startDoc();
  handler.startTag('div', []);
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<div/>');
  parser.parse(handler, '<div/>');
}

function testSkipsOverComments() {
  handler.startDoc();
  handler.startTag('div', []);
  handler.endTag('div');
  handler.endDoc();

  handler.$replay();
  var parser = new goog.string.html.HtmlParser();
  parser.parse(handler, '<div><!-- this is a comment --></div>');
}
