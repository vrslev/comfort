import { init_sentry } from "./sentry";

init_sentry();

frappe.provide("comfort");

var DONT_REMOVE_SIDEBAR_IN_DOCTYPES = ["Item", "Customer"];

// Remove sidebar in Form view
$(document).on("form-load", () => {
  if (!DONT_REMOVE_SIDEBAR_IN_DOCTYPES.includes(cur_frm.doctype)) {
    cur_frm.page.sidebar.remove();
  }
  $(".sidebar-toggle-btn").remove();
});

// Remove sidebar in List view
$(document).on("list_sidebar_setup", () => {
  cur_list.page.sidebar.remove();
});

// Remove sidebar toggle button in all pages. Exists for Workspace view
$(document).on("page-change", () => {
  $(".sidebar-toggle-btn").remove();
});

// Remove buttons from profile dropdown in all pages
$(document).ready(() => {
  $(
    '[class="nav-item dropdown dropdown-help dropdown-mobile d-none d-lg-block"]'
  ).remove();
  $('[onclick="return frappe.ui.toolbar.setup_session_defaults()"]').remove();
  $('[onclick="return frappe.ui.toolbar.view_website()"]').remove();
  $('[onclick="return frappe.ui.toolbar.toggle_full_width()"]').remove();
  $('[href="/app/background_jobs"]').remove();
  $('[href="/app/user-profile"]').remove();
});

// Hide unused modules for production
if (location.href.match("/app/home$" && !frappe.boot.developer_mode)) {
  $(document).ready(() => {
    $('[href="/app/build"]').remove();
    $('[href="/app/website"').remove();
    $('[href="/app/customization"').remove();
    $('[href="/app/settings"').remove();
    $('[href="/app/integrations"').remove();
    $('[href="/app/users"').remove();
    $('[href="/app/tools"').remove();
    for (let el of $('[class="standard-sidebar-label"]')) {
      if (el.textContent.includes("Administration")) {
        $(el).hide();
      }
    }
  });
}

comfort.get_items = (item_codes) => {
  // TODO: Fix freeze
  var promise = new Promise((resolve) => {
    /* eslint-disable */
    let isResolved = false;
    /* eslint-enable */
    frappe.call({
      method: "comfort.comfort_core.get_items",
      args: { item_codes: item_codes },
      callback: (r) => {
        frappe.dom.unfreeze();
        isResolved = true;
        resolve(r.message);
      },
    });
    // setTimeout(() => {
    //   if (!isResolved) {
    //     frappe.dom.freeze();
    //   }
    // }, 1000);
  });
  return promise;
};

// From ERPNext
frappe.form.link_formatters["Item"] = (value, doc) => {
  if (
    doc &&
    value &&
    doc.item_name &&
    doc.item_name !== value &&
    doc.item_code === value
  ) {
    return value + ": " + doc.item_name;
  } else if (!value && doc.doctype && doc.item_name) {
    return doc.item_name;
  } else {
    return value;
  }
};

frappe.ui.form.ControlLink = frappe.ui.form.ControlLink.extend({
  get_filter_description() {
    return;
  },
});

get_currency_symbol = (currency) => {
  if (frappe.boot) {
    if (
      frappe.boot.sysdefaults &&
      frappe.boot.sysdefaults.hide_currency_symbol == "Yes"
    )
      return null;

    if (!currency) currency = frappe.boot.sysdefaults.currency;

    return frappe.model.get_value(":Currency", currency, "symbol") || currency;
  } else {
    // load in template
    return frappe.currency_symbols[currency];
  }
};

format_currency = (v, currency, decimals) => {
  decimals = frappe.boot.sysdefaults.currency_precision || 0;
  let format = get_number_format(currency);
  let symbol = get_currency_symbol(currency);

  if (symbol) {
    return format_number(v, format, decimals) + " " + symbol;
  } else {
    return format_number(v, format, decimals);
  }
};

// Hide "Cancel" buttons in low level DocTypes
for (let doctype of ["GL Entry", "Checkout", "Stock Entry"]) {
  frappe.ui.form.on(doctype, {
    setup(frm) {
      let old_func = frm.toolbar.set_page_actions;
      frm.toolbar.set_page_actions = (status) => {
        old_func.call(frm.toolbar, status);
        if (frm.toolbar.current_status == "Cancel") {
          frm.toolbar.page.clear_secondary_action();
        }
      };
    },
  });
}
