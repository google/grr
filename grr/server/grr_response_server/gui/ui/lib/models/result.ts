/**
 * Component describes which component that will be used to render the
 * cell contents.
 */
// TODO: Expand CellComponent enum types.
export enum CellComponent {
  DEFAULT,
  TIMESTAMP,  // Takes in a Date object (see ComponentToType below)
}
/**
 * ComponentToType maps CellComponent values to types that represent them. This
 * allows us to know the TS type of an object property based on its
 * corresponding CellComponent.
 */
// TODO: Expand CellComponent enum types.
export declare interface ComponentToType {
  [CellComponent.TIMESTAMP]: Date|undefined;
  [CellComponent.DEFAULT]: string|number|undefined;
}

/**
 * ColumnDescriptor describes a column by its title and corresponding cell type
 * to render results.
 */
export declare interface ColumnDescriptor {
  title?: string;
  component?: CellComponent;
}

/**
 * ColumnDescriptorHasComponent is used as an auxiliary interface in the
 * CellData type definition below. It is used to describe a ColumnDescriptor
 * which has the `component` property set (not optional).
 */
export declare interface ColumnDescriptorHasComponent {
  component: CellComponent;
}

/**
 * CellData declares a type that maps the keys of T to its corresponding TS
 * type. For this, it uses ComponentToType map and, based on the CellComponent
 * for a particular key, translates it into the corresponding type.
 *
 * For example, given the following `MY_OBJ` definition:
 * const MY_OBJ = {
 *  'prop1': {},
 *  'prop2': {component: CellComponent.TIMESTAMP},
 * }
 * the corresponding `CellData` vefiries that:
 * - the keys are of type 'prop1'|'prop2'
 * - the corresponding type for each comes from the ComponentToType mapping.
 *   'prop1': string | number | undefined;
 *       comes from: [CellComponent.DEFAULT]: string|number|undefined;
 *   'prop2': Date | undefined;
 *        comes from: [CellComponent.TIMESTAMP]: Date|undefined;
 */
export declare type CellData<T extends {[key: string]: ColumnDescriptor}> = {
  [key in keyof T]:
      ComponentToType[T[key] extends ColumnDescriptorHasComponent ?
                          T[key]['component'] :
                          CellComponent.DEFAULT];
};

/**
 * PayloadTranslation describes the collection of metadata used to translate a
 * given PayloadType into rederable information.
 */
export declare interface PayloadTranslation<
    T extends {[key: string]: ColumnDescriptor}> {
  translateFn(arg: unknown): CellData<T>;
  columns: T;
  tabName: string;
}