import {platformBrowserDynamic} from '@angular/platform-browser-dynamic';

import {AppModule} from './components/app/app_module';
import {environment} from './environments/environment';

platformBrowserDynamic()
  .bootstrapModule(AppModule)
  .catch((err) => console.error(err));
