frappe.provide("comfort");

comfort.fetch_items = (
  item_codes,
  force_update = false,
  download_images = true,
  values_from_db
) => {
  var promise = new Promise((resolve) => {
    let isResolved = false;
    frappe.call({
      method: "comfort.comfort_core.ikea.item.fetch_new_items",
      args: {
        item_codes: item_codes,
        force_update: force_update,
        download_images: download_images,
        values_from_db: values_from_db,
      },
      callback: (r) => {
        if (r.message.unsuccessful.length > 0) {
          frappe.msgprint(
            "Эти товары не удалось загрузить: " +
              r.message.unsuccessful.join(", ")
          );
        }
        frappe.dom.unfreeze();
        isResolved = true;
        resolve(r.message);
      },
    });
    setTimeout(() => {
      if (!isResolved) {
        frappe.dom.freeze();
      }
    }, 1000);
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
