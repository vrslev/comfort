import { init, setUser } from "@sentry/browser";
import { Integrations } from "@sentry/tracing";

export function init_sentry() {
  frappe.call({
    method: "comfort.integrations.sentry.get_info",
    callback: (r) => {
      init({
        dsn: r.message.dsn,
        release: r.message.release,
        integrations: [new Integrations.BrowserTracing()],
      });
      if (frappe.session.user_email) {
        setUser({ email: frappe.session.user_email });
      }
    },
  });
}
