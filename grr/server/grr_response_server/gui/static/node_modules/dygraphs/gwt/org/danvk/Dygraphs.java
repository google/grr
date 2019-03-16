package org.danvk;

import com.google.gwt.core.client.GWT;
import com.google.gwt.dom.client.Document;
import com.google.gwt.dom.client.ScriptElement;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.TextResource;

/**
 * Methods for installing Dygraphs source in a GWT document.
 *
 * @author flooey@google.com (Adam Vartanian)
 */
public class Dygraphs {

  // Protected because the GWT compiler has to generate a subclass.
  protected interface Resources extends ClientBundle {
    @Source("org/danvk/dygraph-combined.js")
    TextResource dygraphs();
  }

  private static final Resources RESOURCES = GWT.create(Resources.class);
  private static boolean installed = false;

  /**
   * Install the Dygraphs JavaScript source into the current document.  This
   * method is idempotent.
   */
  public static synchronized void install() {
    if (!installed) {
      ScriptElement e = Document.get().createScriptElement();
      e.setText(RESOURCES.dygraphs().getText());
      Document.get().getBody().appendChild(e);
      installed = true;
    }
  }

  // Prevent construction
  private Dygraphs() { }

}
