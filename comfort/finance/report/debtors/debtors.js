frappe.query_reports["Debtors"] = {
  onload(report) {
    report.$message.remove();
    report.$summary
      .css("justify-content", "center")
      .css("padding", "var(--padding-2xl)");
  },
};
