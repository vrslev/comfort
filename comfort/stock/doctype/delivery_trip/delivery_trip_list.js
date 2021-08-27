frappe.listview_settings["Delivery Trip"] = {
  add_fields: ["status"],
  get_indicator: (doc) => {
    if (["Cancelled", "Draft"].includes(doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "In Progress") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
};
