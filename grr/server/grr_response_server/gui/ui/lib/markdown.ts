import * as marked from 'marked';

const tempMarked = marked;

type MarkedOptions = Parameters<typeof marked>[1];

/** We export "marked" and its options them with their original name */
export {tempMarked as marked, MarkedOptions};
