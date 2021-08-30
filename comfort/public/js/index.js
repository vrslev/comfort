frappe.provide("comfort");

$(document).on("form-load", () => {
  cur_frm.page.sidebar.remove();
  $(".sidebar-toggle-btn").remove();
});

$(document).on("page-change", () => {
  $(".sidebar-toggle-btn").remove();
});

$(document).on("list_sidebar_setup", () => {
  cur_list.page.sidebar.remove();
});

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

function get_currency_symbol(currency) {
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
}

format_currency = (v, currency, decimals) => {
  var format = get_number_format(currency);
  var symbol = get_currency_symbol(currency);
  if (decimals === undefined) {
    decimals = frappe.boot.sysdefaults.currency_precision || 0;
  }

  if (symbol) return format_number(v, format, decimals) + " " + symbol;
  else return format_number(v, format, decimals);
};
