import * as Sentry from "@sentry/browser";
import { Integrations } from "@sentry/tracing";

export function init_sentry() {
  if (!localStorage.sentry_dsn || !localStorage.sentry_release) {
    frappe.call({
      method: "comfort.integrations.sentry.get_info",
      callback: (r) => {
        if (!r.message) return;
        localStorage.sentry_dsn = r.message.dsn;
        localStorage.sentry_release = r.message.release;
      },
    });
  }

  if (localStorage.sentry_dsn) {
    Sentry.init({
      dsn: localStorage.sentry_dsn,
      release: localStorage.sentry_release,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: 1.0,
      debug: true,
    });
  }
}
