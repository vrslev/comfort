frappe.pages["driver"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    card_layout: true,
    single_column: true,
    disable_sidebar_toggle: true,
  });
  wrapper.driver_page = new DriverPage(wrapper);
};

class DriverPage {
  constructor(wrapper) {
    this.wrapper = wrapper;
    this.page = wrapper.page;
    this.setup_page();
  }

  async setup_page() {
    $(".page-content").empty();
    $(".page-head").css("position", "static");

    if (!frappe.route_options) frappe.route_options = {};
    const response = await frappe.call({
      method: "comfort.stock.page.driver.driver.get_context",
      args: { name: frappe.route_options.name || null },
    });
    this.doc = response.message;

    if (this.doc) {
      this.page.set_title(
        `${__("Delivery Trip")} ${frappe.route_options.name}`
      );
    } else {
      this.page.set_title(__("Not found"));
      return;
    }

    for (let idx = 0; idx < this.doc.stops.length; idx++) {
      this.add_el(idx, this.doc.stops[idx]);
    }
  }

  generate_button(label, link, icon) {
    return `
      <button class="btn btn-default btn-sm ellipsis" style="margin-left: 10px; margin-bottom: 10px">
        <a href="${link}" style="text-decoration: none;">
          <i class="fa fa-${icon} icon-sm"></i>
          ${label}
        </a>
      </button>`;
  }

  generate_open_in_vk_button(stop) {
    if (stop.vk_url && stop.vk_url.match(/vk.com\/gim/)) {
      // We want to add a button only if url guides us to group dialog
      return this.generate_button(__("Open in VK"), stop.vk_url, "comments");
    }
    return "";
  }

  add_el(idx, stop) {
    var el = $(
      `<div
      class="row form-section card-section"
      style="min-height: 200px; padding: 15px; margin-top: 1rem; display: block"
      >
        <h4 style="display: inline-block; margin-left: 1rem; margin-top: 1rem">
          ${idx + 1}. ${stop.customer}
        </h4>
        <div style="margin-block-end: 0.5rem">
          ${this.generate_button(__("Call"), `tel:${stop.phone}`, "phone")}
          ${this.generate_open_in_vk_button(stop)}
        </div>
      </div>`
    ).appendTo(".page-content");

    let field_group = new frappe.ui.FieldGroup({
      body: el,
      fields: [
        {
          fieldname: "details",
          fieldtype: "Data",
          read_only: 1,
          default: stop.details,
          hidden: stop.details ? false : true,
        },
        {
          fieldname: "address",
          fieldtype: "Data",
          read_only: 1,
          options: "URL",
        },
        {
          fieldname: "delivery_type",
          fieldtype: "Data",
          read_only: 1,
          default: stop.installation
            ? `${__(stop.delivery_type)}, ${__("Installation").toLowerCase()}`
            : __(stop.delivery_type),
        },
        {
          fieldname: "pending_amount",
          fieldtype: "Currency",
          read_only: 1,
          default: stop.pending_amount,
        },
        {
          fieldname: "weight",
          fieldtype: "Data",
          read_only: 1,
          default: `${stop.weight} кг`,
        },
        {
          fieldname: "section_break",
          fieldtype: "Section Break",
          collapsible: 1,
          label: "Items",
        },
        {
          fieldname: "items",
          fieldtype: "HTML",
        },
      ],
    });
    field_group.make();

    // Set 'items' field value
    let items_text = "";
    for (const item of stop.items_) {
      items_text += `<li style="
        margin-left: 1em;
        margin-bottom: 0.5rem
      ">${comfort.format_item_code(item.item_code)} ⨉ ${item.qty} шт (${
        item.item_name
      })
      <br />
      </li>`;
    }
    field_group.fields_dict.items.set_value(
      `<ul style="
      margin-left: 0;
      padding-left: 0;
      color: var(--text-light);
    ">${items_text}</ul>`
    );

    // Clear spaces where field labels should be
    $(".clearfix").remove();

    // Set URL in address field
    let address_url_el = field_group.wrapper
      .find('[data-fieldname="address"]')
      .find("a");
    address_url_el.attr("href", stop.route_url);
    address_url_el.text(stop.address);

    // Fix '^' appearance on section break
    field_group.fields_dict.section_break.collapse();
    field_group.fields_dict.section_break.collapse();
  }
}
