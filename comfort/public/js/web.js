import { init_sentry } from "./sentry";

frappe.ready(() => {
  init_sentry();
});
