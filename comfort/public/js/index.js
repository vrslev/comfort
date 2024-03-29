import { init_sentry } from "./sentry";

frappe.provide("comfort");

comfort.get_items = (item_codes) => {
  var promise = new Promise((resolve, reject) => {
    let is_resolved = false;
    frappe
      .call({
        method: "comfort.integrations.ikea.get_items",
        args: { item_codes: item_codes },
        callback: (r) => {
          is_resolved = true;
          frappe.dom.unfreeze();
          resolve(r.message);
        },
      })
      .fail((r) => {
        is_resolved = true;
        frappe.dom.unfreeze();
        reject(r);
      });

    // Freeze if fetch take a long time
    setTimeout(() => {
      if (!is_resolved) {
        frappe.dom.freeze();
      }
    }, 1000);
  });
  return promise;
};

comfort.quick_add_items = (text, field, item_callback, callback) => {
  comfort.get_items(text).then((values) => {
    for (var v of values) {
      let doc = cur_frm.add_child(field, {
        item_code: v.item_code,
        item_name: v.item_name,
        qty: 1,
        rate: v.rate,
        weight: v.weight,
      });
      item_callback(doc.doctype, doc.name);
    }

    let grid = cur_frm.fields_dict[field].grid;

    // loose focus from current row
    grid.add_new_row(null, null, true);
    grid.grid_rows[grid.grid_rows.length - 1].toggle_editable_row();

    for (var i = grid.grid_rows.length; i--; ) {
      let doc = grid.grid_rows[i].doc;
      if (!doc.item_code) {
        grid.grid_rows[i].remove();
      }
    }

    if (callback) {
      callback(cur_frm);
    }
    refresh_field(field);
  });
};

window.get_currency_symbol = (currency) => {
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

window.format_currency = (v, currency, decimals) => {
  decimals = frappe.boot.sysdefaults.currency_precision || 0;
  let format = get_number_format(currency);
  let symbol = get_currency_symbol(currency);

  if (symbol) {
    return format_number(v, format, decimals) + " " + symbol;
  } else {
    return format_number(v, format, decimals);
  }
};

function setup_unnecessary_stuff_removal() {
  // Remove sidebar in Form view
  $(document).on("form-load", () => {
    if (!["Item", "Customer"].includes(cur_frm.doctype)) {
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
    $(".dropdown-help").remove();
    $(".dropdown-notifications").remove();
    $('[class="vertical-bar d-none d-sm-block"]').remove();
    $('[onclick="return frappe.ui.toolbar.setup_session_defaults()"]').remove();
    $('[onclick="return frappe.ui.toolbar.view_website()"]').remove();
    $('[onclick="return frappe.ui.toolbar.toggle_full_width()"]').remove();
    $('[href="/app/background_jobs"]').remove();
    $('[href="/app/user-profile"]').remove();

    // Hide unused modules for production
    if (
      !frappe.boot.developer_mode &&
      ["", "Workspaces"].includes(frappe.get_route()[0])
    ) {
      $(document).ready(() => {
        $('[href="/app/build"]').remove();
        $('[href="/app/website"').remove();
        $('[href="/app/customization"').remove();
        $('[href="/app/settings"').remove();
        $('[href="/app/integrations"').remove();
        $('[href="/app/users"').remove();
        $('[href="/app/tools"').remove();
        $(`.standard-sidebar-label:contains(${__("Administration")})`).remove();
        for (let el of $('[class="standard-sidebar-label"]')) {
          if (el.textContent.includes("Administration")) {
            $(el).hide();
          }
        }
      });
    }
  });
}

comfort.format_item_code = (value) => {
  if (value && /^\d+$/.test(value) && value.length == 8) {
    // Valid item code
    value = `${value.substring(0, 3)}.${value.substring(
      3,
      6
    )}.${value.substring(6, 8)}`;
  }
  return value;
};

function add_item_code_formatter() {
  frappe.form.link_formatters["Item"] = (value, doc, df) => {
    value = comfort.format_item_code(value);

    if (df.fieldname != "item_code") {
      return value;
    } else if (value && doc && doc.item_name && doc.item_name != value) {
      // item code and item name
      return value + ": " + doc.item_name;
    } else if (!value && doc.doctype && doc.item_name) {
      // only item name
      return doc.item_name;
    } else {
      // only item code
      return value;
    }
  };
}

function format_phone(value) {
  var regex = RegExp(/^((8|\+7)[-– ]?)?(\(?\d{3}\)?[-– ]?)?[\d\-– ]{7,10}$/);
  if (!regex.test(value)) return "";
  let clean = value.replace(/[^0-9]+/);
  if (clean[0] == "7") {
    clean = "8" + value.substring(1);
  }
  if (clean.length != 11) {
    return clean;
  }
  return `${value.substring(0, 1)} (${value.substring(1, 4)}) ${value.substring(
    4,
    7
  )}–${value.substring(7, 9)}–${value.substring(9, 11)}`;
}

function patch_data_field_formatter() {
  let old_data_field_formatter = frappe.form.formatters["Data"];
  frappe.form.formatters["Data"] = (value, df) => {
    if (df && df.options == "Phone") {
      return format_phone(value);
    }
    return old_data_field_formatter(value, df);
  };
}

function patch_control_link_class() {
  frappe.ui.form.ControlLink = frappe.ui.form.ControlLink.extend({
    get_filter_description() {
      return;
    },
  });
}

function hide_cancel_button_in_low_level_doctypes() {
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
}

function patch_guess_colour() {
  // Pretty colours for Comfort doctypes
  var old_guess_colour = frappe.utils.guess_colour;
  frappe.utils.guess_colour = (text) => {
    var colors = {
      "In Progress": "orange",
      Completed: "green",
      "To Purchase": "red",
      Purchased: "orange",
      "To Deliver": "orange",
      Delivered: "green",
      Unpaid: "red",
      "Partially Paid": "orange",
      Paid: "green",
      Overpaid: "orange",
      "": " ",
    };
    if (colors[text]) {
      return colors[text];
    } else {
      return old_guess_colour(text);
    }
  };
}

function detect_and_switch_theme() {
  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    $("html").attr("data-theme", "dark");
  } else {
    $("html").attr("data-theme", "light");
  }

  function toggle_theme(e) {
    let theme = e.matches ? "dark" : "light";
    $("html").attr("data-theme", theme);
  }
  window.matchMedia("(prefers-color-scheme: light)").addListener(toggle_theme);
  window.matchMedia("(prefers-color-scheme: dark)").addListener(toggle_theme);
}

setup_unnecessary_stuff_removal();
add_item_code_formatter();
patch_data_field_formatter();
patch_control_link_class();
hide_cancel_button_in_low_level_doctypes();
patch_guess_colour();
init_sentry();
detect_and_switch_theme();
